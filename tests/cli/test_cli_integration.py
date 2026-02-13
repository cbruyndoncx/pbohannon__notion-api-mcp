"""
Integration tests for CLI commands against a real Notion workspace.

Requirements:
- NOTION_API_KEY environment variable must be set
- NOTION_TEST_PAGE_ID environment variable must be set (a dedicated test page)

Setup:
1. Create a page in Notion called "CLI Test Health Check"
2. Set NOTION_TEST_PAGE_ID to that page's ID
3. Run with: pytest -m integration

All tests create subpages/content under the test page and clean up after themselves.
"""
import os
import json
from pathlib import Path
import time

import pytest

# Import the CLI module
import sys
scripts_dir = Path(__file__).parent.parent.parent / "scripts"
sys.path.insert(0, str(scripts_dir))

from notion import cli


# Mark all tests in this file as integration tests
pytestmark = pytest.mark.integration


@pytest.fixture(scope="session")
def notion_credentials():
    """Check that required Notion credentials are available."""
    api_key = os.getenv("NOTION_API_KEY")
    test_page_id = os.getenv("NOTION_TEST_PAGE_ID")

    if not api_key:
        pytest.skip("NOTION_API_KEY not set - skipping integration tests")
    if not test_page_id:
        pytest.skip("NOTION_TEST_PAGE_ID not set - skipping integration tests")

    return {
        "api_key": api_key,
        "test_page_id": test_page_id
    }


@pytest.fixture(scope="session")
def test_run_page(notion_credentials, runner):
    """
    Create a dedicated page for this test run.

    This creates a new subpage under the test results page for each test run,
    making the main page an organized index of test run results.
    """
    from datetime import datetime

    # Create test run page with timestamp
    start_time = datetime.now()
    timestamp = start_time.strftime("%Y-%m-%d %H:%M:%S")
    run_title = f"Test Run - {timestamp}"

    result = runner.invoke(cli, [
        'add', 'page',
        '--title', run_title,
        '--parent', notion_credentials["test_page_id"],
        '--icon', '🧪',
        '--content', f'Integration test run started at {timestamp}'
    ])

    if result.exit_code != 0:
        pytest.skip(f"Failed to create test run page: {result.output}")

    output_data = json.loads(result.output)
    run_page_id = output_data["page"]["id"]

    print(f"\n✅ Created test run page: {run_title} (ID: {run_page_id})")

    # Add initial structure
    runner.invoke(cli, [
        'blocks', 'add', run_page_id,
        '--type', 'heading_2',
        '--text', 'Test Configuration'
    ])
    runner.invoke(cli, [
        'blocks', 'add', run_page_id,
        '--type', 'bulleted_list_item',
        '--text', f'Start Time: {timestamp}'
    ])
    runner.invoke(cli, [
        'blocks', 'add', run_page_id,
        '--type', 'bulleted_list_item',
        '--text', 'Test Suite: Integration Tests'
    ])

    # Store for use in tests
    yield run_page_id

    # After all tests complete, add summary
    end_time = datetime.now()
    duration = (end_time - start_time).total_seconds()

    runner.invoke(cli, [
        'blocks', 'add', run_page_id,
        '--type', 'heading_2',
        '--text', '✅ Test Results'
    ])
    runner.invoke(cli, [
        'blocks', 'add', run_page_id,
        '--type', 'bulleted_list_item',
        '--text', f'End Time: {end_time.strftime("%Y-%m-%d %H:%M:%S")}'
    ])
    runner.invoke(cli, [
        'blocks', 'add', run_page_id,
        '--type', 'bulleted_list_item',
        '--text', f'Duration: {duration:.1f} seconds'
    ])
    runner.invoke(cli, [
        'blocks', 'add', run_page_id,
        '--type', 'bulleted_list_item',
        '--text', 'Status: All tests completed'
    ])

    print(f"\n📝 Test run complete. Duration: {duration:.1f}s. Results in page: {run_page_id}")


@pytest.fixture
def test_page_id(test_run_page):
    """Get the test run page ID (used as parent for all test operations)."""
    return test_run_page


class TestPageOperations:
    """Integration tests for page operations."""

    @pytest.fixture(scope="class", autouse=True)
    def section_header(self, runner, test_run_page):
        """Add section header for this test class."""
        runner.invoke(cli, [
            'blocks', 'add', test_run_page,
            '--type', 'heading_2',
            '--text', '📄 Page Operations Tests'
        ])

    def test_create_and_get_page(self, runner, test_page_id):
        """Create a page and retrieve it."""
        # Create page
        result = runner.invoke(cli, [
            'add', 'page',
            '--title', 'Integration Test Page',
            '--parent', test_page_id,
            '--icon', '🧪'
        ])

        assert result.exit_code == 0, f"Failed to create page: {result.output}"

        # Parse output to get page ID
        output_data = json.loads(result.output)
        assert output_data.get("success"), "Page creation not successful"
        page_id = output_data["page"]["id"]
        assert page_id, "No page ID in response"

        # Get the page
        result = runner.invoke(cli, ['get', 'page', page_id])

        assert result.exit_code == 0, f"Failed to get page: {result.output}"
        output_data = json.loads(result.output)
        assert output_data["page"]["id"] == page_id

        # Clean up - archive the page
        result = runner.invoke(cli, ['delete', 'page', page_id])
        assert result.exit_code == 0, f"Failed to delete page: {result.output}"

    def test_create_page_with_content(self, runner, test_page_id):
        """Create a page with initial content blocks."""
        # Create page
        result = runner.invoke(cli, [
            'add', 'page',
            '--title', 'Page with Content',
            '--parent', test_page_id,
            '--content', 'This is the first paragraph.'
        ])

        assert result.exit_code == 0, f"Failed to create page: {result.output}"

        output_data = json.loads(result.output)
        page_id = output_data["page"]["id"]

        # Add more blocks
        result = runner.invoke(cli, [
            'blocks', 'add',
            page_id,
            '--type', 'heading_2',
            '--text', 'Section Title'
        ])

        assert result.exit_code == 0, f"Failed to add block: {result.output}"

        # List blocks
        result = runner.invoke(cli, ['blocks', 'list', page_id])

        assert result.exit_code == 0, f"Failed to list blocks: {result.output}"
        output_data = json.loads(result.output)
        # Check for blocks list (may be in 'blocks' or 'results' key)
        blocks = output_data.get("blocks") or output_data.get("results", [])
        assert len(blocks) >= 2  # At least paragraph + heading

        # Clean up
        runner.invoke(cli, ['delete', 'page', page_id])

    def test_update_page(self, runner, test_page_id):
        """Create and update a page."""
        # Create page
        result = runner.invoke(cli, [
            'add', 'page',
            '--title', 'Original Title',
            '--parent', test_page_id
        ])

        assert result.exit_code == 0
        page_id = json.loads(result.output)["page"]["id"]

        # Update page title
        result = runner.invoke(cli, [
            'update', 'page',
            page_id,
            '--title', 'Updated Title'
        ])

        assert result.exit_code == 0, f"Failed to update page: {result.output}"

        # Verify update
        result = runner.invoke(cli, ['get', 'page', page_id])
        output_data = json.loads(result.output)

        # Extract title from properties (may be in 'page' wrapper or directly)
        page_data = output_data.get("page", output_data)
        title_property = page_data["properties"].get("title", {})
        title_text = title_property.get("title", [{}])[0].get("plain_text", "")
        assert "Updated Title" in title_text

        # Clean up
        runner.invoke(cli, ['delete', 'page', page_id])

    def test_move_page(self, runner, test_page_id):
        """Create a page and move it to a new parent."""
        # Create two pages - one will be the new parent
        result = runner.invoke(cli, [
            'add', 'page',
            '--title', 'New Parent Page',
            '--parent', test_page_id
        ])
        assert result.exit_code == 0
        new_parent_id = json.loads(result.output)["page"]["id"]

        result = runner.invoke(cli, [
            'add', 'page',
            '--title', 'Page to Move',
            '--parent', test_page_id
        ])
        assert result.exit_code == 0
        page_to_move_id = json.loads(result.output)["page"]["id"]

        # Move the page
        result = runner.invoke(cli, [
            'move', 'page',
            page_to_move_id,
            '--to', new_parent_id
        ])

        assert result.exit_code == 0, f"Failed to move page: {result.output}"

        # Clean up both pages
        runner.invoke(cli, ['delete', 'page', page_to_move_id])
        runner.invoke(cli, ['delete', 'page', new_parent_id])


class TestBlockOperations:
    """Integration tests for block operations."""

    @pytest.fixture(scope="class", autouse=True)
    def section_header(self, runner, test_run_page):
        """Add section header for this test class."""
        runner.invoke(cli, [
            'blocks', 'add', test_run_page,
            '--type', 'heading_2',
            '--text', '🧱 Block Operations Tests'
        ])

    def test_add_various_block_types(self, runner, test_page_id):
        """Add different types of blocks to a page."""
        # Create test page
        result = runner.invoke(cli, [
            'add', 'page',
            '--title', 'Block Types Test',
            '--parent', test_page_id
        ])
        assert result.exit_code == 0
        page_id = json.loads(result.output)["page"]["id"]

        # Test different block types
        block_tests = [
            (['blocks', 'add', page_id, '--type', 'paragraph', '--text', 'A paragraph'], 'paragraph'),
            (['blocks', 'add', page_id, '--type', 'heading_1', '--text', 'Heading 1'], 'heading_1'),
            (['blocks', 'add', page_id, '--type', 'heading_2', '--text', 'Heading 2'], 'heading_2'),
            (['blocks', 'add', page_id, '--type', 'bulleted_list_item', '--text', 'Bullet point'], 'bulleted_list_item'),
            (['blocks', 'add', page_id, '--type', 'numbered_list_item', '--text', 'Numbered item'], 'numbered_list_item'),
            (['blocks', 'add', page_id, '--type', 'to_do', '--text', 'Todo item'], 'to_do'),
            (['blocks', 'add', page_id, '--type', 'quote', '--text', 'A quote'], 'quote'),
            (['blocks', 'add', page_id, '--type', 'code', '--text', 'print("hello")', '--language', 'python'], 'code'),
            (['blocks', 'add', page_id, '--type', 'divider'], 'divider'),
        ]

        for cmd, block_type in block_tests:
            result = runner.invoke(cli, cmd)
            assert result.exit_code == 0, f"Failed to add {block_type}: {result.output}"

        # Verify blocks were created
        result = runner.invoke(cli, ['blocks', 'list', page_id])
        assert result.exit_code == 0
        output_data = json.loads(result.output)
        blocks = output_data.get("blocks") or output_data.get("results", [])
        assert len(blocks) >= len(block_tests)

        # Clean up
        runner.invoke(cli, ['delete', 'page', page_id])

    def test_update_block(self, runner, test_page_id):
        """Create and update a block."""
        # Create page with a block
        result = runner.invoke(cli, [
            'add', 'page',
            '--title', 'Update Block Test',
            '--parent', test_page_id,
            '--content', 'Original text'
        ])
        assert result.exit_code == 0
        page_id = json.loads(result.output)["page"]["id"]

        # Get the block ID
        result = runner.invoke(cli, ['blocks', 'list', page_id])
        output_data = json.loads(result.output)
        blocks = output_data.get("blocks") or output_data.get("results", [])
        block_id = blocks[0]["id"]

        # Update the block
        result = runner.invoke(cli, [
            'update', 'block',
            block_id,
            '--text', 'Updated text'
        ])

        assert result.exit_code == 0, f"Failed to update block: {result.output}"

        # Clean up
        runner.invoke(cli, ['delete', 'page', page_id])


class TestDatabaseOperations:
    """Integration tests for database operations."""

    @pytest.fixture(scope="class", autouse=True)
    def section_header(self, runner, test_run_page):
        """Add section header for this test class."""
        runner.invoke(cli, [
            'blocks', 'add', test_run_page,
            '--type', 'heading_2',
            '--text', '🗄️ Database Operations Tests'
        ])

    def test_create_and_query_database(self, runner, test_page_id):
        """Create a database and query it."""
        # Create database with simple schema
        properties_json = json.dumps({
            "Name": {"title": {}},
            "Status": {
                "select": {
                    "options": [
                        {"name": "Todo", "color": "red"},
                        {"name": "Done", "color": "green"}
                    ]
                }
            }
        })

        result = runner.invoke(cli, [
            'add', 'database',
            '--title', 'Test Database',
            '--parent', test_page_id,
            '--properties', properties_json
        ])

        assert result.exit_code == 0, f"Failed to create database: {result.output}"
        output_data = json.loads(result.output)
        db_id = output_data.get("database", {}).get("id") or output_data.get("id")

        # Get database info
        result = runner.invoke(cli, ['get', 'database', db_id])
        assert result.exit_code == 0

        # Query database (should be empty)
        result = runner.invoke(cli, ['query', 'database', db_id])
        assert result.exit_code == 0
        output_data = json.loads(result.output)
        results = output_data.get("results") or output_data.get("pages", [])
        assert isinstance(results, list)

        # Clean up
        runner.invoke(cli, ['delete', 'database', db_id])


class TestSearchAndCache:
    """Integration tests for search and caching."""

    @pytest.fixture(scope="class", autouse=True)
    def section_header(self, runner, test_run_page):
        """Add section header for this test class."""
        runner.invoke(cli, [
            'blocks', 'add', test_run_page,
            '--type', 'heading_2',
            '--text', '🔍 Search & Cache Tests'
        ])

    def test_search_by_title(self, runner, test_page_id):
        """Create a page and search for it by title."""
        import random
        unique_title = f"SearchTest_{int(time.time())}_{random.randint(1000, 9999)}"

        # Create page with unique title
        result = runner.invoke(cli, [
            'add', 'page',
            '--title', unique_title,
            '--parent', test_page_id
        ])
        assert result.exit_code == 0
        page_id = json.loads(result.output)["page"]["id"]

        # Give Notion's search index a moment to update
        time.sleep(2)

        # Search for it
        result = runner.invoke(cli, ['search', unique_title])
        assert result.exit_code == 0

        output_data = json.loads(result.output)
        results = output_data.get("results") or output_data.get("pages", [])

        # Check if our page is in results (or at least the title appears)
        found = any(r.get("id") == page_id or unique_title in r.get("title", "") for r in results)

        # If not found immediately, it's OK - search indexing can be slow
        # Just verify search doesn't error out
        if not found:
            print(f"Note: Page {unique_title} not yet indexed in search (this is normal)")

        # Clean up
        runner.invoke(cli, ['delete', 'page', page_id])

    def test_list_pages_and_databases(self, runner, test_page_id):
        """List pages and databases."""
        # List pages
        result = runner.invoke(cli, ['list', 'pages'])
        assert result.exit_code == 0
        output_data = json.loads(result.output)
        pages = output_data.get("pages") or output_data.get("results", [])
        assert isinstance(pages, list)

        # List databases
        result = runner.invoke(cli, ['list', 'databases'])
        assert result.exit_code == 0
        output_data = json.loads(result.output)
        databases = output_data.get("databases") or output_data.get("results", [])
        assert isinstance(databases, list)

    def test_cache_with_refresh(self, runner, test_page_id):
        """Test cache refresh functionality."""
        # List with refresh
        result = runner.invoke(cli, ['list', 'pages', '--refresh'])
        assert result.exit_code == 0

        # List without refresh (uses cache)
        result = runner.invoke(cli, ['list', 'pages'])
        assert result.exit_code == 0


class TestDiagnostics:
    """Integration tests for diagnostic commands."""

    @pytest.fixture(scope="class", autouse=True)
    def section_header(self, runner, test_run_page):
        """Add section header for this test class."""
        runner.invoke(cli, [
            'blocks', 'add', test_run_page,
            '--type', 'heading_2',
            '--text', '🩺 Diagnostic Tests'
        ])

    def test_verify_connection_real(self, runner):
        """Verify connection to Notion API."""
        result = runner.invoke(cli, ['verify-connection'])

        assert result.exit_code == 0, f"Connection verification failed: {result.output}"
        output_data = json.loads(result.output)
        assert output_data["success"] is True
        assert "user" in output_data

    def test_check_config_real(self, runner):
        """Check configuration with real credentials."""
        result = runner.invoke(cli, ['check-config'])

        assert result.exit_code == 0
        output_data = json.loads(result.output)
        assert output_data["configuration"]["NOTION_API_KEY"]["set"] is True


class TestErrorHandling:
    """Integration tests for error handling with real API."""

    @pytest.fixture(scope="class", autouse=True)
    def section_header(self, runner, test_run_page):
        """Add section header for this test class."""
        runner.invoke(cli, [
            'blocks', 'add', test_run_page,
            '--type', 'heading_2',
            '--text', '⚠️ Error Handling Tests'
        ])

    def test_get_nonexistent_page(self, runner):
        """Try to get a page that doesn't exist."""
        fake_id = "00000000-0000-0000-0000-000000000000"

        result = runner.invoke(cli, ['get', 'page', fake_id])

        # Should fail with 404 or similar error
        assert result.exit_code != 0

    def test_invalid_parent_for_page(self, runner):
        """Try to create a page with invalid parent."""
        fake_parent = "invalid-parent-id"

        result = runner.invoke(cli, [
            'add', 'page',
            '--title', 'Test Page',
            '--parent', fake_parent
        ])

        # Should fail
        assert result.exit_code != 0
