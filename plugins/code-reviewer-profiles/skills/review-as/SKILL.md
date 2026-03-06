---
name: review-as
description: Review code changes using a reviewer's learned style from their GitHub history
version: 0.2.0
tags: [github, code-review, automation, reviewer-profile]
---

# Review As

Reviews your code changes using a reviewer's learned style from their GitHub history. Provides inline comments and overall feedback matching their patterns, tone, and technical preferences.

## When to Use This Skill

Use this skill when:
- You want to self-review code before creating a PR
- You want feedback in a specific reviewer's style
- You're curious how a teammate might review your changes
- You want to catch issues a reviewer typically flags

**Best used for**:
- Pre-PR self-review
- Learning a reviewer's patterns
- Ensuring consistency with a reviewer's expectations
- Catching common issues early

## Required Argument

`<username>` — the reviewer whose profile to load (e.g., `/review-as octocat`)

## Prerequisites

### Required

1. **Reviewer Profile** — Must exist at one of (checked in order):
   - `~/.claude/reviewer-profiles/profiles/<username>.json`
   - `/tmp/code-reviewer-profiles/profiles/<username>.json`
   - Custom location via `--profile <path>`

   If not found, run `/build-code-reviewer-profile --user=<username>` first.

2. **Git Repository** — Must be in a git repository with:
   - Committed changes on a feature branch, OR
   - Uncommitted changes to review

3. **Base Branch** — Usually `main` or `master` (auto-detected)

### Optional Arguments

- `[branch-name]` — Branch to review (default: current branch vs main)
- `--files <paths>` — Review only specific files
- `--context <lines>` — Lines of context in diff (default: 3)
- `--profile <path>` — Use profile from custom location

## Implementation Steps

### Step 0: Parse Username

1. **Extract `<username>`** from the first argument (e.g., `/review-as octocat` → `octocat`)
2. If no username provided, prompt:
   ```
   Which reviewer's style would you like to use?

   Enter GitHub username: _
   ```

### Step 1: Locate Reviewer Profile

1. **Search for profile** in order:
   - `~/.claude/reviewer-profiles/profiles/<username>.json`
   - `/tmp/code-reviewer-profiles/profiles/<username>.json`
   - If `--profile` flag provided, use that path instead

2. **If not found**, prompt user:
   ```
   ❌ Reviewer profile for '<username>' not found.

   Searched:
   - ~/.claude/reviewer-profiles/profiles/<username>.json
   - /tmp/code-reviewer-profiles/profiles/<username>.json

   Options:
   1. Run /build-code-reviewer-profile --user=<username> to create it
   2. Specify custom profile location with --profile <path>
   ```

3. **Load profile JSON** and extract key sections:
   - `display_name` (used throughout output instead of username)
   - `review_style.summary`
   - `review_style.key_traits`
   - `review_style.tone`
   - `focus_areas` (top 3)
   - `common_patterns`
   - `technical_preferences` (for relevant languages)
   - `anti_patterns_flagged`

4. **Verify profile freshness**:
   - Check `generated_at` timestamp
   - If older than 30 days, warn: "Profile is {age} old. Consider running /build-code-reviewer-profile --user=<username> to refresh."

### Step 2: Get Code Changes

#### Determine What to Review

1. **Parse arguments**:
   - If `[branch-name]` provided: review that branch vs base
   - If `--files` provided: review only those files
   - Otherwise: review current branch vs base

2. **Detect base branch**:
   ```bash
   # Try to get the base branch from git
   git symbolic-ref refs/remotes/origin/HEAD | sed 's@^refs/remotes/origin/@@'
   ```

   Common bases: `main`, `master`, `develop`

3. **Check for changes**:
   ```bash
   # For committed changes
   git diff <base-branch>...<current-branch> --name-only

   # For uncommitted changes
   git diff HEAD --name-only
   ```

4. **If no changes**, exit with message:
   ```
   No changes found to review.

   Make sure you have:
   - Committed changes on your branch, OR
   - Uncommitted changes to review
   ```

#### Fetch Diff with Context

Get the unified diff with context:

```bash
git diff <base-branch>...<current-branch> --unified=3
```

**Output format**:
```diff
diff --git a/services/ConfigService.kt b/services/ConfigService.kt
index abc123..def456 100644
--- a/services/ConfigService.kt
+++ b/services/ConfigService.kt
@@ -45,6 +45,10 @@ class ConfigService {
     fun getConfig(id: String): Config? {
-        return repository.findById(id)
+        return repository.findById(id).orElse(null)
     }
```

### Step 3: Process Diff for Review

#### Split Into Reviewable Chunks

1. **Parse diff** into file-level chunks
2. **For each file**:
   - Extract file path
   - Extract hunks (sections of changes)
   - Group related changes (within ~50 lines)

3. **If diff is large** (>2000 lines):
   - Review file-by-file instead of all at once
   - Show progress: "Reviewing file 3/12: ConfigService.kt..."

#### Filter by File Type

Use the reviewer's profile to prioritize:
- Check `statistics.most_commented_file_types`
- For file types they rarely comment on (e.g., `.json`, `.xml`), provide lighter review

### Step 4: Generate Review Comments

For each file/chunk, generate review using the reviewer's profile as context.

#### Construct AI Prompt

Include in the prompt:

1. **Profile Context** (~2k tokens):
   ```
   You are reviewing code as {display_name}. Use their review style:

   **Review Style**: {profile.review_style.summary}

   **Key Traits**: {profile.review_style.key_traits}

   **Tone**: {profile.review_style.tone}

   **Top Focus Areas**:
   1. {focus_areas[0].category} ({focus_areas[0].frequency}%): {focus_areas[0].patterns}
   2. {focus_areas[1].category} ({focus_areas[1].frequency}%): {focus_areas[1].patterns}
   3. {focus_areas[2].category} ({focus_areas[2].frequency}%): {focus_areas[2].patterns}

   **Common Opening Phrases**: {common_patterns.opening_phrases}

   **Suggestion Style**: {common_patterns.suggestion_style}

   **Technical Preferences for {file_extension}**:
   {technical_preferences.languages[language].preferences}

   **Anti-patterns to Flag**: {anti_patterns_flagged}
   ```

2. **Code Diff** (~5k tokens for typical file):
   ```
   Review this code change:

   File: {file_path}

   {diff_content}
   ```

3. **Instructions**:
   ```
   Provide a code review in {display_name}'s style:
   - Use their typical phrases and tone
   - Focus on their priority areas
   - Flag anti-patterns they commonly catch
   - Structure suggestions as they would (with examples, explanations, questions)
   - Reference specific line numbers from the diff

   Output format:
   {
     "inline_comments": [
       {
         "line": <line_number>,
         "comment": "<review comment in their style>"
       }
     ],
     "overall_feedback": "<high-level observations>"
   }
   ```

#### Parse AI Response

Extract inline comments and overall feedback from JSON response.

### Step 5: Format Review Output

Display the review in a readable format:

```markdown
## Code Review (as {display_name})

**Branch**: feature/my-feature
**Base**: main
**Files changed**: 5

---

### services/ConfigService.kt

**Line 47**: Consider using `Optional` more idiomatically here
You could make this more robust by handling the empty case explicitly:
```kotlin
return repository.findById(id).orElseThrow {
    NotFoundException("Config not found: $id")
}
```

**Line 65**: This method is getting large - consider extraction
Have you thought about breaking this into smaller, focused methods? For example, the validation logic could be its own method.

---

### Overall Feedback

[High-level observations in the reviewer's style]

---

**Profile source**: <username>.json ({total_prs} PRs analyzed, generated {date})
```

### Step 6: Display Review Statistics

After showing the review, display summary stats:

```
📊 Review Summary:
   - Files reviewed: 5
   - Inline comments: 12
   - Focus areas covered: Documentation (4), Code Structure (3), Error Handling (3), Style (2)
   - Review generated using profile from {total_prs} PRs

💡 Tip: Address these comments before creating your PR to align with {display_name}'s expectations.
```

---

## Token Management

### Token Budget Per Review

Typical breakdown for a medium PR:
- Profile context: ~2k tokens
- Code diff (per file): ~3-5k tokens
- Generated review: ~2-3k tokens
- **Total per file**: ~7-10k tokens

### Handling Large Diffs

If total diff exceeds 2000 lines:

1. **Break into file-by-file reviews**:
   - Review each file separately
   - Combine results at the end

2. **Show progress**:
   ```
   Large diff detected (2,847 lines across 12 files)
   Breaking into file-by-file review for better analysis...

   Reviewing file 1/12: ConfigService.kt (247 lines)...
   Reviewing file 2/12: ConfigRepository.kt (189 lines)...
   ...
   ```

3. **Token limit per file**: ~15k tokens
   - If single file exceeds this, review in chunks (methods/classes)

### Skipping Files

Skip files that:
- Are not typically reviewed by this reviewer (check profile stats)
- Are auto-generated (build outputs, lock files)
- Have no substantive changes (whitespace only)

Show: "Skipped 3 files: package-lock.json (auto-generated), ConfigTest.kt.orig (backup)"

---

## Error Handling

### Profile Not Found

If profile doesn't exist:
```
❌ Reviewer profile for '<username>' not found.

Run `/build-code-reviewer-profile --user=<username>` first to generate the profile, or specify a custom location with:
   /review-as <username> --profile <path-to-profile>
```

### No Git Repository

If not in a git repo:
```
❌ Not in a git repository.

This skill requires a git repository to review code changes.
```

### No Changes to Review

If diff is empty:
```
✅ No changes found to review.

Current state:
- Branch: feature/my-feature
- Base: main
- Status: Up to date with main

Make some code changes first, then run this skill again.
```

### Git Command Failures

If `git diff` fails:
- Check if branch exists: `git rev-parse --verify <branch>`
- Check if base branch exists: `git rev-parse --verify <base-branch>`
- Provide clear error: "Branch 'feature/xyz' not found. Did you mean 'feature/abc'?"

### AI Review Failures

If AI fails to generate review:
- Fall back to simpler prompt without full profile context
- If still fails, show: "Unable to generate review. Try reviewing smaller chunks with --files flag."

---

## Command-Line Arguments

### Basic Usage

```bash
# Review current branch against main as a specific reviewer
/review-as octocat

# Review specific branch
/review-as octocat feature/my-feature

# Review against different base
/review-as octocat feature/my-feature --base develop
```

### Advanced Options

```bash
# Review only specific files
/review-as octocat --files src/services/ConfigService.kt src/repository/ConfigRepo.kt

# Use custom profile location
/review-as octocat --profile ~/.claude/reviewer-profiles/profiles/octocat.json

# Increase diff context
/review-as octocat --context 5

# Review uncommitted changes
/review-as octocat --uncommitted
```

---

## Examples

### Example 1: Basic Review

```bash
# User has changes on feature branch
git checkout feature/add-config-caching

# Run review as a specific reviewer
/review-as octocat

# Output:
> Loading octocat's reviewer profile...
> ✅ Profile loaded (150 PRs analyzed)
>
> Analyzing changes on feature/add-config-caching vs main...
> Found 3 files with changes (428 lines)
>
> Generating review in The Octocat's style...
>
> ## Code Review (as The Octocat)
>
> ### services/ConfigService.kt
>
> **Line 56**: Consider adding a cache eviction strategy
> You could make this more robust by...
> [... rest of review ...]
```

### Example 2: Profile Not Found

```bash
/review-as jsmith

# Output:
> ❌ Reviewer profile for 'jsmith' not found.
>
> Searched:
> - ~/.claude/reviewer-profiles/profiles/jsmith.json
> - /tmp/code-reviewer-profiles/profiles/jsmith.json
>
> Options:
> 1. Run /build-code-reviewer-profile --user=jsmith to create it
> 2. Specify custom location: /review-as jsmith --profile <path>
>
> Would you like me to run /build-code-reviewer-profile --user=jsmith now? (y/n)
```

---

## Integration with Workflow

### Recommended Usage Pattern

1. **One-time setup**: Run `/build-code-reviewer-profile --user=<username>`
2. **Before every PR**:
   ```bash
   git checkout -b feature/my-feature
   # ... make changes ...
   git add .
   git commit -m "Implement feature"
   /review-as <username>
   # ... address feedback ...
   git add .
   git commit -m "Address review feedback"
   gh pr create --draft
   ```

3. **Periodic refresh**: Run `/build-code-reviewer-profile --user=<username>` monthly to keep profile current

---

## Success Criteria

The skill is successful when:
- ✅ Reviewer profile is loaded correctly from username lookup
- ✅ Code changes are fetched via git diff
- ✅ Review comments match the reviewer's style and tone
- ✅ Focus areas align with the reviewer's priorities
- ✅ Technical preferences are applied correctly
- ✅ Output is formatted clearly with line references
- ✅ Overall feedback captures the reviewer's typical approach
- ✅ Token usage stays within ~10k per file
- ✅ Large diffs are handled gracefully

---

## Notes

- **Token Efficiency**: Uses ~10k tokens per review (affordable for frequent use)
- **Profile Freshness**: Warns if profile is >30 days old
- **File Filtering**: Skips files the reviewer rarely reviews (auto-generated, etc.)
- **Graceful Degradation**: Falls back to simpler review if full analysis fails
- **Not a Replacement**: This is for self-review - still get human review before merging!
