# CLAUDE.md

This file provides guidance to Claude Code when working with code in this repository.

## Project Overview

This is a **comprehensive command-line interface (CLI)** for the Notion API. The CLI provides complete access to all Notion API features through an intuitive, human-friendly command structure.

The CLI is a single standalone Python script using PEP 723 inline dependencies, executable with `uv run` without installation.

## Architecture

### Single-File CLI (`scripts/notion.py`)

- **Lines**: ~2,260 lines
- **API Coverage**: 100% of documented Notion API endpoints
- **Dependencies**: httpx, click, python-dotenv, structlog
- **Execution**: `uv run scripts/notion.py [command]`

### Key Features

1. **Complete API Coverage**: All Notion endpoints (pages, databases, blocks, todos)
2. **30+ Block Types**: Support for all Notion block types
3. **Smart Caching**: Name-to-ID resolution with automatic caching
4. **Path Navigation**: Use "Parent/Child" paths instead of UUIDs
5. **Human-Friendly**: Intuitive commands with helpful shortcuts
6. **Standalone**: PEP 723 inline dependencies (no installation needed)

### Module Structure

```python
scripts/notion.py:
├── NotionCache class          # Smart caching for name→ID resolution
├── Helper Functions           # ~500 lines
│   ├── create_rich_text()     # Rich text creation
│   ├── create_property()      # Universal property creator (all types)
│   ├── create_todo_properties() # Todo-specific properties
│   ├── build_filter()         # Single filter builder
│   ├── build_compound_filter() # AND/OR filter combinations
│   ├── build_sorts()          # Sort specifications
│   ├── build_todo_filter()    # Todo filter shortcuts
│   └── create_block()         # Universal block creator (30+ types)
├── Utility Functions          # Auth, UUID checking, search
└── CLI Commands               # ~1,500 lines
    ├── add (page, database, todo, block)
    ├── blocks (add, list, delete, subtasks)
    ├── check-config
    ├── delete (page, block)
    ├── get (page, database, block)
    ├── list (pages, databases)
    ├── move (page)
    ├── query (database)
    ├── refresh-cache
    ├── search
    ├── todos (search)
    ├── update (page, database, block)
    └── verify-connection
```

## Development Setup

### Running the CLI

```bash
# Run directly with uv (no installation needed)
uv run scripts/notion.py --help

# Set API key
export NOTION_API_KEY="ntn_your_integration_token_here"

# Test connection
uv run scripts/notion.py verify-connection
```

### Testing

```bash
# Install dev dependencies
uv pip install -e ".[dev]"

# Run tests
pytest tests/cli/ -v

# Run with coverage
pytest tests/cli/ --cov=scripts.notion --cov-report=term-missing

# Run specific test
pytest tests/cli/test_cli_helpers.py::test_create_block_paragraph
```

### Code Formatting

```bash
# Format code
black scripts/notion.py

# Check formatting
black scripts/notion.py --check
```

## Key Design Patterns

### 1. Helper Functions for API Objects

All helper functions create proper Notion API objects:

```python
# Properties
create_property("title", "My Title")
create_property("select", "Option A")
create_property("date", "2026-12-31")

# Filters
build_filter("Status", "select", "equals", "Done")
build_compound_filter([filter1, filter2], "and")

# Blocks
create_block("paragraph", "Hello world")
create_block("code", "print('hello')", language="python")
create_block("to_do", "Task", checked=True)
```

### 2. Smart Caching (NotionCache)

- Caches page/database names → IDs
- Supports hierarchical paths ("Parent/Child")
- Auto-refreshes every 24 hours
- Falls back to API search if not cached

```python
cache = NotionCache()
page_id = cache.find_by_path("Work/Projects/Q1", "page")
```

### 3. ID Resolution

The `resolve_id()` function handles name-or-ID inputs:

```python
resolved_id = resolve_id(cache, "Work/Projects", "page", api_key)
# Returns UUID, whether input was name or ID
```

### 4. Async API Calls

All API calls use httpx AsyncClient with async/await:

```python
async def _get():
    headers = get_auth_headers(api_key)
    async with httpx.AsyncClient(...) as client:
        response = await client.get(f"/pages/{page_id}")
        response.raise_for_status()
        return response.json()

result = asyncio.run(_get())
```

### 5. Error Handling

Commands check for required parameters and provide clear error messages:

```python
if not api_key:
    click.echo("❌ Error: NOTION_API_KEY required", err=True)
    sys.exit(1)
```

## Common Development Tasks

### Adding a New Command

1. Add command function with decorator:

```python
@cli.command()
@click.option('--param', help='Description')
def my_command(param: str):
    """
    Command description.

    Examples:
        notion.py my-command --param value
    """
    # Implementation
```

2. Add error checking
3. Implement async API call
4. Return JSON result

### Adding a New Helper Function

1. Add function with type hints:

```python
def create_my_helper(param: str) -> Dict[str, Any]:
    """
    Helper description.

    Args:
        param: Parameter description

    Returns:
        Notion API object structure
    """
    return {"type": "...", ...}
```

2. Add unit tests in `tests/cli/test_cli_helpers.py`
3. Add integration test in `tests/cli/test_cli_commands.py`

### Adding a New Block Type

Block types are handled by `create_block()`. To add support:

1. Add to the function's block type handling
2. Add to Click choice enum in `blocks add` command
3. Add tests for the new block type

## Testing Strategy

### Test Organization

```
tests/cli/
├── test_cli_helpers.py      # Unit tests for helper functions
├── test_cli_commands.py     # Integration tests for commands
├── test_cli_cache.py        # Cache operations tests
├── test_cli_diagnostics.py  # Diagnostic commands tests
├── test_cli_errors.py       # Error handling tests
└── conftest.py              # Shared fixtures
```

### Test Coverage Target: ~90%

- Helper functions: 95%+ (pure functions)
- Cache operations: 90%+
- Command execution: 85%+
- Error handling: 80%+

### Running Tests

```bash
# All tests
pytest tests/cli/ -v

# Unit tests only (fast)
pytest tests/cli/test_cli_helpers.py -v

# Integration tests (slower)
pytest tests/cli/test_cli_commands.py -v

# With coverage
pytest tests/cli/ --cov=scripts.notion --cov-report=term-missing
```

## Code Style

- **Line Length**: 88 characters (Black default)
- **Python Version**: 3.10+
- **Type Hints**: Use on function signatures
- **Docstrings**: Include examples in command docstrings
- **Error Messages**: Use emoji prefix (❌ for errors, ✅ for success)

## Environment Variables

- `NOTION_API_KEY` - Required: Notion integration token
- `NOTION_DATABASE_ID` - Optional: Default database for todos
- `NOTION_PARENT_PAGE_ID` - Optional: Default parent for new pages

## Debugging

### Enable Verbose Output

Add `--help` to any command to see usage:

```bash
uv run scripts/notion.py add page --help
uv run scripts/notion.py blocks add --help
```

### Test API Connection

```bash
uv run scripts/notion.py verify-connection
uv run scripts/notion.py check-config
```

### Clear Cache

```bash
rm -rf ~/.cache/notion-cli/cache.json
uv run scripts/notion.py refresh-cache
```

## Common Issues

### Import Errors
The script uses inline dependencies (PEP 723), so no imports from src/ are needed.

### API 401 Errors
- Check `NOTION_API_KEY` is set and starts with "ntn_"
- Verify integration has access to pages/databases

### Cache Issues
- Run `uv run scripts/notion.py refresh-cache`
- Cache is stored in `~/.cache/notion-cli/cache.json`

## Performance Tips

1. **Use caching**: Let the cache auto-refresh, don't force refresh unless needed
2. **Use --all sparingly**: Only use `--all` flag when you need all pages
3. **Batch operations**: Use JSON input for bulk block creation

## Documentation

- **Test Plan**: `docs/CLI_TEST_PLAN.md` - 140+ test cases
- **Migration Guide**: `docs/CLI_MIGRATION_GUIDE.md` - Migration from old CLI
- **Quick Reference**: `CLI_QUICK_REFERENCE.md` - Command quick ref
- **Examples**: `examples/` - Real-world usage scripts

## Project Goals

1. **Complete API Coverage**: Expose 100% of Notion API
2. **Human-Friendly**: Make Notion API accessible via intuitive CLI
3. **Standalone**: No installation, just `uv run`
4. **Well-Tested**: High test coverage with clear test cases
5. **Production-Ready**: Proper error handling, validation, clear messages
