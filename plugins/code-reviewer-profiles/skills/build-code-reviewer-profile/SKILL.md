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

#### Step 1.2: Fetch PRs Reviewed by User

Use GitHub CLI to search for PRs where the user left reviews:

```bash
gh search prs \
  --reviewed-by=<username> \
  --merged \
  --limit <limit> \
  --json number,title,repository,mergedAt,url \
  --hostname <github-host>
```

**Note**: For public GitHub (github.com), the `--hostname` parameter can be omitted.

**Pagination strategy** (if you need more than 100 PRs):
- After fetching the first batch, note the oldest `mergedAt` date
- Fetch next batch with: `--merged-at "<{oldest_date}"`
- Continue until you have ~150 PRs or reach desired limit

**Error handling**:
- If search fails with rate limit: wait and retry with exponential backoff
- If search returns 0 results: verify username and GitHub authentication
- Log any errors to `<storage-dir>/cache/errors.log`

#### Step 1.3: Fetch Review Comments for Each PR

For each PR in the search results:

1. **Fetch inline comments** (comments on specific code lines):
   ```bash
   gh api repos/{owner}/{repo}/pulls/{number}/comments --paginate --hostname <github-host>
   ```

   **Note**: For public GitHub (github.com), the `--hostname` parameter can be omitted.

   Key fields to capture:
   - `id`: Comment ID
   - `path`: File path
   - `position`: Line position in diff
   - `original_line`: Original line number
   - `body`: Comment text
   - `diff_hunk`: Code context (3 lines before/after)
   - `created_at`: Timestamp
   - `side`: LEFT or RIGHT (old vs new code)
   - `user.login`: Comment author

   **Filter**: Only keep comments where `user.login === "<username>"`

2. **Fetch review-level comments** (overall PR comments):
   ```bash
   gh api repos/{owner}/{repo}/pulls/{number}/reviews --hostname <github-host>
   ```

   **Note**: For public GitHub (github.com), the `--hostname` parameter can be omitted.

   Key fields to capture:
   - `id`: Review ID
   - `state`: APPROVED, COMMENTED, CHANGES_REQUESTED
   - `body`: Review summary text
   - `submitted_at`: Timestamp
   - `user.login`: Reviewer

   **Filter**: Only keep reviews where `user.login === "bgaudiosi"`

3. **Save to cache file**:
   ```
   <storage-dir>/cache/reviews/<username>/pr-{repo}-{number}.json
   ```

   Use the schema defined in the plan (see "Data Schemas" section below).

4. **Progress tracking**:
   - Show progress: "Fetching PR 45/150: service#2598..."
   - Save progress after every 10 PRs in case of interruption
   - Skip PRs that return 404 (deleted/private) and log them

#### Step 1.4: Build Index File

After fetching all PRs, create an index for efficient lookup:

```json
{
  "username": "<username>",
  "github_host": "<github-host>",
  "display_name": "<display-name>",
  "last_updated": "2026-02-27T15:00:00Z",
  "total_prs_cached": 150,
  "total_comments": 847,
  "repositories": [
    {
      "name": "owner/repository-name",
      "pr_count": 120,
      "comment_count": 689
    }
  ],
  "pr_list": [
    {
      "pr_number": 2598,
      "repository": "owner/repository-name",
      "file": "pr-service-2598.json",
      "comment_count": 11,
      "merged_at": "2026-02-27T10:30:00Z"
    }
  ]
}
```

Save to: `<storage-dir>/cache/reviews/<username>/index.json`

**End of Phase 1**: Display summary to user:
```
✅ Fetched 150 PRs with 847 review comments
📁 Cached in: <storage-dir>/cache/reviews/<username>/
📊 Next: Analyzing patterns to build <display-name>'s profile...
```

---

### Phase 2: Analyze and Build Profile (AI-Powered)

This phase analyzes the cached data using AI in batches for token efficiency.

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

**Process**:
1. Load PRs in batches of 15
2. For each batch, extract all inline and review comments
3. Send to AI with prompt:

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

**Token estimate**: 15 PRs × ~850 tokens/PR = ~12,750 input tokens per batch
- Total batches: 150 PRs ÷ 15 = 10 batches
- Total input: ~127k tokens
- Total output: ~8k tokens (aggregated theme data)

#### Step 2.3: Analyze Review Style (Single Batch)

**Goal**: Understand the reviewer's tone, typical phrases, and suggestion patterns

**Process**:
1. Select a representative sample of 30 comments across different themes
2. Send to AI with prompt:

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

**Token estimate**: ~10k tokens total (input + output)

#### Step 2.4: Extract Technical Preferences (Batch Processing)

**Goal**: Identify language-specific patterns, framework preferences, and anti-patterns

**Process**:
1. Group comments by file extension (.kt, .java, .md, etc.)
2. Sample 30 representative PRs across different repos and file types
3. For each file type, send batch to AI:

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

**Token estimate**: ~10k tokens per batch
- 3-4 batches (one per major file type)
- Total: ~30-40k tokens

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
```

Save to: `<storage-dir>/profiles/<username>-summary.md`

#### Step 2.7: Display Results

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

💡 Next steps:
   - Review the summary: cat <storage-dir>/profiles/<username>-summary.md
   - Apply to code review with this profile (future feature)
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
- On restart, check the index file for last processed PR
- Resume from where it left off
- Display: "Resuming from PR 78/150..."

### Insufficient Data

If fewer than 30 PRs are fetched:
- Warn user: "Only {count} PRs found. Profile may be less accurate. Continue? (y/n)"
- Allow user to proceed or abort

---

## Token Budget

**Phase 1 (Fetching)**: 0 tokens (no AI)

**Phase 2 (Analysis)**:
- Theme extraction: ~127k input + ~8k output = ~135k tokens
- Style analysis: ~10k tokens
- Technical preferences: ~30-40k tokens
- **Total**: ~175-185k tokens (within 200k budget)

---

## Data Schemas

### Cached PR Review File

Schema for `<storage-dir>/cache/reviews/<username>/pr-{repo}-{number}.json`:

```json
{
  "metadata": {
    "username": "<username>",
    "github_host": "<github-host>",
    "pr_number": 2598,
    "repository": {
      "owner": "owner",
      "name": "repository",
      "full_name": "owner/repository-name"
    },
    "pr_title": "Add config analysis skill",
    "pr_url": "https://github.com/owner/repository-name/pull/2598",
    "created_at": "2026-02-26T23:00:19Z",
    "merged_at": "2026-02-27T10:30:00Z",
    "fetched_at": "2026-02-27T15:00:00Z"
  },
  "inline_comments": [
    {
      "id": 1771821,
      "path": ".claude/skill/analyze-active-published-config.md",
      "position": 1,
      "original_line": 1,
      "body": "You could make this quite a bit easier...",
      "diff_hunk": "@@ -0,0 +1,244 @@\n+# Analyze Active Published Config in DynamoDB",
      "created_at": "2026-02-26T23:00:19Z",
      "side": "RIGHT"
    }
  ],
  "review_comments": [
    {
      "id": 2267044,
      "state": "COMMENTED",
      "body": "Overall looks good. Just a few suggestions.",
      "submitted_at": "2026-02-26T23:00:19Z"
    }
  ],
  "statistics": {
    "total_inline_comments": 11,
    "total_review_comments": 1,
    "files_commented": 3
  }
}
```

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
- ✅ Token usage stays within ~185k tokens
- ✅ All errors are handled gracefully
- ✅ User receives clear feedback on progress and results

---

## Notes

- **No Rate Limits**: Be respectful with API calls
- **Incremental Progress**: Save progress every 10 PRs to enable resume on interruption
- **Token Efficiency**: Batch processing keeps analysis within budget
- **Storage Flexibility**: Support both ephemeral (/tmp) and permanent storage
- **Future Enhancement**: Could support `--refresh` flag to fetch only new reviews since last run
