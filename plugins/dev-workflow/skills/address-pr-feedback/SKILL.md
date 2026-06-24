---
name: address-pr-feedback
arguments: PR
description: Use this skill to draft and post replies to review feedback left on a GitHub PR. Use this when the user wants to respond to reviewer comments in the comment threads (as opposed to making code changes, for which you should make changes as commits instead).
allowed-tools:
  - Bash
  - Read
  - Edit
  - Write
  - Glob
  - Grep
  - AskUserQuestion
  - WebFetch
  - WebSearch
  - ToolSearch
---

## Guidelines
NEVER automatically respond to comments without asking first. Only respond after getting confirmation from the user.
ONLY leave one response per comment. Before commenting, double-check that no additional comments have been added in
that comment thread.

ALWAYS respond in the comment thread if there is one. Do not just leave comments on the top level of PR responding
to comments made in a thread. It is okay to leave top level comments when responding to other top level comments.

If the repository uses a GitHub Enterprise host, set the `GH_HOST` environment variable accordingly when running
`gh` commands (check the project's CLAUDE.md for the correct host).

## Task
Please address feedback for the PR: $PR

To do this, find the branch, and check that branch out. Before checking out that branch (if we're coming from another),
verify there are no uncommitted changes on the current branch. If there are, ask if the user wants to commit them first
or stash them.

When addressing feedback, do the following:
1) Evaluate whether or not we should do what the commenter is asking. Ensure their suggestion is correct first of all,
then ensure that it is safe and makes the code more maintainable.
2) If we don't want to continue, come up with a reason, and print that out for the user to respond with. We can end here.
3) If we do want to implement the change, try and do it as its own commit.

After making all the changes and committing that code, and pushing it up to remote, begin looping through the comments
and drafting responses. Again, DO NOT RESPOND WITHOUT ASKING PERMISSION. Some example responses:

> Good suggestion - implemented in commit <Commit URL>
> Done here - <Commit URL>
> Excellent idea - <Commit URL>
> Test added - <Commit URL>
> Good call! - <Commit URL>
> I'm going to leave this change for a future PR, I'd like to leave this change as-is for now since this won't change the functionality.
> I'm not sure I agree - can you elaborate?

After drafting responses, begin to offer comment options — use `AskUserQuestion` with preview Markdown to present choices:
  - **Option A (Brief)** — the concisest version of the comment (one short sentence)
  - **Option B (Detailed)** — a slightly longer version with more context (one to two sentences)
  - **Ignore** — skip this issue and move to the next
  - The user can also choose "Other" to provide their own wording

After the user selects an option, leave it as a comment.
