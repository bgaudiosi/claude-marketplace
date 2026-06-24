---
name: acli
description: Use Atlassian CLI (acli) to read, search, edit, and comment on Jira work items
---

# Atlassian CLI (acli) for Jira Work Items

Use the `acli` command-line tool to interact with Jira tickets directly from the command line. This skill enables you to view ticket details, make edits, add comments, and search for work items.

In the examples below, `PROJ` is a placeholder project key and `PROJ-123` a placeholder ticket key — substitute your actual project key and ticket keys.

## Core Commands

### Viewing Work Items
Use `acli jira workitem view [KEY]` to retrieve information about a Jira ticket:

```bash
# View a ticket with default fields
acli jira workitem view PROJ-123

# View with all fields
acli jira workitem view PROJ-123 --fields '*all'

# View specific fields only
acli jira workitem view PROJ-123 --fields 'summary,description,assignee,status,comment'

# Get JSON output for programmatic use
acli jira workitem view PROJ-123 --json
```

Default fields returned: key, issuetype, summary, status, assignee, description

### Editing Work Items
Use `acli jira workitem edit` to modify ticket fields:

```bash
# Edit a single ticket's summary
acli jira workitem edit --key "PROJ-123" --summary "Updated summary text"

# Edit description (inline)
acli jira workitem edit --key "PROJ-123" --description "New description text"

# Edit description from file
acli jira workitem edit --key "PROJ-123" --description-file "./description.txt"

# Change assignee
acli jira workitem edit --key "PROJ-123" --assignee "user@example.com"

# Self-assign
acli jira workitem edit --key "PROJ-123" --assignee "@me"

# Edit labels (replaces existing)
acli jira workitem edit --key "PROJ-123" --labels "backend,urgent"

# Remove labels
acli jira workitem edit --key "PROJ-123" --remove-labels "old-label"

# Edit multiple fields at once
acli jira workitem edit --key "PROJ-123" --summary "New summary" --assignee "@me" --yes
```

**Important**: Use `--yes` flag to skip confirmation prompts when you're certain about the changes.

### Searching Work Items
Use `acli jira workitem search` to find tickets using JQL (Jira Query Language):

```bash
# Search by project
acli jira workitem search --jql "project = PROJ"

# Search assigned to you
acli jira workitem search --jql "assignee = currentUser() AND status != Done"

# Search with specific status
acli jira workitem search --jql "project = PROJ AND status = 'In Development'"

# Search with custom fields
acli jira workitem search --jql "project = PROJ" --fields "key,summary,assignee,priority"

# Count results
acli jira workitem search --jql "project = PROJ AND status = 'To Do'" --count

# Get all results with pagination
acli jira workitem search --jql "project = PROJ" --paginate

# Get JSON output
acli jira workitem search --jql "project = PROJ" --json

# Limit results
acli jira workitem search --jql "project = PROJ" --limit 10
```

### Creating Work Items
Use `acli jira workitem create` to create new tickets:

```bash
# Create a basic story
acli jira workitem create --project PROJ --type Story --summary "My ticket title"

# Create with a plain-text description
acli jira workitem create --project PROJ --type Story --summary "Title" --description "Plain text description"

# Create with ADF (Atlassian Document Format) description from a JSON file — REQUIRED for formatted descriptions
acli jira workitem create --project PROJ --type Story --summary "Title" --from-json workitem.json
```

**CRITICAL — Description formatting**: Passing `--description` sends plain text. Jira stores it as a single unformatted paragraph — `##` headers and `*` bullets appear as literal characters, not formatting. To get real headings, bullet lists, code blocks, and inline code, you **must** write the description as [Atlassian Document Format (ADF)](https://developer.atlassian.com/cloud/jira/platform/apis/document/structure/) JSON and pass it via `--from-json`.

**ADF JSON structure** for `--from-json` (the file must contain a top-level `fields` key):

```json
{
  "fields": {
    "summary": "My ticket title",
    "description": {
      "version": 1,
      "type": "doc",
      "content": [
        {
          "type": "heading",
          "attrs": {"level": 2},
          "content": [{"type": "text", "text": "Description"}]
        },
        {
          "type": "paragraph",
          "content": [{"type": "text", "text": "Body text here."}]
        },
        {
          "type": "bulletList",
          "content": [
            {
              "type": "listItem",
              "content": [{"type": "paragraph", "content": [{"type": "text", "text": "Bullet item"}]}]
            }
          ]
        },
        {
          "type": "codeBlock",
          "attrs": {},
          "content": [{"type": "text", "text": "code here"}]
        }
      ]
    }
  }
}
```

Common ADF node types: `heading` (attrs: `level` 1-6), `paragraph`, `bulletList` / `orderedList`, `listItem`, `codeBlock`, `text`. Inline marks on text nodes: `{"type": "code"}`, `{"type": "strong"}`, `{"type": "em"}`, `{"type": "link", "attrs": {"href": "..."}}`.

Always write descriptions as ADF via `--from-json` when the content has any structure (headings, lists, code). Only use `--description` for single-sentence plain-text tickets.

### Adding Comments
Use `acli jira workitem comment create` to add comments to tickets:

```bash
# Add a simple comment
acli jira workitem comment create --key "PROJ-123" --body "This is my comment"

# Add comment from file
acli jira workitem comment create --key "PROJ-123" --body-file "./comment.txt"

# Comment on multiple tickets via JQL
acli jira workitem comment create --jql "project = PROJ AND assignee = currentUser()" --body "Bulk comment"
```

## Common Workflows

### Investigating a Ticket
1. View the ticket with all fields: `acli jira workitem view KEY-123 --fields '*all'`
2. Check comments: Include `comment` in the fields list
3. Review related tickets: Look at the links/subtasks in the output

### Updating Ticket Status
1. First view the ticket to understand current state
2. Make necessary edits: `acli jira workitem edit --key "KEY-123" --summary "..." --yes`
3. Add a comment explaining changes: `acli jira workitem comment create --key "KEY-123" --body "..."`

### Searching for Related Work
1. Use JQL to find related tickets: `acli jira workitem search --jql "..."`
2. Review the results and identify relevant tickets
3. View specific tickets for more details

## Guidelines

### Safety and Best Practices
- **ALWAYS view a ticket before editing** to understand its current state
- **Use `--yes` flag carefully** - it skips confirmation prompts
- **Test JQL queries** with `--count` first before bulk operations
- **Avoid bulk edits** unless explicitly requested by the user
- **Be specific with field selections** to reduce noise and improve performance
- **Prefer smaller, targeted changes** over large bulk updates

### When to Use acli
- Reading Jira ticket details, descriptions, and comments
- Making targeted edits to ticket fields (summary, description, labels, assignee)
- Searching for tickets using JQL queries
- Adding comments to document findings or updates
- Checking ticket status and current assignee

### When NOT to Use acli
- For complex workflows requiring multiple dependent operations (consider breaking into steps)
- When the user hasn't provided a specific ticket key or search criteria
- For operations that could accidentally affect many tickets without review

### Field Names Reference
Common Jira fields you can use:
- `summary` - Ticket title
- `description` - Full description
- `status` - Current status (e.g., "To Do", "In Progress", "Done")
- `assignee` - Person assigned to the ticket
- `reporter` - Person who created the ticket
- `priority` - Priority level
- `labels` - Tags/labels
- `comment` - All comments on the ticket
- `issuetype` - Type (Bug, Story, Task, etc.)
- `project` - Project key

### JQL Tips
- Use `currentUser()` for the logged-in user
- Use `AND`, `OR`, `NOT` for boolean logic
- Use quotes for multi-word values: `status = "In Progress"`
- Use `!=` for not equals
- Common operators: `=`, `!=`, `>`, `<`, `>=`, `<=`, `~` (contains), `IN`, `NOT IN`
- Order results: add `ORDER BY created DESC` to JQL queries

## Examples

### Example 1: Review a bug ticket
```bash
# Get full ticket details
acli jira workitem view PROJ-123 --fields '*all'

# Check just the description and comments
acli jira workitem view PROJ-123 --fields 'description,comment'
```

### Example 2: Update ticket after investigating
```bash
# View current state
acli jira workitem view PROJ-123

# Add findings as a comment
acli jira workitem comment create --key "PROJ-123" --body "Found the root cause in PaymentService.java:45"

# Update summary to be more specific
acli jira workitem edit --key "PROJ-123" --summary "PaymentService throws NPE when cart is empty" --yes
```

### Example 3: Find all your in-progress tickets
```bash
# Search for your active work
acli jira workitem search --jql "assignee = currentUser() AND status = 'In Development'" --fields "key,summary,status"

# Count how many tickets you have
acli jira workitem search --jql "assignee = currentUser() AND status != Done" --count
```

### Example 4: Find tickets by text search
```bash
# Search for tickets mentioning "timeout"
acli jira workitem search --jql "project = PROJ AND text ~ 'timeout'" --fields "key,summary"
```

## Error Handling

If you encounter authentication errors, the user may need to run:
```bash
acli jira auth
```

If a command fails:
1. Check that the ticket key is valid and exists
2. Verify you have permissions to perform the operation
3. Ensure JQL syntax is correct (use quotes, proper operators)
4. Check that field names are spelled correctly and exist in the Jira instance
