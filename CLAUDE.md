# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a **Model Context Protocol (MCP) server** that provides advanced todo list management and content organization capabilities through Notion's API. MCP enables AI models to interact with external tools and services, allowing seamless integration with Notion's powerful features.

The server is Python-based and uses modern async patterns throughout with type-safe configuration using Pydantic models.

## Development Setup

### Environment Setup
```bash
# Create virtual environment
uv venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install in editable mode
uv pip install -e .
```

### Running the Server
```bash
# Run directly as module
python -m notion_api_mcp

# With PYTHONPATH (if needed for debugging)
PYTHONPATH=/home/cb/projects/dev/pbohannon__notion-api-mcp python -m notion_api_mcp
```

### Testing
```bash
# Run all tests with coverage
pytest

# Run specific test file
pytest tests/test_server.py

# Run specific test
pytest tests/test_server.py::test_function_name

# Run integration tests (requires Notion API access)
pytest -m integration

# Run with verbose output
pytest -v

# Run without coverage report
pytest --no-cov
```

### Type Checking
```bash
# Run mypy type checker
mypy src/notion_api_mcp
```

### Code Formatting
```bash
# Format code with black
black src/notion_api_mcp tests
```

## Architecture

### Module Structure

The codebase is organized into clean, focused modules:

```
src/notion_api_mcp/
├── __main__.py          # Entry point (runs server via server.main())
├── server.py            # MCP server implementation, tool registration, error handling
├── api/                 # Notion API client layer
│   ├── pages.py         # Pages API (create_page, update_page, todo properties)
│   ├── databases.py     # Databases API (create_database, query_database, filters)
│   └── blocks.py        # Blocks API (append_children, get_block, update_block)
├── models/              # Data models and validation
│   ├── properties.py    # Notion property type definitions
│   └── responses.py     # API response models
└── utils/               # Utilities
    ├── auth.py          # Authentication helpers
    └── formatting.py    # Rich text formatting, markdown conversion
```

### Key Design Patterns

1. **Async Throughout**: All API calls use httpx AsyncClient with proper async/await patterns
2. **Retry Logic**: The `@with_retry` decorator provides exponential backoff for transient failures
3. **Type Safety**: Pydantic models validate configuration and API responses
4. **Clean Separation**: API modules (pages, databases, blocks) are independent and focused
5. **Error Handling**: Custom error codes (ErrorCode class) map to MCP error responses

### MCP Server Flow

1. **Initialization** (`server.py:NotionServer.__init__`):
   - FastMCP app created with capabilities
   - Tools registered via decorators (`@self.app.tool`)
   - API clients initialized lazily in `ensure_client()`

2. **Client Management** (`server.py:ensure_client`):
   - Creates httpx AsyncClient with Notion API headers
   - Tests connection with `/users/me` endpoint
   - Initializes PagesAPI, DatabasesAPI, BlocksAPI with shared client

3. **Tool Execution**:
   - Tools are async functions decorated with `@self.app.tool` and `@with_retry`
   - Each tool calls appropriate API module method
   - Results are JSON-serialized with success/error structure

### Available MCP Tools

**Page Management:**
- `create_page` - Create new Notion page
- `get_page` - Retrieve page by ID
- `update_page` - Update page properties
- `archive_page` / `restore_page` - Archive/restore pages
- `get_page_property` - Get specific property values

**Todo Management:**
- `add_todo` - Create todo with title, description, due date, priority, tags
- `search_todos` - Query todos with filtering and sorting

**Database Operations:**
- `create_database` - Create new database with custom schema
- `query_database` - Query with filters and sorts
- `get_database_info` - Get database metadata

**Block/Content Operations:**
- `add_content_blocks` - Append blocks with positioning support (handles batching for >100 blocks)
- `get_block_content` - Get block by ID
- `list_block_children` - List child blocks
- `update_block_content` - Update block content
- `delete_block` - Delete block

**Diagnostics:**
- `verify_connection` - Test Notion API authentication
- `get_database_info` - Get configured database details

## Configuration

The server uses `ServerConfig` (Pydantic model) with these environment variables:
- `NOTION_API_KEY` - Notion integration token (starts with "ntn_")
- `NOTION_DATABASE_ID` - Default database ID for todos
- `NOTION_PARENT_PAGE_ID` - Parent page for creating new databases/pages
- `DATABASE_TEMPLATE_ID` - (Optional) Template for new databases

Configuration is loaded from `.env` file or environment variables via `ServerConfig.from_env()`.

## Testing Strategy

Tests are organized by module and feature:
- `tests/blocks/` - Block operations (basic, formatting, subtasks, permissions)
- `tests/pages/` - Page operations (basic, permissions)
- `tests/databases/` - Database operations (todo management)
- `tests/properties/` - Property type handling
- `tests/utils/` - Utility functions
- `tests/common/` - Shared test fixtures and helpers

**Test markers:**
- `@pytest.mark.integration` - Tests requiring Notion API access (set in pyproject.toml)

**Coverage:**
- Run `pytest` to see coverage report (configured in pyproject.toml)
- Target: Cover all API methods and error paths

## Common Development Tasks

### Adding a New Tool

1. Add handler function in `server.py` within `register_tools()`:
```python
@self.app.tool(name="tool_name", description="What it does")
@with_retry(retry_count=3)
async def handle_tool_name(param: str) -> str:
    await self.ensure_client()
    result = await self.api_module.method(param)
    return json.dumps(result, indent=2)
```

2. Add corresponding API method in appropriate module (`api/pages.py`, `api/databases.py`, or `api/blocks.py`)

3. Write tests in `tests/test_tool_handlers.py` or module-specific test files

### Adding a New API Method

1. Add method to appropriate API class (`PagesAPI`, `DatabasesAPI`, `BlocksAPI`)
2. Use structured logging: `self._log.error("event_name", context=value)`
3. Let httpx exceptions propagate (handled by `@with_retry` decorator)
4. Return raw JSON response from Notion API

### Working with Notion API

- **API Version**: "2022-06-28" (set in client headers)
- **Base URL**: https://api.notion.com/v1
- **Authentication**: Bearer token in Authorization header
- **Rate Limits**: Notion has rate limits; retry logic handles 429 responses
- **Batch Limits**: Max 100 blocks per append_children request (handled automatically)

## Debugging

### Logging
The server uses structlog for structured logging:
```python
self._log.error("event_name", param1=value1, param2=value2)
```

### Common Issues

1. **401 Authentication Error**: Check NOTION_API_KEY is correct and starts with "ntn_"
2. **404 Not Found**: Verify database/page ID and that integration has access
3. **Connection Errors**: Check network connectivity; retry logic will attempt 3x with backoff
4. **Import Errors**: Ensure PYTHONPATH includes project root when running directly

### Testing Locally

Use `verify_connection` tool to test authentication and configuration.

## Code Style

- **Line Length**: 88 characters (Black default)
- **Python Version**: 3.10+
- **Type Hints**: Required on all function signatures (enforced by mypy)
- **Async**: Use async/await for all I/O operations
- **Imports**: Absolute imports from package root
