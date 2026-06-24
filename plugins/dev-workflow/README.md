# Dev Workflow

Everyday development workflow skills — TDD-driven bug solving, pull request creation and feedback, and Jira ticket management. These are general-purpose, repo-agnostic skills with no host- or project-specific assumptions.

## Available Skills

### `/bug-solver-tdd`
Solve a bug using test-driven development. Validates a theory logically, then writes a test that reproduces the bug **before** writing any fix. "This isn't actually a bug" is an acceptable outcome. Matches the project's existing test conventions.

### `/create-pull-request`
Create a draft pull request for the current branch. Uses the repo's PR template, pushes the latest commit first, branches off the default branch if you're on it, and keeps descriptions succinct. Picks up ticket context from the branch name prefix (e.g. `PROJ-123-...`) when present.

### `/address-pr-feedback <PR>`
Address reviewer feedback on a GitHub PR: make code changes as commits where warranted, then draft and post reply comments — one per thread, always after confirmation.

### `/acli`
Reference for the Atlassian CLI (`acli`) — view, search, edit, comment on, and create Jira work items, including writing formatted descriptions via Atlassian Document Format (ADF).

### `/create-jira-ticket`
Create a well-structured Jira ticket (Description / Implementation Details / Acceptance Criteria), investigating the repo for implementation context. Prompts for the project key and derives GitHub code links from the repo's actual remote.

### `/do-ticket <TICKET>`
Read a Jira ticket via `acli`, form a plan, and create a `proj-123-...` branch before starting work.

## Prerequisites

- **GitHub skills** (`create-pull-request`, `address-pr-feedback`) require the GitHub CLI (`gh`), authenticated. For GitHub Enterprise, set `GH_HOST`.
- **Jira skills** (`acli`, `create-jira-ticket`, `do-ticket`) require the Atlassian CLI (`acli`), authenticated via `acli jira auth`.
