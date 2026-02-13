# Notion API MCP

A comprehensive toolkit for Notion API integration, providing both:
- **MCP Server**: AI-powered interaction through Claude Desktop and other MCP clients
- **CLI Scripts**: Direct command-line tools using `uv run` for automation and scripting

This project enables advanced todo list management and content organization capabilities through Notion's API.

## MCP Overview

Python-based MCP server that enables AI models to interact with Notion's API, providing:
- **Todo Management**: Create, update, and track tasks with rich text, due dates, priorities, and nested subtasks
- **Database Operations**: Create and manage Notion databases with custom properties, filters, and views
- **Content Organization**: Structure and format content with Markdown support, hierarchical lists, and block operations
- **Real-time Integration**: Direct interaction with Notion's workspace, pages, and databases through clean async implementation

[Full feature list →](docs/features.md)

## Quick Start

```bash
# Clone and setup
git clone https://github.com/yourusername/notion-api-mcp.git
cd notion-api-mcp
uv venv && source .venv/bin/activate

# Install and configure
uv pip install -e .
cp .env.integration.template .env

# Add your Notion credentials to .env:
# NOTION_API_KEY=ntn_your_integration_token_here
# NOTION_PARENT_PAGE_ID=your_page_id_here  # For new databases
# NOTION_DATABASE_ID=your_database_id_here  # For existing databases

# Run the server
python -m notion_api_mcp
```

## Getting Started

### 1. Create a Notion Integration

1. Go to https://www.notion.so/my-integrations
2. Click "New integration"
3. Name your integration (e.g., "My MCP Integration")
4. Select the workspace where you'll use the integration
5. Copy the "Internal Integration Token" - this will be your `NOTION_API_KEY`
   - Should start with "ntn_"

### 2. Set Up Notion Access

You'll need either a parent page (for creating new databases) or an existing database ID:

#### Option A: Parent Page for New Databases
1. Open Notion in your browser
2. Create a new page or open an existing one where you want to create databases
3. Click the ••• menu in the top right
4. Select "Add connections" and choose your integration
5. Copy the page ID from the URL - it's the string after the last slash and before the question mark
   - Example: In `https://notion.so/myworkspace/123456abcdef...`, the ID is `123456abcdef...`
   - This will be your `NOTION_PARENT_PAGE_ID`

#### Option B: Existing Database
1. Open your existing Notion database
2. Make sure it's connected to your integration (••• menu > Add connections)
3. Copy the database ID from the URL
   - Example: In `https://notion.so/myworkspace/123456abcdef...?v=...`, the ID is `123456abcdef...`
   - This will be your `NOTION_DATABASE_ID`

### 3. Install the MCP Server

1. Create virtual environment:
```bash
cd notion-api-mcp
uv venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

2. Install dependencies:
```bash
uv pip install -e .
```

3. Configure environment:
```bash
cp .env.integration.template .env
```

4. Edit .env with your Notion credentials:
```env
NOTION_API_KEY=ntn_your_integration_token_here

# Choose one or both of these depending on your needs:
NOTION_PARENT_PAGE_ID=your_page_id_here  # For creating new databases
NOTION_DATABASE_ID=your_database_id_here  # For working with existing databases
```

### 4. Configure Claude Desktop

IMPORTANT: While the server supports both .env files and environment variables, Claude Desktop specifically requires configuration in its config file to use the MCP.

Add to Claude Desktop's config (`~/Library/Application Support/Claude/claude_desktop_config.json`):
```json
{
  "mcpServers": {
    "notion-api": {
      "command": "/path/to/your/.venv/bin/python",
      "args": ["-m", "notion_api_mcp"],
      "env": {
        "NOTION_API_KEY": "ntn_your_integration_token_here",
        
        // Choose one or both:
        "NOTION_PARENT_PAGE_ID": "your_page_id_here",
        "NOTION_DATABASE_ID": "your_database_id_here"
      }
    }
  }
}
```

Note: Even if you have a .env file configured, you must add these environment variables to the Claude Desktop config for Claude to use the MCP. The .env file is primarily for local development and testing.

## CLI Scripts (Standalone Usage)

In addition to the MCP server, this project provides standalone CLI scripts using PEP 723 inline dependencies. These scripts can be run directly with `uv run` without any installation or virtual environment setup.

### Quick Start with CLI

```bash
# Set your API key
export NOTION_API_KEY="ntn_your_integration_token_here"

# Verify connection
uv run scripts/notion-utils.py verify-connection

# Check configuration
uv run scripts/notion-utils.py check-config

# Get database info
uv run scripts/notion-utils.py get-database-info --database-id <id>
```

### Available Scripts

#### 1. `notion-utils.py` - Diagnostics and Utilities
```bash
# Verify API connection
uv run scripts/notion-utils.py verify-connection

# Get database information
uv run scripts/notion-utils.py get-database-info --database-id <id>

# Check environment configuration
uv run scripts/notion-utils.py check-config
```

#### 2. `notion-pages.py` - Page Management
```bash
# Create a page in a database
uv run scripts/notion-pages.py create --database-id <id> --title "My Page"

# Create a page under another page
uv run scripts/notion-pages.py create --page-id <id> --parent-type page --title "Child"

# Get page information
uv run scripts/notion-pages.py get <page-id>

# Update page properties
uv run scripts/notion-pages.py update <page-id> \
    --properties '{"Status": {"select": {"name": "Done"}}}'

# Archive/restore pages
uv run scripts/notion-pages.py archive <page-id>
uv run scripts/notion-pages.py restore <page-id>
```

#### 3. `notion-databases.py` - Database and Todo Operations
```bash
# Query a database
uv run scripts/notion-databases.py query --database-id <id>

# Query with filters
uv run scripts/notion-databases.py query --database-id <id> \
    --filter '{"property": "Status", "select": {"equals": "Done"}}'

# Add a todo
uv run scripts/notion-databases.py add-todo --database-id <id> \
    --title "Complete project" \
    --description "Finish all tasks" \
    --due-date "2026-12-31" \
    --priority "High" \
    --tags "work,urgent"

# Search todos
uv run scripts/notion-databases.py search-todos --database-id <id> \
    --status "In Progress" \
    --priority "High"

# Get database info
uv run scripts/notion-databases.py info --database-id <id>
```

#### 4. `notion-blocks.py` - Block Content Operations
```bash
# Add text to a page
uv run scripts/notion-blocks.py add <page-id> --text "Hello, world!"

# Add multiple blocks from JSON
uv run scripts/notion-blocks.py add <page-id> --blocks '[
    {"type": "paragraph", "paragraph": {"rich_text": [{"text": {"content": "First"}}]}},
    {"type": "heading_1", "heading_1": {"rich_text": [{"text": {"content": "Title"}}]}}
]'

# Get block content
uv run scripts/notion-blocks.py get <block-id>

# List child blocks
uv run scripts/notion-blocks.py list-children <block-id>

# Update block content
uv run scripts/notion-blocks.py update <block-id> \
    --content '{"paragraph": {"rich_text": [{"text": {"content": "Updated"}}]}}'

# Delete a block
uv run scripts/notion-blocks.py delete <block-id>
```

### Environment Variables for CLI

The CLI scripts use environment variables for configuration (with optional CLI flag overrides):

- `NOTION_API_KEY` - **Required**: Notion integration token
- `NOTION_DATABASE_ID` - Optional: Default database ID for queries
- `NOTION_PARENT_PAGE_ID` - Optional: Default parent page for new pages/databases

You can either:
1. Set environment variables: `export NOTION_API_KEY="ntn_..."`
2. Create a `.env` file in the project root (automatically loaded)
3. Override with CLI flags: `--api-key "ntn_..."`

### CLI vs MCP Server

**Use CLI scripts when:**
- You want direct command-line access to Notion
- You're writing shell scripts or automation
- You don't need Claude Desktop integration
- You want standalone executables

**Use MCP server when:**
- You're using Claude Desktop or other MCP clients
- You want conversational AI interaction with Notion
- You need complex, multi-step workflows with AI assistance

## Documentation

- [Configuration Details](docs/configuration.md) - Detailed configuration options and environment variables
- [Features](docs/features.md) - Complete feature list and capabilities
- [Architecture](docs/ARCHITECTURE.md) - Overview of available tools and usage examples
- [API Reference](docs/api_reference.md) - Detailed API endpoints and implementation details
- [Test Coverage Matrix](docs/test_coverage_matrix.md) - Test coverage and validation status
- [Dependencies](docs/dependencies.md) - Project dependencies and version information
- [Changelog](docs/CHANGELOG.md) - Development progress and updates

## Development

The server uses modern Python async features throughout:
- Type-safe configuration using Pydantic models
- Async HTTP using httpx for better performance
- Clean MCP integration for exposing Notion capabilities
- Proper resource cleanup and error handling

### Debugging

The server includes comprehensive logging:
- Console output for development
- File logging when running as a service
- Detailed error messages
- Request/response logging at debug level

Set `PYTHONPATH` to include the project root when running directly:

```bash
PYTHONPATH=/path/to/project python -m notion_api_mcp
```

## Future Development

Planned enhancements:
1. Performance Optimization
   - Add request caching
   - Optimize database queries
   - Implement connection pooling

2. Advanced Features
   - Multi-workspace support
   - Batch operations
   - Real-time updates
   - Advanced search capabilities

3. Developer Experience
   - Interactive API documentation
   - CLI tools for common operations
   - Additional code examples
   - Performance monitoring

4. Testing Enhancements
   - Performance benchmarks
   - Load testing
   - Additional edge cases
   - Extended integration tests