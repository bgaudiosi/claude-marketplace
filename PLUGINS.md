# Available Plugins

This document lists all available Claude Code plugins and their skills in this repository.

- [Code Reviewer Profiles](#code-reviewer-profiles-plugin)
- [Dev Workflow](#dev-workflow-plugin)

### Code Reviewer Profiles Plugin

Learn and apply code review styles from GitHub history

**Skills:**
- **`/build-code-reviewer-profile`** - Fetch any GitHub user's review history and generate a code reviewer profile
- **`/review-as`** - Review code changes using a reviewer's learned style combined with rigorous review methodology

See [plugins/code-reviewer-profiles/README.md](plugins/code-reviewer-profiles/README.md) for detailed documentation.

### Dev Workflow Plugin

Everyday development workflow skills: TDD bug solving, PR creation and feedback, and Jira ticket management

**Skills:**
- **`/acli`** - Use Atlassian CLI (acli) to read, search, edit, and comment on Jira work items
- **`/address-pr-feedback`** - Use this skill to draft and post replies to review feedback left on a GitHub PR. Use this when the user wants to respond to reviewer comments in the comment threads (as opposed to making code changes, for which you should make changes as commits instead).
- **`/bug-solver-tdd`** - Solves a bug using test driven development
- **`/create-jira-ticket`** - Use this skill when creating Jira tickets.
- **`/create-pull-request`** - Use this skill when creating pull requests. If there are competing skill choices, use this one.
- **`/do-ticket`** - Use this skill when working on Jira tickets.

See [plugins/dev-workflow/README.md](plugins/dev-workflow/README.md) for detailed documentation.
