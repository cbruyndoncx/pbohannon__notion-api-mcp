"""
Unit tests for NotionCache class.

Tests cache operations including:
- Initialization and persistence
- Staleness checking
- Update from search results
- ID resolution (direct, path-based, hierarchical)
- Cache saving and loading
"""
import sys
import json
from pathlib import Path
from datetime import datetime, timedelta

import pytest

# Import from scripts/notion.py
scripts_dir = Path(__file__).parent.parent.parent / "scripts"
sys.path.insert(0, str(scripts_dir))

from notion import NotionCache


# =============================================================================
# Cache Initialization Tests
# =============================================================================

def test_cache_init_creates_directory(tmp_path):
    """Initialize cache when directory doesn't exist."""
    cache_file = tmp_path / "new_cache" / "cache.json"

    cache = NotionCache(cache_file)

    assert cache.cache_path.parent.exists()
    assert cache.data["pages"] == {}
    assert cache.data["databases"] == {}
    assert cache.data["hierarchy"] == {}
    assert cache.data["last_refresh"] is None


def test_cache_init_loads_existing(tmp_path):
    """Load existing cache file."""
    cache_file = tmp_path / "cache.json"

    # Create cache with data
    existing_data = {
        "pages": {"page-1": {"title": "Test Page", "id": "page-1"}},
        "databases": {"db-1": {"title": "Test DB", "id": "db-1"}},
        "hierarchy": {},
        "last_refresh": "2026-01-01T00:00:00"
    }
    cache_file.write_text(json.dumps(existing_data))

    # Load in new instance
    cache = NotionCache(cache_file)

    assert cache.data["pages"]["page-1"]["title"] == "Test Page"
    assert cache.data["databases"]["db-1"]["title"] == "Test DB"
    assert cache.data["last_refresh"] == "2026-01-01T00:00:00"


def test_cache_init_handles_corrupt_file(tmp_path):
    """Handle corrupted JSON file gracefully."""
    cache_file = tmp_path / "cache.json"

    # Write invalid JSON
    cache_file.write_text("invalid json {")

    # Should not raise exception, should return default structure
    cache = NotionCache(cache_file)

    assert cache.data["pages"] == {}
    assert cache.data["databases"] == {}
    assert cache.data["last_refresh"] is None


def test_cache_init_empty_file(tmp_path):
    """Handle empty file."""
    cache_file = tmp_path / "cache.json"
    cache_file.write_text("")

    cache = NotionCache(cache_file)

    assert cache.data["pages"] == {}
    assert cache.data["databases"] == {}


# =============================================================================
# Cache Staleness Tests
# =============================================================================

def test_cache_is_stale_no_refresh(tmp_path):
    """Check staleness when never refreshed."""
    cache = NotionCache(tmp_path / "cache.json")

    assert cache.is_stale() is True


def test_cache_is_stale_recent_refresh(tmp_path):
    """Check staleness after recent refresh."""
    cache = NotionCache(tmp_path / "cache.json")
    cache.data["last_refresh"] = datetime.now().isoformat()
    cache._save()

    assert cache.is_stale() is False


def test_cache_is_stale_old_refresh(tmp_path):
    """Check staleness after 25 hours (beyond 24h TTL)."""
    cache = NotionCache(tmp_path / "cache.json")
    old_time = datetime.now() - timedelta(hours=25)
    cache.data["last_refresh"] = old_time.isoformat()

    assert cache.is_stale() is True


def test_cache_is_stale_exactly_24_hours(tmp_path):
    """Check staleness at exactly 24 hours."""
    cache = NotionCache(tmp_path / "cache.json")
    exactly_24h = datetime.now() - timedelta(hours=24)
    cache.data["last_refresh"] = exactly_24h.isoformat()

    # Should be stale (> 24 hours)
    assert cache.is_stale() is True


def test_cache_is_stale_just_under_24_hours(tmp_path):
    """Check staleness just under 24 hours."""
    cache = NotionCache(tmp_path / "cache.json")
    just_under = datetime.now() - timedelta(hours=23, minutes=59)
    cache.data["last_refresh"] = just_under.isoformat()

    # Should not be stale (< 24 hours)
    assert cache.is_stale() is False


# =============================================================================
# Cache Update Tests
# =============================================================================

def test_update_from_search_single_page(tmp_path):
    """Update cache with single page result."""
    cache = NotionCache(tmp_path / "cache.json")

    results = [{
        "object": "page",
        "id": "page-123",
        "properties": {
            "title": {
                "title": [{"plain_text": "My Page", "type": "text"}]
            }
        },
        "parent": {"page_id": "parent-123"},
        "url": "https://notion.so/page-123",
        "archived": False
    }]

    cache.update_from_search(results)

    assert "page-123" in cache.data["pages"]
    assert cache.data["pages"]["page-123"]["title"] == "My Page"
    assert cache.data["pages"]["page-123"]["parent_id"] == "parent-123"
    assert cache.data["pages"]["page-123"]["url"] == "https://notion.so/page-123"
    assert cache.data["pages"]["page-123"]["archived"] is False
    assert cache.data["last_refresh"] is not None


def test_update_from_search_single_database(tmp_path):
    """Update cache with single database result."""
    cache = NotionCache(tmp_path / "cache.json")

    results = [{
        "object": "database",
        "id": "db-123",
        "title": [{"plain_text": "My Database", "type": "text"}],
        "parent": {"page_id": "parent-123"},
        "url": "https://notion.so/db-123",
        "archived": False
    }]

    cache.update_from_search(results)

    assert "db-123" in cache.data["databases"]
    assert cache.data["databases"]["db-123"]["title"] == "My Database"
    assert cache.data["databases"]["db-123"]["parent_id"] == "parent-123"


def test_update_from_search_multiple_items(tmp_path):
    """Update cache with multiple pages and databases."""
    cache = NotionCache(tmp_path / "cache.json")

    results = [
        {
            "object": "page",
            "id": "page-1",
            "properties": {"title": {"title": [{"plain_text": "Page 1"}]}},
            "parent": {"workspace": True},
            "url": "https://notion.so/page-1",
            "archived": False
        },
        {
            "object": "page",
            "id": "page-2",
            "properties": {"title": {"title": [{"plain_text": "Page 2"}]}},
            "parent": {"page_id": "page-1"},
            "url": "https://notion.so/page-2",
            "archived": False
        },
        {
            "object": "database",
            "id": "db-1",
            "title": [{"plain_text": "DB 1"}],
            "parent": {"page_id": "page-1"},
            "url": "https://notion.so/db-1",
            "archived": False
        }
    ]

    cache.update_from_search(results)

    assert len(cache.data["pages"]) == 2
    assert len(cache.data["databases"]) == 1
    assert "page-1" in cache.data["pages"]
    assert "page-2" in cache.data["pages"]
    assert "db-1" in cache.data["databases"]


def test_update_from_search_updates_hierarchy(tmp_path):
    """Update cache hierarchy with parent-child relationships."""
    cache = NotionCache(tmp_path / "cache.json")

    results = [
        {
            "object": "page",
            "id": "parent",
            "properties": {"title": {"title": [{"plain_text": "Parent"}]}},
            "parent": {"workspace": True},
            "url": "https://notion.so/parent",
            "archived": False
        },
        {
            "object": "page",
            "id": "child-1",
            "properties": {"title": {"title": [{"plain_text": "Child 1"}]}},
            "parent": {"page_id": "parent"},
            "url": "https://notion.so/child-1",
            "archived": False
        },
        {
            "object": "page",
            "id": "child-2",
            "properties": {"title": {"title": [{"plain_text": "Child 2"}]}},
            "parent": {"page_id": "parent"},
            "url": "https://notion.so/child-2",
            "archived": False
        }
    ]

    cache.update_from_search(results)

    assert "parent" in cache.data["hierarchy"]
    assert "child-1" in cache.data["hierarchy"]["parent"]
    assert "child-2" in cache.data["hierarchy"]["parent"]
    assert len(cache.data["hierarchy"]["parent"]) == 2


def test_update_from_search_untitled_page(tmp_path):
    """Update cache with page that has no title."""
    cache = NotionCache(tmp_path / "cache.json")

    results = [{
        "object": "page",
        "id": "page-123",
        "properties": {},
        "parent": {"workspace": True},
        "url": "https://notion.so/page-123",
        "archived": False
    }]

    cache.update_from_search(results)

    # Should use "Untitled" as default
    assert cache.data["pages"]["page-123"]["title"] == "Untitled"


def test_update_from_search_archived_item(tmp_path):
    """Update cache with archived item."""
    cache = NotionCache(tmp_path / "cache.json")

    results = [{
        "object": "page",
        "id": "page-123",
        "properties": {"title": {"title": [{"plain_text": "Archived Page"}]}},
        "parent": {"workspace": True},
        "url": "https://notion.so/page-123",
        "archived": True
    }]

    cache.update_from_search(results)

    assert cache.data["pages"]["page-123"]["archived"] is True


def test_update_from_search_overwrites_existing(tmp_path):
    """Update cache overwrites existing entries."""
    cache = NotionCache(tmp_path / "cache.json")

    # Add initial data
    cache.data["pages"]["page-123"] = {
        "id": "page-123",
        "title": "Old Title",
        "parent_id": "old-parent",
        "url": "https://notion.so/page-123",
        "archived": False
    }

    # Update with new data
    results = [{
        "object": "page",
        "id": "page-123",
        "properties": {"title": {"title": [{"plain_text": "New Title"}]}},
        "parent": {"page_id": "new-parent"},
        "url": "https://notion.so/page-123",
        "archived": False
    }]

    cache.update_from_search(results)

    assert cache.data["pages"]["page-123"]["title"] == "New Title"
    assert cache.data["pages"]["page-123"]["parent_id"] == "new-parent"


# =============================================================================
# Direct Lookup Tests
# =============================================================================

def test_find_by_path_direct_title(tmp_path):
    """Find page by direct title match."""
    cache = NotionCache(tmp_path / "cache.json")
    cache.data["pages"]["page-123"] = {
        "id": "page-123",
        "title": "My Page",
        "parent_id": None
    }

    result = cache.find_by_path("My Page", "page")

    assert result == "page-123"


def test_find_by_path_case_insensitive(tmp_path):
    """Find page with different case."""
    cache = NotionCache(tmp_path / "cache.json")
    cache.data["pages"]["page-123"] = {
        "id": "page-123",
        "title": "My Page",
        "parent_id": None
    }

    result = cache.find_by_path("my page", "page")

    assert result == "page-123"


def test_find_by_path_database(tmp_path):
    """Find database by title."""
    cache = NotionCache(tmp_path / "cache.json")
    cache.data["databases"]["db-123"] = {
        "id": "db-123",
        "title": "My Database",
        "parent_id": None
    }

    result = cache.find_by_path("My Database", "database")

    assert result == "db-123"


def test_find_by_path_not_found(tmp_path):
    """Lookup non-existent page."""
    cache = NotionCache(tmp_path / "cache.json")

    result = cache.find_by_path("Nonexistent", "page")

    assert result is None


def test_find_by_path_wrong_type(tmp_path):
    """Lookup page when searching for database."""
    cache = NotionCache(tmp_path / "cache.json")
    cache.data["pages"]["page-123"] = {
        "id": "page-123",
        "title": "My Page",
        "parent_id": None
    }

    result = cache.find_by_path("My Page", "database")

    assert result is None


# =============================================================================
# Hierarchical Path Tests
# =============================================================================

def test_find_by_path_two_level_hierarchy(tmp_path):
    """Find page with parent/child path."""
    cache = NotionCache(tmp_path / "cache.json")

    # Setup hierarchy
    cache.data["pages"]["parent"] = {
        "id": "parent",
        "title": "Parent",
        "parent_id": None
    }
    cache.data["pages"]["child"] = {
        "id": "child",
        "title": "Child",
        "parent_id": "parent"
    }

    result = cache.find_by_path("Parent/Child", "page")

    assert result == "child"


def test_find_by_path_three_level_hierarchy(tmp_path):
    """Find page with grandparent/parent/child path."""
    cache = NotionCache(tmp_path / "cache.json")

    cache.data["pages"]["grandparent"] = {
        "id": "grandparent",
        "title": "Grandparent",
        "parent_id": None
    }
    cache.data["pages"]["parent"] = {
        "id": "parent",
        "title": "Parent",
        "parent_id": "grandparent"
    }
    cache.data["pages"]["child"] = {
        "id": "child",
        "title": "Child",
        "parent_id": "parent"
    }

    result = cache.find_by_path("Grandparent/Parent/Child", "page")

    assert result == "child"


def test_find_by_path_hierarchy_case_insensitive(tmp_path):
    """Find page with mixed case in path."""
    cache = NotionCache(tmp_path / "cache.json")

    cache.data["pages"]["parent"] = {
        "id": "parent",
        "title": "Parent",
        "parent_id": None
    }
    cache.data["pages"]["child"] = {
        "id": "child",
        "title": "Child",
        "parent_id": "parent"
    }

    result = cache.find_by_path("PARENT/child", "page")

    assert result == "child"


def test_find_by_path_hierarchy_not_found_parent(tmp_path):
    """Path lookup fails when parent not found."""
    cache = NotionCache(tmp_path / "cache.json")

    cache.data["pages"]["child"] = {
        "id": "child",
        "title": "Child",
        "parent_id": "nonexistent"
    }

    result = cache.find_by_path("Nonexistent/Child", "page")

    assert result is None


def test_find_by_path_hierarchy_not_found_child(tmp_path):
    """Path lookup fails when child not found."""
    cache = NotionCache(tmp_path / "cache.json")

    cache.data["pages"]["parent"] = {
        "id": "parent",
        "title": "Parent",
        "parent_id": None
    }

    result = cache.find_by_path("Parent/Nonexistent", "page")

    assert result is None


def test_find_by_path_with_spaces(tmp_path):
    """Path lookup with spaces in names."""
    cache = NotionCache(tmp_path / "cache.json")

    cache.data["pages"]["parent"] = {
        "id": "parent",
        "title": "My Parent Page",
        "parent_id": None
    }
    cache.data["pages"]["child"] = {
        "id": "child",
        "title": "My Child Page",
        "parent_id": "parent"
    }

    result = cache.find_by_path("My Parent Page/My Child Page", "page")

    assert result == "child"


def test_find_by_path_with_trailing_spaces(tmp_path):
    """Path lookup with trailing/leading spaces."""
    cache = NotionCache(tmp_path / "cache.json")

    cache.data["pages"]["parent"] = {
        "id": "parent",
        "title": "Parent",
        "parent_id": None
    }
    cache.data["pages"]["child"] = {
        "id": "child",
        "title": "Child",
        "parent_id": "parent"
    }

    result = cache.find_by_path(" Parent / Child ", "page")

    assert result == "child"


# =============================================================================
# Title Lookup Tests
# =============================================================================

def test_get_title_page_found(tmp_path):
    """Get title for existing page ID."""
    cache = NotionCache(tmp_path / "cache.json")
    cache.data["pages"]["page-123"] = {
        "id": "page-123",
        "title": "My Page"
    }

    result = cache.get_title("page-123")

    assert result == "My Page"


def test_get_title_database_found(tmp_path):
    """Get title for existing database ID."""
    cache = NotionCache(tmp_path / "cache.json")
    cache.data["databases"]["db-123"] = {
        "id": "db-123",
        "title": "My Database"
    }

    result = cache.get_title("db-123")

    assert result == "My Database"


def test_get_title_not_found(tmp_path):
    """Get title for non-existent ID."""
    cache = NotionCache(tmp_path / "cache.json")

    result = cache.get_title("nonexistent")

    assert result is None


def test_get_title_checks_both_collections(tmp_path):
    """Get title searches both pages and databases."""
    cache = NotionCache(tmp_path / "cache.json")
    cache.data["pages"]["page-123"] = {
        "id": "page-123",
        "title": "Page Title"
    }
    cache.data["databases"]["db-123"] = {
        "id": "db-123",
        "title": "Database Title"
    }

    page_title = cache.get_title("page-123")
    db_title = cache.get_title("db-123")

    assert page_title == "Page Title"
    assert db_title == "Database Title"


# =============================================================================
# Cache Persistence Tests
# =============================================================================

def test_cache_saves_to_disk(tmp_path):
    """Cache saves data to disk."""
    cache_file = tmp_path / "cache.json"
    cache = NotionCache(cache_file)

    cache.data["pages"]["page-123"] = {"title": "Test"}
    cache._save()

    # Verify file exists and contains data
    assert cache_file.exists()
    saved_data = json.loads(cache_file.read_text())
    assert "page-123" in saved_data["pages"]


def test_cache_persists_across_instances(tmp_path):
    """Cache persists data across multiple instances."""
    cache_file = tmp_path / "cache.json"

    # First instance
    cache1 = NotionCache(cache_file)
    cache1.data["pages"]["page-123"] = {"title": "Test", "id": "page-123"}
    cache1._save()

    # Second instance should load the data
    cache2 = NotionCache(cache_file)

    assert "page-123" in cache2.data["pages"]
    assert cache2.data["pages"]["page-123"]["title"] == "Test"


def test_cache_update_saves_automatically(tmp_path):
    """update_from_search saves automatically."""
    cache_file = tmp_path / "cache.json"
    cache = NotionCache(cache_file)

    results = [{
        "object": "page",
        "id": "page-123",
        "properties": {"title": {"title": [{"plain_text": "Auto Save Test"}]}},
        "parent": {"workspace": True},
        "url": "https://notion.so/page-123",
        "archived": False
    }]

    cache.update_from_search(results)

    # Verify saved to disk
    saved_data = json.loads(cache_file.read_text())
    assert "page-123" in saved_data["pages"]
    assert saved_data["pages"]["page-123"]["title"] == "Auto Save Test"


# =============================================================================
# Edge Cases
# =============================================================================

def test_cache_multiple_pages_same_title(tmp_path):
    """Handle multiple pages with same title (returns first match)."""
    cache = NotionCache(tmp_path / "cache.json")

    cache.data["pages"]["page-1"] = {
        "id": "page-1",
        "title": "Duplicate",
        "parent_id": None
    }
    cache.data["pages"]["page-2"] = {
        "id": "page-2",
        "title": "Duplicate",
        "parent_id": None
    }

    result = cache.find_by_path("Duplicate", "page")

    # Should return one of them (implementation returns first match)
    assert result in ["page-1", "page-2"]


def test_cache_empty_title(tmp_path):
    """Handle page with empty title."""
    cache = NotionCache(tmp_path / "cache.json")

    results = [{
        "object": "page",
        "id": "page-123",
        "properties": {"title": {"title": [{"plain_text": ""}]}},
        "parent": {"workspace": True},
        "url": "https://notion.so/page-123",
        "archived": False
    }]

    cache.update_from_search(results)

    # Empty string should be stored as-is or "Untitled"
    assert "page-123" in cache.data["pages"]


def test_cache_special_characters_in_title(tmp_path):
    """Handle special characters in titles (excluding path separator)."""
    cache = NotionCache(tmp_path / "cache.json")

    # Test with special characters that don't conflict with path separator
    cache.data["pages"]["page-123"] = {
        "id": "page-123",
        "title": "Page with & ampersand @ symbol",
        "parent_id": None
    }

    result = cache.find_by_path("Page with & ampersand @ symbol", "page")
    assert result == "page-123"

    # Test that titles with / are treated as hierarchical paths (expected behavior)
    cache.data["pages"]["parent-123"] = {
        "id": "parent-123",
        "title": "Parent",
        "parent_id": None
    }
    cache.data["pages"]["child-123"] = {
        "id": "child-123",
        "title": "Child",
        "parent_id": "parent-123"
    }
    cache.data["hierarchy"]["parent-123"] = ["child-123"]

    # "/" in path is treated as separator, not literal character
    result = cache.find_by_path("Parent/Child", "page")
    assert result == "child-123"
