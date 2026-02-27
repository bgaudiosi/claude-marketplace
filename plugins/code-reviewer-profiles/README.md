# Code Reviewer Profiles

Learn and apply code review styles from GitHub history. This plugin analyzes a person's past code reviews to understand their style, preferences, and patterns, then applies that learned style to review new code.

## Purpose

This plugin enables:
- **Automated self-review**: Review your own code in the style of an experienced reviewer before creating a PR
- **Understanding reviewer patterns**: Learn what matters most to specific reviewers
- **Consistency in code review**: Apply consistent review standards across teams
- **Learning from experience**: Understand experienced reviewers' patterns and preferences

## How It Works

1. **Fetch review history** from GitHub using the GitHub CLI
2. **Analyze patterns** using AI to extract style, preferences, and focus areas
3. **Generate a profile** capturing the reviewer's approach
4. **Apply the profile** to review new code changes in that reviewer's style

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

## Data Storage

By default, profile data is stored in `/tmp/code-reviewer-profiles/`:

```
/tmp/code-reviewer-profiles/
├── profiles/
│   ├── <username>.json           # Reviewer profile
│   └── <username>-summary.md      # Human-readable summary
└── cache/
    └── reviews/
        └── <username>/
            ├── index.json                # Metadata index
            └── pr-{repo}-{number}.json   # Individual PRs
```

**Note**: `/tmp` is ephemeral and cleared on system restart. When running `/build-code-reviewer-profile`, you'll be prompted to specify a permanent storage location if you want the profile to persist (e.g., `~/.claude/reviewer-profiles/`).

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

- **Applying a review**: ~10k tokens per review
  - Profile summary: ~2k tokens
  - Code diff: ~5k tokens (typical PR)
  - Review output: ~3k tokens

## Example Workflow

```bash
# 1. Build a reviewer profile (one-time setup)
/build-code-reviewer-profile --user=<username>

# When prompted, choose storage location:
# - Press Enter for /tmp (ephemeral, cleared on restart)
# - Or specify: ~/.claude/reviewer-profiles/ (permanent)

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
2. If you stored it in a custom location, provide that path when prompted
3. Check that the profile file exists: `ls /tmp/code-reviewer-profiles/profiles/`

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
3. For each file/chunk, generate review comments using the profile as context
4. Format output as inline comments with line references
5. Provide overall feedback matching the reviewer's typical approach

## Contributing

This plugin is part of the Claude Marketplace. To suggest improvements or report issues, please open an issue in the marketplace repository.
