# Code Reviewer Profiles

Learn and apply code review styles from GitHub history. This plugin analyzes a person's past code reviews to understand their style, preferences, and patterns, then applies that learned style — combined with a structured review methodology — to review new code.

## Purpose

This plugin enables:
- **Substantive code review**: Structured methodology checks functional correctness, naming, intent comments, hackiness, test coverage, and optimization — with findings categorized by priority (P1/P2/P3)
- **Persona-driven feedback**: Reviews are expressed in the reviewer's learned tone, phrases, and focus areas
- **Automated self-review**: Review your own code in the style of an experienced reviewer before creating a PR
- **Consistency in code review**: Apply consistent review standards across teams

## How It Works

1. **Fetch review history** from GitHub using the GitHub CLI
2. **Analyze patterns** using AI to extract style, preferences, and focus areas
3. **Generate a profile** capturing the reviewer's approach
4. **Apply the profile** to review new code changes — the review methodology determines **what** to check, the profile determines **how** findings are expressed

## Available Skills

### `/build-code-reviewer-profile`

Fetches any GitHub user's review history and generates a reviewer profile.

**What it does:**
- Searches for PRs reviewed by the specified GitHub user
- Supports both public GitHub (github.com) and GitHub Enterprise instances
- Fetches inline and review-level comments with code context
- Caches raw review data for efficient reprocessing
- Analyzes patterns to build a comprehensive reviewer profile
- Generates both JSON profile and human-readable summary

**Example usage:**
```bash
# Public GitHub user
/build-code-reviewer-profile --user=octocat

# Enterprise GitHub user
/build-code-reviewer-profile --user=bgaudiosi --host=github.enterprise.com

# Interactive (will prompt for username and host)
/build-code-reviewer-profile
```

### `/review-as-ben`

Reviews your code changes using Ben Gaudiosi's learned review style.

**What it does:**
- Loads Ben's reviewer profile
- Gets your code changes via git diff
- Generates inline review comments matching Ben's style
- Provides overall feedback in Ben's tone and approach

**Example usage:**
```bash
# Review current branch against main
/review-as-ben

# Review specific branch
/review-as-ben feature/my-feature

# Review specific files
/review-as-ben --files src/services/ConfigService.kt
```

## Prerequisites

### GitHub CLI Authentication

You must have the GitHub CLI (`gh`) installed and authenticated to your GitHub instance:

```bash
# Check if authenticated
gh auth status

# For public GitHub:
gh auth login

# For GitHub Enterprise:
gh auth login --hostname your-github-host.com
```

Required scopes:
- `repo` (to read PR and review data)
- `read:org` (to search across organization repositories)

### Git Repository

For `/review-as-ben`, you must be in a git repository with code changes to review.

## References

The `references/` directory contains review methodology documents used during code review:

- **`review-principles.md`** — Concrete good/bad examples for intent comments, naming, hackiness, documentation/tests, and language-specific patterns. These principles are language-agnostic (examples happen to be Kotlin/TypeScript but apply universally).

## Data Storage

Profile data is stored in `~/.claude/reviewer-profiles/`:

```
~/.claude/reviewer-profiles/
├── profiles/
│   ├── <username>.json           # Reviewer profile
│   └── <username>-summary.md      # Human-readable summary
└── cache/
    └── reviews/
        └── <username>/
            ├── index.json                # Metadata index
            └── pr-{repo}-{number}.json   # Individual PRs
```

### Storage Structure

- **profiles/**: Generated reviewer profiles (JSON + markdown summary)
- **cache/reviews/**: Raw review data fetched from GitHub
- **cache/errors.log**: Error log for troubleshooting

## Token Usage

The plugin is designed to be token-efficient:

- **Building a profile**: ~125k tokens total
  - Theme extraction: ~76k tokens (6-8 batches of 15 PRs each)
  - Style analysis: ~10k tokens (1 batch)
  - Technical preferences: ~30k tokens (3-4 batches)

- **Applying a review**: ~10-12k tokens per file
  - Methodology checklist + review principles: ~1.5k tokens
  - Profile context (persona): ~2k tokens
  - Code diff: ~3-5k tokens (typical file)
  - Review output: ~3-4k tokens

## Example Workflow

```bash
# 1. Build a reviewer profile (one-time setup)
/build-code-reviewer-profile --user=<username>

# 2. Create a feature branch and make changes
git checkout -b feature/my-new-feature
# ... make code changes ...

# 3. Review your changes in that reviewer's style
# (Note: Currently only /review-as-ben is available)
/review-as-ben

# 4. Review the feedback and iterate
# ... make improvements based on review ...

# 5. Create PR with confidence
git push origin feature/my-new-feature
gh pr create --draft
```

## Troubleshooting

### "Profile not found" error

If `/review-as-ben` can't find the profile:
1. Run `/build-code-reviewer-profile --user=bgaudiosi` first to create Ben's profile
2. If you stored it in a custom location, use the `--profile` flag
3. Check that the profile file exists: `ls ~/.claude/reviewer-profiles/profiles/`

### "gh: command not found"

Install the GitHub CLI:
```bash
brew install gh
```

### "gh api: HTTP 404: Not Found"

This usually means:
- The PR is private or deleted (skipped automatically)
- You don't have access to the repository
- The GitHub hostname is incorrect

Check your authentication: `gh auth status`

### Network errors during fetch

The skill will automatically retry with exponential backoff. If fetching is interrupted, progress is saved incrementally and will resume from the last successful PR.

### Large diff warnings

If your code changes are very large (>2000 lines), the review will be broken into file-by-file batches to stay within token limits.

## Current Limitations

This plugin now supports building profiles for any GitHub user, but profile application is currently limited:

- ✅ **Profile building**: Works for any GitHub user on public or enterprise GitHub
- ⚠️ **Profile application**: Currently limited to Ben Gaudiosi (`/review-as-ben`)

## Future Enhancements

- `review-with-profile --user=<username>` - Apply any reviewer's profile to code reviews
- `compare-reviewers --users=user1,user2` - Compare review styles side-by-side
- `combine-reviewers --users=user1,user2` - Merge multiple review perspectives
- `refresh-profile --user=<username>` - Incrementally update profiles with new reviews

## Technical Details

### Data Sources

Reviews are fetched using the GitHub CLI:
- `gh search prs --reviewed-by=<user>` - Find reviewed PRs
- `gh api repos/{owner}/{repo}/pulls/{number}/comments` - Inline comments with code context
- `gh api repos/{owner}/{repo}/pulls/{number}/reviews` - Review-level comments

### Profile Generation

The profile captures:
- **Review style**: Overall approach, tone, and key traits
- **Focus areas**: Categories like Documentation, Code Structure, Testing (with frequency)
- **Common patterns**: Typical phrases, suggestion style, questions asked
- **Technical preferences**: Language-specific patterns, framework preferences
- **Anti-patterns**: Issues commonly flagged
- **Statistics**: Comment distribution, file types, averages

### Review Application

When applying a profile:
1. Load the reviewer's profile (style, preferences, patterns)
2. Get code changes via `git diff`
3. Auto-detect build system and run build/tests if available
4. Load review methodology checklist and review principles reference
5. For each file/chunk, generate review using a single prompt combining methodology checklist + persona overlay
6. Categorize findings by priority: P1 (must fix), P2 (should fix), P3 (consider)
7. Format output with priority grouping, line references, and checklist coverage

## Contributing

This plugin is part of the Claude Marketplace. To suggest improvements or report issues, please open an issue in the marketplace repository.
