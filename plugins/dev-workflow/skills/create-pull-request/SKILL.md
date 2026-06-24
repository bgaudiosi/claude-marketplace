---
name: create-pull-request
description: Use this skill when creating pull requests. If there are competing skill choices, use this one.
---

## Your Task
Create a pull request for the current branch. If the current branch is the default branch (main/master),
create a new branch first before opening the PR — never open a PR directly from the default branch.

Look through the git history of this branch as compared to the default branch for the code changes that
were made.

ALWAYS open the pull request in draft mode.

Ensure you use the pull request template in the current repository. This is typically found at
`.github/PULL_REQUEST_TEMPLATE.md` or some variation of that.

If there is a ticket associated with the branch - usually denoted by the prefix of the branch itself
(e.g. `PROJ-123-...`) - use that for context when creating the PR.

Ensure the latest commit is pushed to a remote before creating the PR.

Be succinct in your descriptions. Do not over-explain — communicate what changes are being made and why.

## Additional Context
#$ARGUMENTS
