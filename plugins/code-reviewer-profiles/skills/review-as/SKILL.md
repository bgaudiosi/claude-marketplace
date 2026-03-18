---
name: review-as
description: Review code changes using a reviewer's learned style combined with rigorous review methodology
version: 0.3.0
tags: [github, code-review, automation, reviewer-profile]
---

# Review As

Reviews your code changes using a reviewer's learned style from their GitHub history, layered on top of a structured review methodology. The profile determines HOW findings are expressed; the methodology determines WHAT to check.

## Review Philosophy

Code should be:
1. **Functional first** — Compiles, tests pass, logic is correct
2. **Clean and maintainable second** — Intent comments, verbose naming, no hackiness
3. **Optimized third** — Performance considerations (only after 1 & 2)

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

1. **Reviewer Profile** — Must exist at:
   - `~/.claude/reviewer-profiles/profiles/<username>.json`
   - Or custom location via `--profile <path>`

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

1. **Search for profile**:
   - If `--profile` flag provided, use that path
   - Otherwise, check `~/.claude/reviewer-profiles/profiles/<username>.json`

2. **If not found**, prompt user:
   ```
   Reviewer profile for '<username>' not found.

   Searched:
   - ~/.claude/reviewer-profiles/profiles/<username>.json

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

### Step 2.5: Build Validation (Optional)

Auto-detect the project's build system and run build + tests if possible.

1. **Detect build system** by checking for:
   - `build.gradle*` or `pom.xml` → Gradle/Maven (run `./gradlew build` or `mvn verify`)
   - `package.json` → Node (run `npm test` or `yarn test`)
   - `Cargo.toml` → Rust (run `cargo build && cargo test`)
   - `go.mod` → Go (run `go build ./... && go test ./...`)
   - `Makefile` → Make (run `make test`)
   - `Gemfile` → Ruby (run `bundle exec rake test`)
   - `pyproject.toml` or `setup.py` → Python (run `pytest`)

2. **Run build + tests** if detected:
   - Set a 2-minute timeout
   - Record pass/fail/skipped status
   - If no build system found or build takes >2min, skip gracefully

3. **Feed results into review**:
   - Build failures become P1 findings
   - Test failures become P1 findings with specific test names
   - Build success is noted in the review header

### Step 3: Process Diff for Review

#### Load Review Principles

Read `references/review-principles.md` (relative to this skill: `../../references/review-principles.md`) for detailed review context with concrete examples.

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

For each file/chunk, generate review using a single prompt that combines the methodology checklist with the reviewer's persona overlay. This is a single pass — not two separate passes — for token efficiency.

#### Construct AI Prompt

Include in the prompt:

1. **Methodology Checklist** (~1.5k tokens):
   ```
   Review this code change against the following checklist. For each area,
   note any findings with the appropriate priority level.

   CHECKLIST:
   1. Functional Correctness (P1 — must fix)
      - Logic errors, off-by-ones, race conditions
      - Error handling gaps (swallowed exceptions, missing cases)
      - Build/test results: {build_status}
      - Null safety issues, type mismatches

   2. Intent & Documentation (P2 — should fix)
      - Comments that don't match the code they describe
      - Missing "why" comments on non-obvious logic
      - Public API docs missing or outdated
      - Comments with major typos or grammar issues

   3. Naming & Readability (P2 — should fix)
      - Abbreviated variable/function names (use verbose names)
      - Standard abbreviations OK: id, url, html, json, xml, dto, api
      - Unclear or misleading names

   4. Hackiness & Code Quality (P2 — should fix)
      - TODO comments used as excuse for poor code
      - Workarounds without explanation or ticket reference
      - Copy-pasted code that should be extracted
      - Magic numbers without named constants

   5. Test Coverage (P2 — should fix)
      - New functionality missing tests
      - Tests only covering happy path (need edge cases, error cases)
      - Test names that don't describe behavior

   6. Optimization (P3 — consider)
      - Only flag clearly impactful performance issues
      - N+1 queries, unnecessary allocations in hot paths
      - Do NOT nitpick micro-optimizations

   For detailed examples of each principle, the review-principles.md
   reference has been loaded as context.
   ```

2. **Persona Overlay** (~2k tokens):
   ```
   Express all findings in {display_name}'s review style:

   **Review Style**: {profile.review_style.summary}
   **Key Traits**: {profile.review_style.key_traits}
   **Tone**: {profile.review_style.tone}

   **Top Focus Areas** (give these extra scrutiny):
   1. {focus_areas[0].category} ({focus_areas[0].frequency}%): {focus_areas[0].patterns}
   2. {focus_areas[1].category} ({focus_areas[1].frequency}%): {focus_areas[1].patterns}
   3. {focus_areas[2].category} ({focus_areas[2].frequency}%): {focus_areas[2].patterns}

   **Common Opening Phrases**: {common_patterns.opening_phrases}
   **Suggestion Style**: {common_patterns.suggestion_style}

   **Technical Preferences for {file_extension}**:
   {technical_preferences.languages[language].preferences}

   **Anti-patterns to Flag**: {anti_patterns_flagged}

   IMPORTANT:
   - P1 issues are ALWAYS flagged regardless of persona focus areas
   - Reviewer's focus areas weight which P2 issues get more scrutiny
   - Use the reviewer's typical phrases and tone for all comments
   - Reference specific line numbers from the diff
   ```

3. **Code Diff** (~3-5k tokens):
   ```
   File: {file_path}

   {diff_content}
   ```

4. **Output Format Instructions**:
   ```
   Output as JSON:
   {
     "p1_issues": [
       {
         "file": "<file_path>",
         "line": <line_number>,
         "category": "<checklist category>",
         "comment": "<review comment in reviewer's voice>",
         "suggestion": "<optional code suggestion>"
       }
     ],
     "p2_issues": [...],
     "p3_issues": [...],
     "overall_feedback": "<high-level observations in reviewer's voice>",
     "checklist_coverage": ["functional_correctness", "intent_documentation", ...]
   }
   ```

#### Parse AI Response

Extract priority-categorized findings and overall feedback from JSON response.

### Step 5: Format Review Output

Display the review grouped by priority:

```markdown
## Code Review (as {display_name})

**Branch**: feature/my-feature → main
**Files changed**: 5
**Build**: Passed / Failed / Skipped

---

### P1: Must Fix

**services/ConfigService.kt:47** `[Functional Correctness]`
{Comment in reviewer's voice about the issue}
```suggestion
return repository.findById(id).orElseThrow {
    NotFoundException("Config not found: $id")
}
```

**services/DataSync.kt:89** `[Functional Correctness]`
{Comment about swallowed exception}

---

### P2: Should Fix

**services/ConfigService.kt:65** `[Naming]`
{Comment about abbreviated variable name}

**services/OrderService.kt:112** `[Intent & Documentation]`
{Comment about missing "why" comment}

**tests/ConfigServiceTest.kt** `[Test Coverage]`
{Comment about missing edge case tests}

---

### P3: Consider

**services/Repository.kt:120** `[Optimization]`
{Comment about N+1 query}

---

### Overall Feedback

{High-level observations in the reviewer's style}

---

**Checklist coverage**: 6/6 areas checked (Functional, Intent, Naming, Hackiness, Tests, Optimization)
**Profile source**: <username>.json ({total_prs} PRs analyzed, generated {date})
```

### Step 6: Display Review Statistics

After showing the review, display summary stats:

```
Review Summary:
   - Files reviewed: 5
   - Build/tests: Passed
   - P1 (must fix): 2
   - P2 (should fix): 5
   - P3 (consider): 1
   - Checklist coverage: 6/6
   - Focus areas covered: Documentation (4), Code Structure (3), Error Handling (3)
   - Profile: {total_prs} PRs analyzed

Tip: Address P1 issues before creating your PR. P2s align with {display_name}'s expectations.
```

---

## Token Management

### Token Budget Per Review

Typical breakdown for a medium PR:
- Methodology checklist + review principles: ~1.5k tokens
- Profile context (persona): ~2k tokens
- Code diff (per file): ~3-5k tokens
- Generated review: ~3-4k tokens
- **Total per file**: ~10-12k tokens

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
Reviewer profile for '<username>' not found.

Run `/build-code-reviewer-profile --user=<username>` first to generate the profile, or specify a custom location with:
   /review-as <username> --profile <path-to-profile>
```

### No Git Repository

If not in a git repo:
```
Not in a git repository.

This skill requires a git repository to review code changes.
```

### No Changes to Review

If diff is empty:
```
No changes found to review.

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

### Example 1: Full Review with Build Validation

```bash
git checkout feature/add-config-caching
/review-as octocat

# Output:
> Loading octocat's reviewer profile...
> Profile loaded (150 PRs analyzed)
>
> Analyzing changes on feature/add-config-caching vs main...
> Found 3 files with changes (428 lines)
>
> Running build validation... Passed (12 tests, 0 failures)
>
> Generating review as The Octocat...
>
> ## Code Review (as The Octocat)
>
> **Branch**: feature/add-config-caching → main
> **Files changed**: 3
> **Build**: Passed (12 tests)
>
> ### P1: Must Fix
>
> **services/CacheService.kt:89** `[Functional Correctness]`
> Cache eviction never triggers — TTL comparison is inverted
>
> ### P2: Should Fix
>
> **services/ConfigService.kt:47** `[Naming]`
> `cfg` → `configuration` — let's be explicit here
>
> **services/ConfigService.kt:65** `[Intent & Documentation]`
> This caching logic is subtle — add a comment explaining the eviction strategy
>
> ### P3: Consider
>
> (none)
>
> ### Overall Feedback
> Good approach to caching! The TTL bug in CacheService is the main blocker.
>
> **Checklist coverage**: 6/6
```

### Example 2: Profile Not Found

```bash
/review-as jsmith

# Output:
> Reviewer profile for 'jsmith' not found.
>
> Searched:
> - ~/.claude/reviewer-profiles/profiles/jsmith.json
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
   # ... address P1 and P2 feedback ...
   git add .
   git commit -m "Address review feedback"
   gh pr create --draft
   ```

3. **Periodic refresh**: Run `/build-code-reviewer-profile --user=<username>` monthly to keep profile current

---

## Success Criteria

The skill is successful when:
- Reviewer profile is loaded correctly from username lookup
- Code changes are fetched via git diff
- Build/tests are run when a build system is detected
- Review comments are categorized by priority (P1/P2/P3)
- P1 functional issues are always caught regardless of persona
- Review comments match the reviewer's style and tone
- Focus areas align with the reviewer's priorities
- All 6 checklist areas are evaluated
- Output is formatted with priority grouping and line references
- Token usage stays within ~12k per file
- Large diffs are handled gracefully

---

## Notes

- **Token Efficiency**: Uses ~10-12k tokens per file review (single combined pass)
- **Profile Freshness**: Warns if profile is >30 days old
- **File Filtering**: Skips files the reviewer rarely reviews (auto-generated, etc.)
- **Graceful Degradation**: Falls back to simpler review if full analysis fails
- **Build Validation**: Auto-detects build system, skips if not found or >2min
- **Not a Replacement**: This is for self-review — still get human review before merging!
