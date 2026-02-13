"""
Unit tests for CLI helper functions.

Tests all helper functions in notion.py including:
- Rich text creation
- Property creation (all types)
- Todo properties
- Filter building
- Sort building
- Block creation (all 30+ types)
- Utility functions
"""
import sys
from pathlib import Path
from datetime import datetime

import pytest

# Import from scripts/notion.py
scripts_dir = Path(__file__).parent.parent.parent / "scripts"
sys.path.insert(0, str(scripts_dir))

from notion import (
    create_rich_text,
    create_property,
    create_todo_properties,
    build_filter,
    build_compound_filter,
    build_sorts,
    build_todo_filter,
    create_block,
    is_uuid,
)


# =============================================================================
# Rich Text Creation Tests
# =============================================================================

def test_create_rich_text_simple():
    """Create simple rich text without formatting."""
    result = create_rich_text("Hello world")

    assert len(result) == 1
    assert result[0]["type"] == "text"
    assert result[0]["text"]["content"] == "Hello world"
    assert "annotations" not in result[0]
    assert "link" not in result[0]["text"]


def test_create_rich_text_with_annotations():
    """Create rich text with bold and italic."""
    result = create_rich_text("Bold text", annotations={"bold": True, "italic": True})

    assert result[0]["annotations"]["bold"] is True
    assert result[0]["annotations"]["italic"] is True


def test_create_rich_text_with_link():
    """Create linked text."""
    result = create_rich_text("Link", link="https://example.com")

    assert result[0]["text"]["link"]["url"] == "https://example.com"


def test_create_rich_text_with_all_options():
    """Create rich text with annotations and link."""
    result = create_rich_text(
        "Formatted link",
        annotations={"bold": True, "underline": True},
        link="https://example.com"
    )

    assert result[0]["text"]["content"] == "Formatted link"
    assert result[0]["text"]["link"]["url"] == "https://example.com"
    assert result[0]["annotations"]["bold"] is True
    assert result[0]["annotations"]["underline"] is True


# =============================================================================
# Property Creation Tests
# =============================================================================

def test_create_property_title():
    """Create title property from string."""
    result = create_property("title", "My Title")

    assert "title" in result
    assert len(result["title"]) == 1
    assert result["title"][0]["type"] == "text"
    assert result["title"][0]["text"]["content"] == "My Title"


def test_create_property_rich_text():
    """Create rich text property from string."""
    result = create_property("rich_text", "Some text")

    assert "rich_text" in result
    assert len(result["rich_text"]) == 1
    assert result["rich_text"][0]["text"]["content"] == "Some text"


def test_create_property_number():
    """Create number property."""
    result = create_property("number", 42)

    assert result == {"number": 42}


def test_create_property_select():
    """Create select property from string."""
    result = create_property("select", "Option A")

    assert result == {"select": {"name": "Option A"}}


def test_create_property_multi_select():
    """Create multi-select property from string list."""
    result = create_property("multi_select", ["Tag1", "Tag2", "Tag3"])

    assert "multi_select" in result
    assert len(result["multi_select"]) == 3
    assert result["multi_select"][0] == {"name": "Tag1"}
    assert result["multi_select"][1] == {"name": "Tag2"}
    assert result["multi_select"][2] == {"name": "Tag3"}


def test_create_property_date_string():
    """Create date property from ISO string."""
    result = create_property("date", "2026-12-31")

    assert result == {"date": {"start": "2026-12-31"}}


def test_create_property_date_datetime():
    """Create date property from datetime object."""
    dt = datetime(2026, 12, 31, 23, 59, 59)
    result = create_property("date", dt)

    assert "date" in result
    assert "start" in result["date"]
    assert result["date"]["start"].startswith("2026-12-31")


def test_create_property_checkbox():
    """Create checkbox property."""
    result_true = create_property("checkbox", True)
    result_false = create_property("checkbox", False)

    assert result_true == {"checkbox": True}
    assert result_false == {"checkbox": False}


def test_create_property_url():
    """Create URL property."""
    result = create_property("url", "https://example.com")

    assert result == {"url": "https://example.com"}


def test_create_property_email():
    """Create email property."""
    result = create_property("email", "test@example.com")

    assert result == {"email": "test@example.com"}


def test_create_property_phone_number():
    """Create phone number property."""
    result = create_property("phone_number", "+1-555-1234")

    assert result == {"phone_number": "+1-555-1234"}


def test_create_property_status():
    """Create status property from string."""
    result = create_property("status", "In Progress")

    assert result == {"status": {"name": "In Progress"}}


def test_create_property_invalid_type():
    """Use unsupported property type."""
    with pytest.raises(ValueError, match="Unsupported property type"):
        create_property("invalid_type", "value")


# =============================================================================
# Todo Properties Tests
# =============================================================================

def test_create_todo_properties_minimal():
    """Create todo with only title."""
    result = create_todo_properties(title="My Task")

    assert "Task" in result
    assert result["Task"]["title"][0]["text"]["content"] == "My Task"
    assert len(result) == 1


def test_create_todo_properties_full():
    """Create todo with all properties."""
    result = create_todo_properties(
        title="Complete project",
        description="Finish all tasks",
        due_date="2026-12-31",
        priority="High",
        tags=["work", "urgent"],
        status="In Progress"
    )

    assert result["Task"]["title"][0]["text"]["content"] == "Complete project"
    assert result["Description"]["rich_text"][0]["text"]["content"] == "Finish all tasks"
    assert result["Due Date"]["date"]["start"] == "2026-12-31"
    assert result["Priority"]["select"]["name"] == "High"
    assert len(result["Tags"]["multi_select"]) == 2
    assert result["Tags"]["multi_select"][0]["name"] == "work"
    assert result["Tags"]["multi_select"][1]["name"] == "urgent"
    assert result["Status"]["status"]["name"] == "In Progress"


def test_create_todo_properties_partial():
    """Create todo with some optional properties."""
    result = create_todo_properties(
        title="Task",
        priority="Low",
        due_date="2026-06-15"
    )

    assert "Task" in result
    assert "Priority" in result
    assert "Due Date" in result
    assert "Description" not in result
    assert "Tags" not in result
    assert "Status" not in result


# =============================================================================
# Filter Building Tests
# =============================================================================

def test_build_filter_text_equals():
    """Build text equals filter."""
    result = build_filter("Status", "text", "equals", "Done")

    assert result == {
        "property": "Status",
        "text": {"equals": "Done"}
    }


def test_build_filter_number_greater_than():
    """Build number comparison filter."""
    result = build_filter("Priority", "number", "greater_than", 5)

    assert result == {
        "property": "Priority",
        "number": {"greater_than": 5}
    }


def test_build_filter_select_equals():
    """Build select equals filter."""
    result = build_filter("Status", "select", "equals", "In Progress")

    assert result == {
        "property": "Status",
        "select": {"equals": "In Progress"}
    }


def test_build_filter_date_before():
    """Build date filter."""
    result = build_filter("Due Date", "date", "on_or_before", "2026-12-31")

    assert result == {
        "property": "Due Date",
        "date": {"on_or_before": "2026-12-31"}
    }


def test_build_filter_is_empty():
    """Build empty filter without value."""
    result = build_filter("Description", "rich_text", "is_empty")

    assert result == {
        "property": "Description",
        "rich_text": {"is_empty": True}
    }


def test_build_filter_is_not_empty():
    """Build not empty filter without value."""
    result = build_filter("Tags", "multi_select", "is_not_empty")

    assert result == {
        "property": "Tags",
        "multi_select": {"is_not_empty": True}
    }


# =============================================================================
# Compound Filter Tests
# =============================================================================

def test_build_compound_filter_and():
    """Combine filters with AND."""
    filter1 = build_filter("Status", "select", "equals", "Done")
    filter2 = build_filter("Priority", "select", "equals", "High")

    result = build_compound_filter([filter1, filter2], "and")

    assert "and" in result
    assert len(result["and"]) == 2
    assert result["and"][0] == filter1
    assert result["and"][1] == filter2


def test_build_compound_filter_or():
    """Combine filters with OR."""
    filter1 = build_filter("Status", "select", "equals", "Done")
    filter2 = build_filter("Status", "select", "equals", "In Progress")

    result = build_compound_filter([filter1, filter2], "or")

    assert "or" in result
    assert len(result["or"]) == 2


def test_build_compound_filter_invalid_operator():
    """Use invalid operator."""
    filters = [build_filter("Status", "select", "equals", "Done")]

    with pytest.raises(ValueError, match="Operator must be"):
        build_compound_filter(filters, "xor")


def test_build_compound_filter_multiple():
    """Combine multiple filters."""
    filters = [
        build_filter("Status", "select", "equals", "Done"),
        build_filter("Priority", "select", "equals", "High"),
        build_filter("Tags", "multi_select", "contains", "urgent")
    ]

    result = build_compound_filter(filters, "and")

    assert len(result["and"]) == 3


# =============================================================================
# Sort Building Tests
# =============================================================================

def test_build_sorts_single():
    """Build single sort."""
    result = build_sorts([("Priority", "descending")])

    assert len(result) == 1
    assert result[0] == {
        "property": "Priority",
        "direction": "descending"
    }


def test_build_sorts_multiple():
    """Build multiple sorts."""
    result = build_sorts([
        ("Priority", "descending"),
        ("Due Date", "ascending"),
        ("Title", "ascending")
    ])

    assert len(result) == 3
    assert result[0]["property"] == "Priority"
    assert result[0]["direction"] == "descending"
    assert result[1]["property"] == "Due Date"
    assert result[1]["direction"] == "ascending"


def test_build_sorts_invalid_direction():
    """Use invalid direction."""
    with pytest.raises(ValueError, match="Invalid direction"):
        build_sorts([("Priority", "random")])


# =============================================================================
# Todo Filter Building Tests
# =============================================================================

def test_build_todo_filter_none():
    """Build filter with no parameters."""
    result = build_todo_filter()

    assert result is None


def test_build_todo_filter_single():
    """Build filter with one parameter."""
    result = build_todo_filter(status="In Progress")

    # Should return single filter, not compound
    assert "property" in result
    assert result["property"] == "Status"
    assert result["status"]["equals"] == "In Progress"


def test_build_todo_filter_multiple():
    """Build filter with multiple parameters."""
    result = build_todo_filter(
        status="In Progress",
        priority="High",
        due_before="2026-03-01"
    )

    # Should return compound AND filter
    assert "and" in result
    assert len(result["and"]) == 3


def test_build_todo_filter_all_parameters():
    """Build filter with all parameters."""
    result = build_todo_filter(
        status="Done",
        priority="Low",
        due_before="2026-12-31",
        due_after="2026-01-01",
        tags="work"
    )

    assert "and" in result
    assert len(result["and"]) == 5


# =============================================================================
# Block Creation - Text Blocks
# =============================================================================

def test_create_block_paragraph():
    """Create paragraph block."""
    result = create_block("paragraph", "Hello world")

    assert result["type"] == "paragraph"
    assert result["paragraph"]["rich_text"][0]["text"]["content"] == "Hello world"


def test_create_block_heading_1():
    """Create heading_1 block."""
    result = create_block("heading_1", "Main Title")

    assert result["type"] == "heading_1"
    assert result["heading_1"]["rich_text"][0]["text"]["content"] == "Main Title"


def test_create_block_heading_2():
    """Create heading_2 block."""
    result = create_block("heading_2", "Section")

    assert result["type"] == "heading_2"
    assert result["heading_2"]["rich_text"][0]["text"]["content"] == "Section"


def test_create_block_heading_3():
    """Create heading_3 block."""
    result = create_block("heading_3", "Subsection")

    assert result["type"] == "heading_3"
    assert result["heading_3"]["rich_text"][0]["text"]["content"] == "Subsection"


def test_create_block_bulleted_list_item():
    """Create bulleted list item."""
    result = create_block("bulleted_list_item", "Item 1")

    assert result["type"] == "bulleted_list_item"
    assert result["bulleted_list_item"]["rich_text"][0]["text"]["content"] == "Item 1"


def test_create_block_numbered_list_item():
    """Create numbered list item."""
    result = create_block("numbered_list_item", "Step 1")

    assert result["type"] == "numbered_list_item"
    assert result["numbered_list_item"]["rich_text"][0]["text"]["content"] == "Step 1"


def test_create_block_quote():
    """Create quote block."""
    result = create_block("quote", "Quote text")

    assert result["type"] == "quote"
    assert result["quote"]["rich_text"][0]["text"]["content"] == "Quote text"


def test_create_block_toggle():
    """Create toggle block."""
    result = create_block("toggle", "Toggle content")

    assert result["type"] == "toggle"
    assert result["toggle"]["rich_text"][0]["text"]["content"] == "Toggle content"


# =============================================================================
# Block Creation - Special Text Blocks
# =============================================================================

def test_create_block_to_do_unchecked():
    """Create unchecked todo block."""
    result = create_block("to_do", "Task item")

    assert result["type"] == "to_do"
    assert result["to_do"]["checked"] is False
    assert result["to_do"]["rich_text"][0]["text"]["content"] == "Task item"


def test_create_block_to_do_checked():
    """Create checked todo block."""
    result = create_block("to_do", "Task item", checked=True)

    assert result["type"] == "to_do"
    assert result["to_do"]["checked"] is True


def test_create_block_code_plain():
    """Create code block without language."""
    result = create_block("code", "print('hello')")

    assert result["type"] == "code"
    assert result["code"]["language"] == "plain text"
    assert result["code"]["rich_text"][0]["text"]["content"] == "print('hello')"


def test_create_block_code_python():
    """Create code block with language."""
    result = create_block("code", "print('hello')", language="python")

    assert result["type"] == "code"
    assert result["code"]["language"] == "python"


def test_create_block_callout_default_icon():
    """Create callout without icon."""
    result = create_block("callout", "Important note")

    assert result["type"] == "callout"
    assert result["callout"]["icon"]["emoji"] == "💡"
    assert result["callout"]["rich_text"][0]["text"]["content"] == "Important note"


def test_create_block_callout_custom_icon():
    """Create callout with custom icon."""
    result = create_block("callout", "Warning", icon="⚠️")

    assert result["type"] == "callout"
    assert result["callout"]["icon"]["emoji"] == "⚠️"


# =============================================================================
# Block Creation - Layout Blocks
# =============================================================================

def test_create_block_divider():
    """Create divider block."""
    result = create_block("divider")

    assert result == {"type": "divider", "divider": {}}


def test_create_block_table_of_contents():
    """Create table of contents."""
    result = create_block("table_of_contents")

    assert result["type"] == "table_of_contents"
    assert "table_of_contents" in result


def test_create_block_breadcrumb():
    """Create breadcrumb block."""
    result = create_block("breadcrumb")

    assert result == {"type": "breadcrumb", "breadcrumb": {}}


def test_create_block_column_list():
    """Create column list."""
    result = create_block("column_list")

    assert result == {"type": "column_list", "column_list": {}}


def test_create_block_column():
    """Create column."""
    result = create_block("column")

    assert result == {"type": "column", "column": {}}


# =============================================================================
# Block Creation - Media Blocks
# =============================================================================

def test_create_block_image():
    """Create image block."""
    result = create_block("image", url="https://example.com/image.jpg")

    assert result["type"] == "image"
    assert result["image"]["type"] == "external"
    assert result["image"]["external"]["url"] == "https://example.com/image.jpg"


def test_create_block_video():
    """Create video block."""
    result = create_block("video", url="https://example.com/video.mp4")

    assert result["type"] == "video"
    assert result["video"]["external"]["url"] == "https://example.com/video.mp4"


def test_create_block_file():
    """Create file block."""
    result = create_block("file", url="https://example.com/doc.pdf")

    assert result["type"] == "file"
    assert result["file"]["external"]["url"] == "https://example.com/doc.pdf"


def test_create_block_pdf():
    """Create PDF block."""
    result = create_block("pdf", url="https://example.com/document.pdf")

    assert result["type"] == "pdf"
    assert result["pdf"]["external"]["url"] == "https://example.com/document.pdf"


def test_create_block_audio():
    """Create audio block."""
    result = create_block("audio", url="https://example.com/audio.mp3")

    assert result["type"] == "audio"
    assert result["audio"]["external"]["url"] == "https://example.com/audio.mp3"


def test_create_block_image_no_url():
    """Create image without URL."""
    with pytest.raises(ValueError, match="requires a url"):
        create_block("image")


# =============================================================================
# Block Creation - Special Blocks
# =============================================================================

def test_create_block_bookmark():
    """Create bookmark block."""
    result = create_block("bookmark", url="https://example.com")

    assert result["type"] == "bookmark"
    assert result["bookmark"]["url"] == "https://example.com"


def test_create_block_embed():
    """Create embed block."""
    result = create_block("embed", url="https://youtube.com/watch?v=123")

    assert result["type"] == "embed"
    assert result["embed"]["url"] == "https://youtube.com/watch?v=123"


def test_create_block_link_preview():
    """Create link preview block."""
    result = create_block("link_preview", url="https://example.com")

    assert result["type"] == "link_preview"
    assert result["link_preview"]["url"] == "https://example.com"


def test_create_block_equation():
    """Create equation block."""
    result = create_block("equation", expression="E=mc^2")

    assert result["type"] == "equation"
    assert result["equation"]["expression"] == "E=mc^2"


def test_create_block_link_to_page():
    """Create link to page block."""
    result = create_block("link_to_page", page_id="abc123")

    assert result["type"] == "link_to_page"
    assert result["link_to_page"]["type"] == "page_id"
    assert result["link_to_page"]["page_id"] == "abc123"


def test_create_block_link_to_page_no_id():
    """Create link to page without ID."""
    with pytest.raises(ValueError, match="requires page_id"):
        create_block("link_to_page")


def test_create_block_child_page():
    """Create child page block."""
    result = create_block("child_page", title="Sub Page")

    assert result["type"] == "child_page"
    assert result["child_page"]["title"] == "Sub Page"


def test_create_block_child_database():
    """Create child database block."""
    result = create_block("child_database", title="Sub DB")

    assert result["type"] == "child_database"
    assert result["child_database"]["title"] == "Sub DB"


def test_create_block_table():
    """Create table block."""
    result = create_block("table", table_width=3, has_column_header=True)

    assert result["type"] == "table"
    assert result["table"]["table_width"] == 3
    assert result["table"]["has_column_header"] is True


def test_create_block_unsupported_type():
    """Use unsupported block type."""
    with pytest.raises(ValueError, match="Unsupported block type"):
        create_block("invalid_block_type")


# =============================================================================
# Utility Functions
# =============================================================================

def test_is_uuid_valid_with_hyphens():
    """Check valid UUID with hyphens."""
    result = is_uuid("123e4567-e89b-12d3-a456-426614174000")

    assert result is True


def test_is_uuid_valid_without_hyphens():
    """Check valid UUID without hyphens."""
    result = is_uuid("123e4567e89b12d3a456426614174000")

    assert result is True


def test_is_uuid_invalid_length():
    """Check invalid UUID (wrong length)."""
    result = is_uuid("123456")

    assert result is False


def test_is_uuid_invalid_chars():
    """Check invalid UUID (non-hex chars)."""
    result = is_uuid("xyz12345678901234567890123456789")

    assert result is False


def test_is_uuid_empty_string():
    """Check empty string."""
    result = is_uuid("")

    assert result is False


def test_is_uuid_notion_id():
    """Check real Notion ID format."""
    result = is_uuid("a1b2c3d4e5f6789012345678abcdef90")

    assert result is True
