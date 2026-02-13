# CLI Quick Reference

Fast reference for all Notion API CLI commands.

## Setup

```bash
export NOTION_API_KEY="ntn_your_token_here"
export NOTION_DATABASE_ID="your_database_id"  # Optional
export NOTION_PARENT_PAGE_ID="your_page_id"   # Optional
```

## Commands by Category

### 🔧 Utilities

```bash
# Verify API connection
uv run scripts/notion-utils.py verify-connection

# Get database info
uv run scripts/notion-utils.py get-database-info --database-id <id>

# Check configuration
uv run scripts/notion-utils.py check-config
```

### 📄 Pages

```bash
# Create page in database
uv run scripts/notion-pages.py create --database-id <id> --title "Title"

# Create page under page
uv run scripts/notion-pages.py create --page-id <id> --parent-type page --title "Title"

# Get page
uv run scripts/notion-pages.py get <page-id>

# Update page
uv run scripts/notion-pages.py update <page-id> --properties '{...}'

# Archive/restore page
uv run scripts/notion-pages.py archive <page-id>
uv run scripts/notion-pages.py restore <page-id>

# Get property
uv run scripts/notion-pages.py get-property <page-id> <property-id>
```

### 🗄️ Databases

```bash
# Create database
uv run scripts/notion-databases.py create \
    --parent-page-id <id> \
    --title "DB Name" \
    --properties '{...}'

# Query database
uv run scripts/notion-databases.py query --database-id <id>

# Query with filter
uv run scripts/notion-databases.py query --database-id <id> \
    --filter '{"property": "Status", "select": {"equals": "Done"}}'

# Query with sort
uv run scripts/notion-databases.py query --database-id <id> \
    --sort '[{"property": "Created", "direction": "descending"}]'

# Get database info
uv run scripts/notion-databases.py info --database-id <id>
```

### ✅ Todos

```bash
# Add todo
uv run scripts/notion-databases.py add-todo \
    --database-id <id> \
    --title "Task name" \
    [--description "Details"] \
    [--due-date "2026-12-31"] \
    [--priority "High|Medium|Low"] \
    [--tags "tag1,tag2"] \
    [--status "Not Started"]

# Search todos by status
uv run scripts/notion-databases.py search-todos \
    --database-id <id> \
    --status "In Progress"

# Search by priority
uv run scripts/notion-databases.py search-todos \
    --database-id <id> \
    --priority "High"

# Find overdue tasks
uv run scripts/notion-databases.py search-todos \
    --database-id <id> \
    --overdue-only
```

### 📝 Blocks

```bash
# Add text block
uv run scripts/notion-blocks.py add <page-id> --text "Content"

# Add blocks from JSON
uv run scripts/notion-blocks.py add <page-id> --blocks '[{...}]'

# Add after specific block
uv run scripts/notion-blocks.py add <page-id> --text "Content" --after <block-id>

# Get block
uv run scripts/notion-blocks.py get <block-id>

# List children
uv run scripts/notion-blocks.py list-children <block-id>

# Update block
uv run scripts/notion-blocks.py update <block-id> --content '{...}'

# Delete block
uv run scripts/notion-blocks.py delete <block-id>
```

## Common Patterns

### Pipeline JSON Output

```bash
# Get database info and extract properties
uv run scripts/notion-databases.py info --database-id <id> | \
    jq '.database.properties'

# Count completed tasks
uv run scripts/notion-databases.py search-todos \
    --database-id <id> \
    --status "Done" | \
    jq '.count'
```

### Environment Override

```bash
# Override with flags
uv run scripts/notion-pages.py create \
    --api-key "ntn_different_key" \
    --database-id "different_db" \
    --title "Test"
```

### Scripting

```bash
# Loop through pages
for page_id in $(cat page_ids.txt); do
    uv run scripts/notion-pages.py archive "$page_id"
done

# Conditional logic
if uv run scripts/notion-utils.py verify-connection; then
    echo "Connected!"
else
    echo "Connection failed"
    exit 1
fi
```

## Example JSON Formats

### Page Properties

```json
{
  "Status": {
    "select": {"name": "In Progress"}
  },
  "Priority": {
    "select": {"name": "High"}
  },
  "Tags": {
    "multi_select": [
      {"name": "work"},
      {"name": "urgent"}
    ]
  }
}
```

### Block Content (Paragraph)

```json
{
  "type": "paragraph",
  "paragraph": {
    "rich_text": [
      {
        "type": "text",
        "text": {"content": "Your text here"}
      }
    ]
  }
}
```

### Database Filter

```json
{
  "and": [
    {"property": "Status", "select": {"equals": "Done"}},
    {"property": "Priority", "select": {"equals": "High"}}
  ]
}
```

### Database Sort

```json
[
  {"property": "Due Date", "direction": "ascending"},
  {"property": "Priority", "direction": "descending"}
]
```

## Help Commands

Every script and command has `--help`:

```bash
# Script-level help
uv run scripts/notion-pages.py --help

# Command-level help
uv run scripts/notion-pages.py create --help
uv run scripts/notion-databases.py query --help
uv run scripts/notion-blocks.py add --help
```

## Exit Codes

All scripts follow standard exit codes:
- `0` - Success
- `1` - Error (check JSON output for details)

## Error Handling

All errors are returned as JSON:

```json
{
  "success": false,
  "error": "Error description here"
}
```

## Quick Tips

1. **JSON formatting**: Use `jq` to pretty-print output
   ```bash
   uv run scripts/notion-pages.py get <id> | jq .
   ```

2. **Save output**: Redirect to file
   ```bash
   uv run scripts/notion-databases.py query --database-id <id> > backup.json
   ```

3. **Silence uv output**: Add `2>/dev/null`
   ```bash
   uv run scripts/notion-utils.py verify-connection 2>/dev/null
   ```

4. **Test before using**: Always use `--help` first
   ```bash
   uv run scripts/notion-blocks.py add --help
   ```

## See Also

- [CLI Migration Guide](docs/CLI_MIGRATION_GUIDE.md) - Detailed migration from MCP
- [Example Scripts](examples/README.md) - Automation examples
- [Main README](README.md) - Full project documentation
