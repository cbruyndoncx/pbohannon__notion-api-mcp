"""
Shared fixtures for CLI tests.
"""
import sys
from pathlib import Path
from typing import Dict, Any

import pytest
from click.testing import CliRunner

# Add scripts directory to path so we can import notion.py
scripts_dir = Path(__file__).parent.parent.parent / "scripts"
sys.path.insert(0, str(scripts_dir))


@pytest.fixture(scope="session")
def runner():
    """Click CLI test runner."""
    return CliRunner()


@pytest.fixture
def temp_cache(tmp_path):
    """Temporary cache directory and file."""
    cache_dir = tmp_path / ".cache" / "notion-cli"
    cache_dir.mkdir(parents=True)
    return cache_dir / "cache.json"


@pytest.fixture
def sample_page_data() -> Dict[str, Any]:
    """Sample page API response."""
    return {
        "object": "page",
        "id": "page-123",
        "properties": {
            "title": {
                "title": [{"plain_text": "Test Page", "type": "text"}]
            }
        },
        "parent": {"page_id": "parent-123"},
        "url": "https://notion.so/page-123",
        "created_time": "2026-01-01T00:00:00.000Z",
        "last_edited_time": "2026-01-01T00:00:00.000Z",
        "archived": False
    }


@pytest.fixture
def sample_database_data() -> Dict[str, Any]:
    """Sample database API response."""
    return {
        "object": "database",
        "id": "db-123",
        "title": [{"plain_text": "Test DB", "type": "text"}],
        "properties": {
            "Name": {"type": "title", "title": {}},
            "Status": {
                "type": "select",
                "select": {
                    "options": [
                        {"name": "Not Started", "color": "gray"},
                        {"name": "In Progress", "color": "blue"},
                        {"name": "Done", "color": "green"}
                    ]
                }
            }
        },
        "parent": {"page_id": "parent-123"},
        "url": "https://notion.so/db-123",
        "created_time": "2026-01-01T00:00:00.000Z",
        "last_edited_time": "2026-01-01T00:00:00.000Z",
        "archived": False
    }


@pytest.fixture
def sample_block_data() -> Dict[str, Any]:
    """Sample block API response."""
    return {
        "object": "block",
        "id": "block-123",
        "type": "paragraph",
        "paragraph": {
            "rich_text": [
                {
                    "type": "text",
                    "text": {"content": "Test content"},
                    "plain_text": "Test content"
                }
            ],
            "color": "default"
        },
        "created_time": "2026-01-01T00:00:00.000Z",
        "last_edited_time": "2026-01-01T00:00:00.000Z",
        "has_children": False,
        "archived": False
    }
