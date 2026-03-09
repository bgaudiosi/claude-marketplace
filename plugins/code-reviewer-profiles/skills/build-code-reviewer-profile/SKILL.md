---
name: build-code-reviewer-profile
description: Fetch any GitHub user's review history and generate a code reviewer profile
version: 0.1.0
tags: [github, code-review, profile-generation, analysis]
---

# Build Code Reviewer Profile

Fetches a GitHub user's review history and generates a comprehensive reviewer profile capturing their code review style, preferences, and patterns.

## When to Use This Skill

Use this skill when:
- You want to build or update a GitHub user's reviewer profile
- You need to analyze someone's code review patterns
- You're setting up a reviewer profile for the first time
- You want to refresh a profile with recent review data

## Command-Line Arguments

### Required (or will be prompted)
- `--user=<username>` - GitHub username to analyze (e.g., `jsmith`, `octocat`)

### Optional
- `--host=<hostname>` - GitHub host (default: `github.com`)
  - For GitHub Enterprise: `--host=github.enterprise.com`
  - For public GitHub: omit or use `--host=github.com`
- `--storage=<path>` - Storage directory (default: `/tmp/code-reviewer-profiles/`)
- `--limit=<number>` - Maximum PRs to fetch (default: 150)

### Examples

```bash
# Public GitHub user
/build-code-reviewer-profile --user=octocat

# Enterprise GitHub user with custom host
/build-code-reviewer-profile --user=jsmith --host=github.enterprise.com

# With custom storage
/build-code-reviewer-profile --user=torvalds --storage=~/.claude/profiles/

# Interactive (will prompt for username and host)
/build-code-reviewer-profile
```

## Prerequisites

### Required Tools

1. **GitHub CLI (`gh`)** - Must be installed and authenticated:
   ```bash
   gh auth status
   ```

   If not authenticated, run:
   ```bash
   # For public GitHub (default):
   gh auth login

   # For GitHub Enterprise:
   gh auth login --hostname <github-host>
   ```

2. **Required GitHub scopes**:
   - `repo` (to read PR and review data)
   - `read:org` (to search across organization repositories)

### Environment

- Internet connectivity to access GitHub API
- Sufficient disk space for caching review data (~50MB for 150 PRs)

## Implementation Steps

This skill operates in **two distinct phases** for token efficiency:

### Phase 1: Fetch and Cache Reviews (No AI Required)

This phase collects raw data from GitHub without AI analysis.

#### Step 1.0: Parse Arguments and Collect Parameters

1. **Parse command-line arguments**:
   - Extract `--user`, `--host`, `--storage`, `--limit` if provided

2. **Prompt for missing required parameters**:

   **If username not provided**:
   ```
   Which GitHub user would you like to build a profile for?

   Enter GitHub username: _
   ```

   **If host not provided**:
   ```
   Which GitHub instance?

   1. github.com (public GitHub) [default]
   2. GitHub Enterprise (custom host)

   Choose option (1/2) or press Enter for default: _
   ```

   If user chooses option 2:
   ```
   Enter GitHub Enterprise hostname (e.g., github.enterprise.com): _
   ```

3. **Fetch display name from GitHub**:
   ```bash
   gh api users/<username> --jq '.name' --hostname <github-host>
   ```

   - If successful and name is not empty, use display name
   - Otherwise, fall back to username

4. **Verify GitHub authentication**:
   ```bash
   gh auth status --hostname <github-host>
   ```

   If not authenticated:
   ```
   ❌ Not authenticated to <github-host>

   Please authenticate first:
   # For public GitHub:
   gh auth login

   # For GitHub Enterprise:
   gh auth login --hostname <github-host>

   Then run this skill again.
   ```
   Exit skill.

5. **Display configuration summary**:
   ```
   📋 Configuration:
      Username: <username>
      Display name: <display-name>
      GitHub host: <github-host>
      Storage: <storage-dir> (will prompt next)
      PR limit: <limit>

   Continue? (y/n)
   ```

#### Step 1.1: Initialize Storage

1. **Prompt user for storage location**:
   ```
   Profile data will be stored persistently. Where would you like to store it?

   Options:
   1. Default location: /tmp/code-reviewer-profiles/ (cleared on system restart)
   2. Permanent location (e.g., ~/.claude/reviewer-profiles/)

   Enter path or press Enter for default:
   ```

2. **Create directory structure**:
   ```bash
   mkdir -p <storage-dir>/profiles
   mkdir -p <storage-dir>/cache/reviews/<username>
   ```

3. **Store the chosen storage path** for use in Phase 2 and by the review skill.

#### Step 1.2: Fetch PRs and Review Comments

Run the fetch script to search for PRs, fetch all inline and review-level comments, and build the index:

```bash
python3 <plugin-dir>/scripts/fetch_reviews.py \
  --user=<username> \
  --cache-dir=<storage-dir>/cache/reviews/<username> \
  --limit=<limit>
```

Where `<plugin-dir>` is the directory containing this skill's plugin (i.e. the `code-reviewer-profiles` plugin directory). You can find it relative to this SKILL.md file: `../../../scripts/fetch_reviews.py` or by resolving the plugin root.

**Host handling**:
- If `--host` is omitted, the script auto-detects the host from `gh auth status`
- For GitHub Enterprise, pass `--host=<github-host>` explicitly
- The script handles `GH_HOST` env var automatically for non-github.com hosts (since `gh search` doesn't support `--hostname`)

**Resume support**: If interrupted, re-running the same command resumes from the last checkpoint. The script saves a checkpoint every 10 PRs and skips already-cached PR files.

**What the script does**:
1. Searches for merged PRs reviewed by the user (with date-window pagination for >100 PRs)
2. For each PR, fetches inline comments and review-level comments via `gh api`
3. Filters comments to only those authored by the target user
4. Marks trivial comments (LGTM, "Looks good", emoji-only, etc.) with `"trivial": true` — these are preserved in the data but flagged for exclusion during analysis
5. Normalizes file extensions using `pathlib` and includes a `file_types` summary per PR
6. Saves each PR to `<cache-dir>/pr-{owner}-{repo}-{number}.json`
7. Builds `<cache-dir>/index.json` with metadata, repository stats, and PR list

**End of Phase 1**: The script prints a summary. Display it to the user:
```
✅ Fetched <N> PRs with <M> review comments
📁 Cached in: <storage-dir>/cache/reviews/<username>/
📊 Next: Analyzing patterns to build <display-name>'s profile...
```

---

### Phase 2: Analyze and Build Profile

This phase analyzes the cached data directly. Read cached PR files in batches to manage context window usage.

#### Step 2.1: Load Cached Data

Read the index file to get the list of cached PRs:
```
<storage-dir>/cache/reviews/<username>/index.json
```

**Verification**:
- Ensure at least 30 PRs are cached (minimum for meaningful analysis)
- If fewer, warn user and ask whether to proceed anyway

#### Step 2.2: Extract Comment Themes (Batch Processing)

**Goal**: Categorize all comments by theme (Documentation, Testing, Code Structure, etc.)

**Trivial comment handling**: Comments in the cached data that have `"trivial": true` should be **excluded from theme analysis**. Do not categorize or analyze them. However, count them separately and report the total in the final statistics (e.g., "45 approval-only comments excluded from analysis"). These are LGTM, "Looks good", emoji-only, and similar approval comments that don't contain substantive review feedback.

**Process**:
1. Load PRs in batches of 15
2. For each batch, extract all inline and review comments, **skipping those with `"trivial": true`**
3. Analyze with the following categorization:

   ```
   Analyze these code review comments and categorize each by theme:
   - Documentation (missing docs, unclear comments, etc.)
   - Testing (missing tests, test coverage, edge cases)
   - Code Structure (method extraction, class design, abstraction)
   - Error Handling (exception handling, validation, edge cases)
   - Performance (inefficiencies, optimization opportunities)
   - Security (vulnerabilities, secure coding practices)
   - Style (naming, formatting, conventions)
   - Other (anything that doesn't fit above)

   For each comment, output:
   {
     "comment_id": <id>,
     "theme": "<category>",
     "summary": "<brief summary>",
     "code_context": "<file path and line>"
   }
   ```

4. Aggregate results across all batches
5. Count frequency of each theme

**Batching guide**: ~15 PRs per batch keeps context manageable. Adjust based on comment density.

#### Step 2.3: Analyze Review Style (Single Batch)

**Goal**: Understand the reviewer's tone, typical phrases, and suggestion patterns

**Process**:
1. Select a representative sample of 30 comments across different themes
2. Analyze with the following prompt:

   ```
   Analyze this reviewer's style based on these sample comments:

   1. What is the overall tone? (e.g., professional, constructive, direct)
   2. What are the key traits? (e.g., detail-oriented, pragmatic, example-driven)
   3. What phrases does the reviewer commonly use?
   4. How does the reviewer structure suggestions?
      - Does the reviewer provide code examples?
      - Does the reviewer explain reasoning?
      - Does the reviewer ask questions?
   5. What questions does the reviewer commonly ask?

   Output as JSON with keys: tone, key_traits, opening_phrases, suggestion_style, questions_asked
   ```

3. Parse and store the style analysis

#### Step 2.4: Extract Technical Preferences (Batch Processing)

**Goal**: Identify language-specific patterns, framework preferences, and anti-patterns

**Process**:
1. Group comments by file extension using the `file_extension` field on each inline comment (already normalized by the fetch script via `pathlib` — handles Dockerfile, dotfiles, and extensionless files correctly). You can also use the per-PR `file_types` summary for quick aggregation.
2. Sample 30 representative PRs across different repos and file types
3. For each file type, analyze with:

   ```
   Analyze these code review comments for {file_type} files.
   Identify:
   1. Language-specific preferences (e.g., "Use data classes", "Prefer Optional")
   2. Framework-specific patterns (e.g., Spring, testing frameworks)
   3. Anti-patterns flagged (e.g., "Hardcoded values", "Missing error handling")
   4. Common suggestions for this file type

   Output as JSON with keys: language_preferences, framework_patterns, anti_patterns, common_suggestions
   ```

4. Aggregate across all file types

#### Step 2.5: Generate Profile JSON

Combine all analysis results into the profile schema:

```json
{
  "profile_version": "1.0",
  "username": "<username>",
  "github_host": "<github-host>",
  "display_name": "<display-name>",
  "generated_at": "2026-02-27T15:30:00Z",
  "data_sources": {
    "total_prs_analyzed": 150,
    "total_comments_analyzed": 847,
    "date_range": {
      "earliest": "2024-01-15T10:00:00Z",
      "latest": "2026-02-27T10:30:00Z"
    }
  },
  "review_style": {
    "summary": "...",
    "key_traits": ["..."],
    "tone": "..."
  },
  "focus_areas": [
    {
      "category": "Documentation",
      "frequency": 0.42,
      "examples": ["..."],
      "patterns": ["..."]
    }
  ],
  "common_patterns": {
    "opening_phrases": ["..."],
    "suggestion_style": ["..."],
    "questions_asked": ["..."]
  },
  "technical_preferences": {
    "languages": {
      "kotlin": {"preferences": ["..."]},
      "java": {"preferences": ["..."]}
    },
    "frameworks": {
      "spring": ["..."]
    }
  },
  "anti_patterns_flagged": ["..."],
  "statistics": {
    "avg_comments_per_pr": 5.6,
    "most_commented_file_types": [
      {"extension": ".kt", "count": 423}
    ],
    "comment_distribution": {
      "nitpicks": 0.15,
      "suggestions": 0.65,
      "blocking_issues": 0.20
    }
  }
}
```

Save to: `<storage-dir>/profiles/<username>.json`

#### Step 2.6: Generate Human-Readable Summary

Create a markdown summary for easy reference:

```markdown
# <display-name>'s Code Review Profile

**Username**: <username>
**GitHub**: <github-host>
**Generated**: 2026-02-27 15:30:00
**Data sources**: 150 PRs, 847 comments (2024-01-15 to 2026-02-27)

## Review Style

<display-name>'s review style is [summary from analysis]. Key traits include:
- [Trait 1]
- [Trait 2]
- [Trait 3]

**Tone**: [Professional, constructive, educational, etc.]

## Focus Areas

### 1. Documentation (42% of comments)
[Description of documentation focus]

**Common patterns**:
- [Pattern 1]
- [Pattern 2]

**Examples**:
- "Add metadata header to explain purpose"
- "Document config options in javadoc"

### 2. Code Structure (31% of comments)
[Similar structure...]

## Common Phrases

**Opening phrases**:
- "You could make this easier by..."
- "Consider..."
- "This might be clearer if..."

**Questions asked**:
- "What happens if X?"
- "Have we considered Y?"

## Technical Preferences

### Kotlin
- [Preference 1]
- [Preference 2]

### Java
- [Preference 1]
- [Preference 2]

## Anti-Patterns Flagged

- Hardcoded configuration values
- Missing error handling
- Large methods without extraction

## Statistics

- Average comments per PR: 5.6
- Most commented file types: .kt (423), .java (289), .md (87)
- Comment distribution: 65% suggestions, 20% blocking issues, 15% nitpicks
- Trivial/approval-only comments excluded from analysis: <N>
```

Save to: `<storage-dir>/profiles/<username>-summary.md`

#### Step 2.7: Generate Agent File

After generating the profile, create a Claude agent file so the user can invoke `review-as-<username>` as an agent directly.

1. **Ask user where to write the agent file**:
   ```
   Would you like to generate a Claude agent for quick access?

   This creates an agent you can invoke as `review-as-<username>` from any project.

   Options:
   1. Default: ~/.claude/agents/review-as-<username>.md
   2. Custom path

   Enter path or press Enter for default:
   ```

2. **Generate the agent file** at the chosen path with this structure:

   ```markdown
   ---
   name: review-as-<username>
   description: Review code changes as <display_name> would, based on their learned review style from <total_prs> PRs
   model: inherit
   tools: ["Read", "Bash", "Grep", "Glob"]
   ---

   You are reviewing code as <display_name>. Apply their review style based on this profile.

   ## Review Style

   <Inline profile.review_style.summary>

   **Key Traits**: <Inline profile.review_style.key_traits as comma-separated list>

   **Tone**: <Inline profile.review_style.tone>

   ## Top Focus Areas

   1. <focus_areas[0].category> (<focus_areas[0].frequency>%): <focus_areas[0].patterns>
   2. <focus_areas[1].category> (<focus_areas[1].frequency>%): <focus_areas[1].patterns>
   3. <focus_areas[2].category> (<focus_areas[2].frequency>%): <focus_areas[2].patterns>

   ## Common Patterns

   **Opening Phrases**: <common_patterns.opening_phrases>

   **Suggestion Style**: <common_patterns.suggestion_style>

   ## Technical Preferences

   <For each language in technical_preferences.languages, list the preferences>

   ## Anti-Patterns to Flag

   <Inline anti_patterns_flagged as bulleted list>

   ## Instructions

   1. Get the diff: `git diff main...HEAD` (or ask user for base branch)
   2. For each changed file, review using <display_name>'s style
   3. Output inline comments with file paths and line numbers
   4. Provide overall feedback summarizing key findings
   5. Use their typical tone, phrases, and focus areas
   6. Flag anti-patterns they commonly catch
   7. Skip auto-generated files (lock files, build outputs)
   ```

3. **Create parent directory** if it doesn't exist:
   ```bash
   mkdir -p ~/.claude/agents/
   ```

4. **Write the file** with all profile data inlined (not referenced — the agent file must be self-contained).

#### Step 2.8: Display Results

Show the user:

```
✅ Profile generated successfully!

📊 Analysis complete:
   - Analyzed 150 PRs with 847 comments
   - Date range: 2024-01-15 to 2026-02-27
   - Top focus areas: Documentation (42%), Code Structure (31%), Testing (18%)

📁 Files created:
   - Profile: <storage-dir>/profiles/<username>.json
   - Summary: <storage-dir>/profiles/<username>-summary.md
   - Agent: ~/.claude/agents/review-as-<username>.md

💡 Next steps:
   - Review the summary: cat <storage-dir>/profiles/<username>-summary.md
   - Use the review skill: /review-as <username>
   - Or invoke the agent directly: review-as-<username>
```

---

## Error Handling

### Network Errors

If `gh` commands fail with network errors:
1. Wait 5 seconds
2. Retry with exponential backoff (5s, 10s, 20s, 40s)
3. After 4 retries, log error and skip to next PR
4. Continue processing remaining PRs

### API Errors

- **404 Not Found**: PR is private or deleted - skip and log
- **403 Forbidden**: Authentication issue - stop and prompt user to re-authenticate
- **422 Unprocessable**: Invalid parameters - log error and skip
- **500/503 Server Error**: GitHub outage - wait and retry

### Data Validation

After fetching each PR:
- Verify JSON is valid
- Ensure required fields exist (`id`, `body`, `path` for inline comments)
- Skip malformed comments and log warning

### Interrupted Progress

If the skill is interrupted during Phase 1:
- Simply re-run the same `fetch_reviews.py` command — it resumes from the last checkpoint automatically
- The script saves a `checkpoint.json` every 10 PRs and skips already-cached PR files
- Display: "Resuming from checkpoint: PR 78/150..."

### Insufficient Data

If fewer than 30 PRs are fetched:
- Warn user: "Only {count} PRs found. Profile may be less accurate. Continue? (y/n)"
- Allow user to proceed or abort

---

## Context Management

**Phase 1 (Fetching)**: Handled entirely by `fetch_reviews.py` — no AI analysis needed.

**Phase 2 (Analysis)**: Read cached files in batches of ~15 PRs to keep context manageable. Adjust batch size based on comment density — PRs with many long comments may need smaller batches.

---

## Data Schemas

### Cached PR Review File

Schema for `<storage-dir>/cache/reviews/<username>/pr-{owner}-{repo}-{number}.json`:

This schema is produced by the `fetch_reviews.py` script. Each file contains PR metadata, inline comments, review comments, and a file type summary.

```json
{
  "pr_number": 2598,
  "repository": "owner/repository-name",
  "pr_title": "Add config analysis skill",
  "pr_url": "https://github.com/owner/repository-name/pull/2598",
  "closed_at": "2026-02-27T10:30:00Z",
  "inline_comments": [
    {
      "id": 1771821,
      "path": ".claude/skill/analyze-active-published-config.md",
      "position": 1,
      "original_line": 1,
      "body": "You could make this quite a bit easier...",
      "diff_hunk": "@@ -0,0 +1,244 @@\n+# Analyze Active Published Config in DynamoDB",
      "created_at": "2026-02-26T23:00:19Z",
      "side": "RIGHT",
      "file_extension": "md",
      "trivial": false
    }
  ],
  "review_comments": [
    {
      "id": 2267044,
      "state": "COMMENTED",
      "body": "Overall looks good. Just a few suggestions.",
      "submitted_at": "2026-02-26T23:00:19Z",
      "trivial": false
    },
    {
      "id": 2267045,
      "state": "APPROVED",
      "body": "LGTM",
      "submitted_at": "2026-02-26T23:05:00Z",
      "trivial": true
    }
  ],
  "file_types": {
    "md": 1,
    "kt": 3,
    "Dockerfile": 1
  }
}
```

**Key fields added by the fetch script**:
- `trivial` (boolean): `true` for LGTM, "Looks good", emoji-only, and similar approval comments. Exclude these from theme analysis but count them in statistics.
- `file_extension` (string): Normalized file extension via `pathlib`. Handles special cases: `Dockerfile`, `.gitignore`, extensionless files → `"no-extension"`.
- `file_types` (object): Per-PR summary of file extensions mentioned in inline comments.

---

## Examples

### Example 1: Public GitHub User

```bash
# User invokes skill with username
/build-code-reviewer-profile --user=octocat

# Skill uses default host (github.com)
> Fetching display name from GitHub...
> Display name: The Octocat

# Skill prompts for storage location
> Where would you like to store profile data?
> 1. Default: /tmp/code-reviewer-profiles/ (ephemeral)
> 2. Permanent: ~/.claude/reviewer-profiles/
>
> Enter path or press Enter for default:

# User chooses permanent location
~/.claude/reviewer-profiles/

> 📋 Configuration:
>    Username: octocat
>    Display name: The Octocat
>    GitHub host: github.com
>    Storage: ~/.claude/reviewer-profiles/
>    PR limit: 150
>
> Continue? (y/n) y

# Phase 1: Fetching
> Initializing storage at ~/.claude/reviewer-profiles/...
> Searching for PRs reviewed by octocat on github.com...
> Found 150 PRs to analyze
>
> Fetching PR 1/150: cli/cli#2598...
> Fetching PR 2/150: cli/cli#2597...
> ...
> ✅ Fetched 150 PRs with 847 comments
>
> Phase 1 complete! Beginning analysis...

# Phase 2: Analysis
> Analyzing comment themes (batch 1/10)...
> Analyzing comment themes (batch 2/10)...
> ...
> Extracting review style patterns...
> Identifying technical preferences...
>
> ✅ Profile generated successfully!
>
> 📊 Analysis complete:
>    - Analyzed 150 PRs with 847 comments
>    - Date range: 2024-01-15 to 2026-02-27
>    - Top focus areas: Documentation (42%), Code Structure (31%), Testing (18%)
>
> Files created:
>   - Profile: ~/.claude/reviewer-profiles/profiles/octocat.json
>   - Summary: ~/.claude/reviewer-profiles/profiles/octocat-summary.md
>
> Next: Review the summary to understand The Octocat's review style
```

### Example 2: Enterprise GitHub with Interactive Prompts

```bash
# User invokes skill without arguments
/build-code-reviewer-profile

# Skill prompts for username
> Which GitHub user would you like to build a profile for?
>
> Enter GitHub username: jsmith

# Skill prompts for host
> Which GitHub instance?
>
> 1. github.com (public GitHub) [default]
> 2. GitHub Enterprise (custom host)
>
> Choose option (1/2) or press Enter for default: 2

> Enter GitHub Enterprise hostname: github.enterprise.com

# Fetches display name
> Fetching display name from GitHub...
> Display name: Jane Smith

# Skill prompts for storage location
> Where would you like to store profile data?
> 1. Default: /tmp/code-reviewer-profiles/ (ephemeral)
> 2. Permanent: ~/.claude/reviewer-profiles/
>
> Enter path or press Enter for default:

# User presses Enter for default
/tmp/code-reviewer-profiles/

> 📋 Configuration:
>    Username: jsmith
>    Display name: Jane Smith
>    GitHub host: github.enterprise.com
>    Storage: /tmp/code-reviewer-profiles/
>    PR limit: 150
>
> Continue? (y/n) y

# Phase 1: Fetching
> Initializing storage at /tmp/code-reviewer-profiles/...
> Verifying GitHub authentication to github.enterprise.com...
> ✓ Authenticated as jsmith
>
> Searching for PRs reviewed by jsmith on github.enterprise.com...
> Found 132 PRs to analyze
>
> Fetching PR 1/132: acme/api-service#1234...
> ...
> ✅ Fetched 132 PRs with 623 comments
>
> Phase 1 complete! Beginning analysis...

# Phase 2: Analysis
> [Analysis output similar to Example 1...]
>
> ✅ Profile generated successfully!
>
> Files created:
>   - Profile: /tmp/code-reviewer-profiles/profiles/jsmith.json
>   - Summary: /tmp/code-reviewer-profiles/profiles/jsmith-summary.md
```

### Example 3: Ben Gaudiosi (Concrete Example)

```bash
# Building a profile for Ben Gaudiosi on Toast's GitHub Enterprise
/build-code-reviewer-profile --user=bgaudiosi --host=github.enterprise.com --storage=~/.claude/profiles/

> Fetching display name from GitHub...
> Display name: Ben Gaudiosi

> 📋 Configuration:
>    Username: bgaudiosi
>    Display name: Ben Gaudiosi
>    GitHub host: github.enterprise.com
>    Storage: ~/.claude/profiles/
>    PR limit: 150
>
> Continue? (y/n) y

# [Phase 1 and Phase 2 proceed as above...]

> ✅ Profile generated successfully!
>
> 📊 Analysis complete:
>    - Analyzed 150 PRs with 847 comments
>    - Date range: 2024-01-15 to 2026-02-27
>    - Top focus areas: Documentation (42%), Code Structure (31%), Testing (18%)
>
> Files created:
>   - Profile: ~/.claude/profiles/profiles/bgaudiosi.json
>   - Summary: ~/.claude/profiles/profiles/bgaudiosi-summary.md
>
> Next: Use /review-as-ben to apply this profile to code reviews
```

---

## Success Criteria

The skill is successful when:
- ✅ At least 100 PRs with review comments are fetched
- ✅ Cache files are created with valid JSON
- ✅ Index file accurately reflects cached data
- ✅ Profile JSON contains all required fields
- ✅ Summary markdown is human-readable and accurate
- ✅ All errors are handled gracefully
- ✅ User receives clear feedback on progress and results

---

## Notes

- **No Rate Limits**: Be respectful with API calls
- **Incremental Progress**: Save progress every 10 PRs to enable resume on interruption
- **Batch Processing**: Read cached data in batches to manage context
- **Storage Flexibility**: Support both ephemeral (/tmp) and permanent storage
- **Future Enhancement**: Could support `--refresh` flag to fetch only new reviews since last run
