# Available Plugins

This document lists all available Claude Code plugins and their commands in the ai-helpers repository.

- [Code Reviewer Profiles](#code-reviewer-profiles-plugin)

### Code Reviewer Profiles Plugin

Learn and apply code review styles from GitHub history

**Commands:**
- **`/code-reviewer-profiles:build-code-reviewer-profile` `[--user=<username>] [--host=<hostname>] [--storage=<path>]`** - Fetch a GitHub user's review history and generate a reviewer profile + agent
- **`/code-reviewer-profiles:review-as` `<username> [branch] [--files <paths>] [--profile <path>]`** - Review code changes using a reviewer's learned style

See [plugins/code-reviewer-profiles/](plugins/code-reviewer-profiles/) for detailed documentation.
