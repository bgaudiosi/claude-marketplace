---
name: do-ticket
arguments: TICKET
description: Use this skill when working on Jira tickets.
---

## Your Task
Read the contents of $TICKET using the Atlassian Jira CLI tool. This can be done with the following command:
`acli jira workitem view $TICKET`. Check out the `acli` skill for more commands.

Come up with a plan to execute this ticket. If there is any ambiguity in the ticket or if the detail
is insufficient, ask the user for more details.

If we aren't on a branch associated with this ticket, create one before doing any work. It should be of
the format `proj-123-brief-description-of-issue` - `proj-123` is just an example there of course, please use
$TICKET instead.
