# Integration Tests Guide

## Overview

Integration tests run against a real Notion workspace to validate end-to-end functionality. These tests create, read, update, and delete actual pages, blocks, and databases.

## Setup

### 1. Create a Test Page in Notion

1. Open your Notion workspace
2. Create a new page called **"CLI Test Health Check"** or similar
3. Copy the page ID from the URL:
   - URL format: `https://www.notion.so/workspace-name/<PAGE_ID>?v=...`
   - Or use Share → Copy link and extract the ID

### 2. Set Environment Variables

Add to your `.env` file:

```bash
# Required for all CLI operations
NOTION_API_KEY=ntn_your_api_key_here

# Required for integration tests
NOTION_TEST_PAGE_ID=your-test-page-id-here
```

**Important**: The API key must have access to the test page!

### 3. Verify Setup

Run the diagnostic commands to verify your configuration:

```bash
# Check configuration
uv run scripts/notion.py check-config

# Verify connection
uv run scripts/notion.py verify-connection
```

## Running Integration Tests

### Run All Integration Tests

```bash
pytest -m integration -v
```

### Run Specific Test Classes

```bash
# Test page operations only
pytest -m integration -k TestPageOperations -v

# Test block operations only
pytest -m integration -k TestBlockOperations -v

# Test database operations only
pytest -m integration -k TestDatabaseOperations -v
```

### Run Unit Tests Only (Skip Integration)

```bash
pytest -m "not integration" -v
```

### Run All Tests (Unit + Integration)

```bash
pytest tests/cli/ -v
```

## Test Coverage

Integration tests cover:

### Page Operations
- ✅ Create page with title, parent, icon
- ✅ Create page with initial content blocks
- ✅ Get page by ID
- ✅ Update page title
- ✅ Move page to new parent
- ✅ Delete/archive page

### Block Operations
- ✅ Add various block types (paragraph, headings, lists, to-do, quote, code, divider)
- ✅ List blocks in a page
- ✅ Update block content
- ✅ Block positioning

### Database Operations
- ✅ Create database with schema
- ✅ Get database info
- ✅ Query database

### Search and Cache
- ✅ Search by title
- ✅ List pages and databases
- ✅ Cache refresh functionality

### Diagnostics
- ✅ Verify connection (real API)
- ✅ Check config (real credentials)

### Error Handling
- ✅ Handle nonexistent pages (404)
- ✅ Handle invalid parents
- ✅ API error responses

## Cleanup

**All tests automatically clean up after themselves** by archiving created pages and databases.

If tests fail midway and leave test data:

```bash
# Manually archive leftover pages
uv run scripts/notion.py delete page <page-id>

# Or go to your test page in Notion and manually archive subpages
```

## Test Structure

```
tests/cli/test_cli_integration.py
├── TestPageOperations       (5 tests)
├── TestBlockOperations      (2 tests)
├── TestDatabaseOperations   (1 test)
├── TestSearchAndCache       (3 tests)
├── TestDiagnostics          (2 tests)
└── TestErrorHandling        (2 tests)
```

**Total: 15 integration tests**

## Best Practices

1. **Use a dedicated test workspace** or page to avoid affecting production data
2. **Run integration tests before releases** to validate API changes
3. **Check test page periodically** for orphaned test data
4. **Monitor API rate limits** - integration tests make real API calls
5. **Keep test page organized** - all test data appears as subpages

## Troubleshooting

### "NOTION_TEST_PAGE_ID not set - skipping integration tests"

Set the environment variable:
```bash
export NOTION_TEST_PAGE_ID=your-page-id-here
```

### "Connection verification failed"

Check:
- Is `NOTION_API_KEY` correct and starts with `ntn_`?
- Does the integration have access to your workspace?
- Is your internet connection working?

### "Failed to create page: 404"

Check:
- Does the API key have access to `NOTION_TEST_PAGE_ID`?
- Is the test page ID correct (not a database ID)?
- Has the test page been deleted/archived?

### Tests are slow

Integration tests make real API calls and are inherently slower than unit tests:
- Unit tests: ~0.3 seconds for 137 tests
- Integration tests: ~10-30 seconds for 15 tests (depends on API latency)

To skip them during development:
```bash
pytest -m "not integration"
```

## Example Test Run

```bash
$ pytest -m integration -v

tests/cli/test_cli_integration.py::TestPageOperations::test_create_and_get_page PASSED
tests/cli/test_cli_integration.py::TestPageOperations::test_create_page_with_content PASSED
tests/cli/test_cli_integration.py::TestPageOperations::test_update_page PASSED
tests/cli/test_cli_integration.py::TestPageOperations::test_move_page PASSED
tests/cli/test_cli_integration.py::TestBlockOperations::test_add_various_block_types PASSED
tests/cli/test_cli_integration.py::TestBlockOperations::test_update_block PASSED
tests/cli/test_cli_integration.py::TestDatabaseOperations::test_create_and_query_database PASSED
tests/cli/test_cli_integration.py::TestSearchAndCache::test_search_by_title PASSED
tests/cli/test_cli_integration.py::TestSearchAndCache::test_list_pages_and_databases PASSED
tests/cli/test_cli_integration.py::TestSearchAndCache::test_cache_with_refresh PASSED
tests/cli/test_cli_integration.py::TestDiagnostics::test_verify_connection_real PASSED
tests/cli/test_cli_integration.py::TestDiagnostics::test_check_config_real PASSED
tests/cli/test_cli_integration.py::TestErrorHandling::test_get_nonexistent_page PASSED
tests/cli/test_cli_integration.py::TestErrorHandling::test_invalid_parent_for_page PASSED

============================== 15 passed in 24.3s ==============================
```

## CI/CD Integration

For GitHub Actions or similar:

```yaml
- name: Run integration tests
  env:
    NOTION_API_KEY: ${{ secrets.NOTION_API_KEY }}
    NOTION_TEST_PAGE_ID: ${{ secrets.NOTION_TEST_PAGE_ID }}
  run: pytest -m integration -v
```

Store credentials as repository secrets!
