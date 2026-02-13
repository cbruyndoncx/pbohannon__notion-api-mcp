# Notion CLI

A comprehensive, standalone command-line interface for the Notion API. Provides complete access to Notion's features through an intuitive, human-friendly CLI with smart caching and path-based navigation.

## Features

- ✅ **Complete API Coverage** - All Notion API endpoints and parameters
- ✅ **30+ Block Types** - Support for all Notion block types
- ✅ **Database Operations** - Create, query, update databases with filters and sorts
- ✅ **Todo Management** - Full task management with properties (priority, tags, due dates, status)
- ✅ **Smart Caching** - Name-to-ID resolution with automatic caching
- ✅ **Path Navigation** - Use `"Parent/Child"` paths instead of UUIDs
- ✅ **Standalone** - Single executable with PEP 723 inline dependencies
- ✅ **Human-Friendly** - Intuitive commands with helpful shortcuts

## Quick Start

```bash
# Set your API key
export NOTION_API_KEY="ntn_your_integration_token_here"

# Verify connection
uv run scripts/notion.py verify-connection

# List all pages
uv run scripts/notion.py list pages

# Add a page with icon and cover
uv run scripts/notion.py add page \
    --title "Meeting Notes" \
    --parent "Work" \
    --icon "📝" \
    --cover "https://example.com/cover.jpg"

# Add a todo
uv run scripts/notion.py add todo \
    --title "Complete project" \
    --database "Tasks" \
    --priority High \
    --tags "work,urgent" \
    --due-date "2026-12-31"

# Query database with filters
uv run scripts/notion.py query database "Tasks" \
    --status "In Progress" \
    --priority High
```

## Installation

### Option 1: Standalone Usage (Recommended)

The CLI uses PEP 723 inline dependencies and can run directly with `uv`:

```bash
# No installation required!
uv run scripts/notion.py --help
```

### Option 2: Install Dependencies

```bash
# Install uv if not already installed
pip install uv

# Install project dependencies
uv pip install -e .

# Or install dev dependencies for testing
uv pip install -e ".[dev]"
```

## Getting Started

### 1. Create a Notion Integration

1. Go to https://www.notion.so/my-integrations
2. Click "New integration"
3. Name your integration (e.g., "My CLI Tool")
4. Copy the "Internal Integration Token" - this is your `NOTION_API_KEY`
   - Should start with "ntn_"

### 2. Connect Integration to Your Pages/Databases

1. Open the Notion page or database you want to access
2. Click the ••• menu in the top right
3. Select "Add connections" and choose your integration
4. The integration now has access to that page and its children

### 3. Set Environment Variables

```bash
# Required
export NOTION_API_KEY="ntn_your_integration_token_here"

# Optional (for defaults)
export NOTION_DATABASE_ID="your_default_database_id"
export NOTION_PARENT_PAGE_ID="your_default_parent_page_id"
```

Or create a `.env` file:

```env
NOTION_API_KEY=ntn_your_integration_token_here
NOTION_DATABASE_ID=your_database_id
NOTION_PARENT_PAGE_ID=your_parent_page_id
```

## Complete CLI Reference

### Diagnostics

```bash
# Verify API connection
uv run scripts/notion.py verify-connection

# Check environment configuration
uv run scripts/notion.py check-config
```

### List & Search

```bash
# List all pages
uv run scripts/notion.py list pages

# List all databases
uv run scripts/notion.py list databases --refresh

# Search for content
uv run scripts/notion.py search "project"
uv run scripts/notion.py search --type page "meeting"
```

### Pages

```bash
# Create page with all options
uv run scripts/notion.py add page \
    --title "Meeting Notes" \
    --parent "Work/Projects" \
    --icon "📝" \
    --cover "https://example.com/cover.jpg" \
    --content "Initial content"

# Get page
uv run scripts/notion.py get page "Meeting Notes"
uv run scripts/notion.py get page "Work/Projects/Q1"

# Update page
uv run scripts/notion.py update page "Notes" --title "Updated Title"
uv run scripts/notion.py update page "Old Page" --archive
uv run scripts/notion.py update page "Archived" --restore

# Move page
uv run scripts/notion.py move page "Note" --to "Archive"

# Delete page (archives it)
uv run scripts/notion.py delete page "Old Notes"
```

### Databases

```bash
# Create database with template
uv run scripts/notion.py add database \
    --title "Tasks" \
    --parent "Work" \
    --template tasks

# Available templates: tasks, notes, contacts

# Create custom database
uv run scripts/notion.py add database \
    --title "CRM" \
    --parent "Work" \
    --properties '{"Name": {"title": {}}, "Email": {"email": {}}}'

# Query database with filters
uv run scripts/notion.py query database "Tasks" \
    --status "In Progress" \
    --priority High \
    --due-before "2026-03-01"

# Query with custom filter
uv run scripts/notion.py query database "Tasks" \
    --filter '{"property": "Status", "status": {"equals": "Done"}}' \
    --sorts '[{"property": "Priority", "direction": "descending"}]'

# Fetch all results with pagination
uv run scripts/notion.py query database "Tasks" --all

# Get database info
uv run scripts/notion.py get database "Tasks"

# Update database
uv run scripts/notion.py update database "Tasks" --title "My Tasks"
```

### Todos

```bash
# Add todo with properties
uv run scripts/notion.py add todo \
    --database "Tasks" \
    --title "Complete project" \
    --description "Finish all remaining tasks" \
    --due-date "2026-12-31" \
    --priority "High" \
    --tags "work,urgent" \
    --status "In Progress"

# Search todos with filters
uv run scripts/notion.py todos search \
    --database "Tasks" \
    --status "In Progress" \
    --priority High \
    --due-before "2026-03-01"

# Search by tags
uv run scripts/notion.py todos search --tags urgent --limit 10
```

### Blocks - All 30+ Types

**Text Blocks:**

```bash
# Paragraphs and headings
uv run scripts/notion.py blocks add "Notes" --type paragraph --text "Hello world"
uv run scripts/notion.py blocks add "Notes" --type heading_1 --text "Main Title"
uv run scripts/notion.py blocks add "Notes" --type heading_2 --text "Section"
uv run scripts/notion.py blocks add "Notes" --type heading_3 --text "Subsection"

# Lists
uv run scripts/notion.py blocks add "Notes" --type bulleted_list_item --text "Item 1"
uv run scripts/notion.py blocks add "Notes" --type numbered_list_item --text "Step 1"

# Todo items
uv run scripts/notion.py blocks add "Notes" --type to_do --text "Task" --checked

# Other text blocks
uv run scripts/notion.py blocks add "Notes" --type quote --text "Quote"
uv run scripts/notion.py blocks add "Notes" --type toggle --text "Toggle content"
```

**Code & Equations:**

```bash
# Code blocks
uv run scripts/notion.py blocks add "Notes" \
    --type code \
    --text "print('hello')" \
    --language python

# Equations
uv run scripts/notion.py blocks add "Notes" \
    --type equation \
    --expression "E=mc^2"
```

**Callouts:**

```bash
uv run scripts/notion.py blocks add "Notes" \
    --type callout \
    --text "Important note" \
    --icon "💡"
```

**Media Blocks:**

```bash
# Images, videos, files
uv run scripts/notion.py blocks add "Notes" \
    --type image \
    --url "https://example.com/image.jpg"

uv run scripts/notion.py blocks add "Notes" \
    --type video \
    --url "https://youtube.com/watch?v=..."

# Bookmarks and embeds
uv run scripts/notion.py blocks add "Notes" \
    --type bookmark \
    --url "https://example.com"
```

**Layout Blocks:**

```bash
uv run scripts/notion.py blocks add "Notes" --type divider
uv run scripts/notion.py blocks add "Notes" --type table_of_contents
```

**Block Operations:**

```bash
# List blocks
uv run scripts/notion.py blocks list "Quick Note"

# Get specific block
uv run scripts/notion.py get block <block-id>

# Update block
uv run scripts/notion.py update block <block-id> --text "Updated content"

# Delete block
uv run scripts/notion.py blocks delete <block-id>
```

**Subtasks:**

```bash
# Add subtask to todo
uv run scripts/notion.py blocks subtasks add <todo-block-id> --text "Subtask 1"

# List subtasks
uv run scripts/notion.py blocks subtasks list <todo-block-id>

# Mark complete/incomplete
uv run scripts/notion.py blocks subtasks check <subtask-id>
uv run scripts/notion.py blocks subtasks uncheck <subtask-id>
```

### Cache Management

```bash
# Refresh cache of pages and databases
uv run scripts/notion.py refresh-cache
```

## Human-Friendly Features

### 1. Path-Based Navigation

Use readable paths instead of UUIDs:

```bash
# Instead of:
uv run scripts/notion.py get page "123e4567-e89b-12d3-a456-426614174000"

# Use:
uv run scripts/notion.py get page "Work/Projects/Q1 Planning"
```

### 2. Smart Caching

- Automatic caching of page/database names to IDs
- Cache refreshes every 24 hours
- Manual refresh: `uv run scripts/notion.py refresh-cache`
- Fallback to API search if not in cache

### 3. Template Support

Predefined database templates for common use cases:

```bash
uv run scripts/notion.py add database --title "Tasks" --template tasks
uv run scripts/notion.py add database --title "Notes" --template notes
uv run scripts/notion.py add database --title "CRM" --template contacts
```

### 4. Filter Shortcuts

Easy filters for common queries:

```bash
# Instead of complex JSON:
uv run scripts/notion.py query database "Tasks" \
    --status "Done" \
    --priority High

# Equivalent to:
uv run scripts/notion.py query database "Tasks" \
    --filter '{"and": [{"property": "Status", ...}, {"property": "Priority", ...}]}'
```

## Environment Variables

The CLI uses these environment variables:

- `NOTION_API_KEY` - **Required**: Notion integration token
- `NOTION_DATABASE_ID` - Optional: Default database for todos
- `NOTION_PARENT_PAGE_ID` - Optional: Default parent for new pages/databases

You can:
1. Set environment variables: `export NOTION_API_KEY="ntn_..."`
2. Create a `.env` file in the project root
3. Override with CLI flags: `--api-key "ntn_..."`

## Examples

See the `examples/` directory for real-world usage examples:

- `backup-database.sh` - Backup database to JSON
- `bulk-create-pages.sh` - Bulk page creation
- `daily-standup-automation.sh` - Daily standup automation
- `weekly-review.sh` - Weekly review workflow

## Documentation

- [CLI Test Plan](docs/CLI_TEST_PLAN.md) - Comprehensive test plan with 140+ test cases
- [CLI Migration Guide](docs/CLI_MIGRATION_GUIDE.md) - Migration from older CLI versions
- [Quick Reference](CLI_QUICK_REFERENCE.md) - Command quick reference
- [Implementation Summary](IMPLEMENTATION_SUMMARY.md) - Implementation details

## Development

### Running Tests

```bash
# Install dev dependencies
uv pip install -e ".[dev]"

# Run all tests
pytest

# Run with coverage
pytest --cov=scripts.notion --cov-report=term-missing

# Run specific test file
pytest tests/cli/test_cli_helpers.py -v
```

### Code Style

```bash
# Format code
black scripts/

# Check formatting
black scripts/ --check
```

## Troubleshooting

### Common Issues

**401 Authentication Error**
- Check that `NOTION_API_KEY` is set correctly
- Verify token starts with "ntn_"
- Ensure integration has access to the pages/databases

**404 Not Found**
- Verify the page/database exists
- Check integration has been connected to the page
- Try refreshing cache: `uv run scripts/notion.py refresh-cache`

**Name Not Found in Cache**
- Run `uv run scripts/notion.py refresh-cache`
- Check spelling of page/database name
- Use exact case-sensitive name or UUID

### Getting Help

```bash
# General help
uv run scripts/notion.py --help

# Command-specific help
uv run scripts/notion.py add --help
uv run scripts/notion.py blocks add --help
```

## Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Submit a pull request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- Built with [Click](https://click.palletsprojects.com/) for CLI framework
- Uses [httpx](https://www.python-httpx.org/) for async HTTP requests
- Follows [PEP 723](https://peps.python.org/pep-0723/) for inline script dependencies
