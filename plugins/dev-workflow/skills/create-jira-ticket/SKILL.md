---
name: create-jira-ticket
description: Use this skill when creating Jira tickets.
---

## Your Task
Create a Jira ticket using the following context provided by the user:
#$ARGUMENTS

Investigate the repo for how this may actually be implemented and any files that may need to change.
Ensure that we're currently on the main branch before going too deep. `development` or `master` are okay too depending on the repo.

After the ticket has been created, figure out which parent to assign to the ticket. This can vary a lot
based on the project we're in - the best approach here is to list all open epics and have the user pick which
one.

If there is any ambiguity, feel free to ask the user for more details.

Creating and editing the ticket should utilize the Atlassian Jira CLI tool (see the `acli` skill). For a structured description, write a temporary ADF JSON payload, pass it to `acli` via `--from-json`, then remove the temp file afterward. Don't leave scratch files behind.

When linking to code, always use GitHub links. Derive the host and repo from the repository's actual remote
(`git remote get-url origin`) rather than assuming a host. For example, for a repo on github.com at
`owner/my-service`, link to CLAUDE.md as `https://github.com/owner/my-service/blob/main/CLAUDE.md`. If the
remote is a GitHub Enterprise host, use that host instead.

## Jira Project
Ask the user which Jira project the ticket belongs to if it isn't obvious. If the repo or team has an
established default project, infer it and confirm with the user.

## Ticket Type
Generally, we should use the following rules for determining ticket type:
* Story: A feature or refactor
* Bug: A bug, self explanatory
* Task: An administrative task, generally doesn't require writing code. e.g. "Call X API for Y customer"
* Spike: A research task that requires some deeper investigation, will usually have some kind of document as output.

## Title Format
The Jira ticket title should have this format: "[service-name] Brief Description of Issue"
"service-name" in the above references the deployable artifact associated with this ticket. If you're unsure,
the name of the repo we're in is a good place to start. If the repo follows a convention of prefixing names
(e.g. an org prefix like `acme-`), strip that prefix to get the service name.

# Jira Ticket Format
Use the following format for any Jira tickets you create.

## Description
Describe the story/bug here. Ensure to mention customer impact as well as any other related tickets.
This section should be non-technical, as much as is possible.

## Implementation Details
This section should be a bit more technical and describe:
1) Suspected areas where the developer will need to add/edit code
2) Possible root causes
We should put GitHub links here of specific files.

## Acceptance Criteria
* A bullet-pointed list describing the behavior when this ticket is complete
