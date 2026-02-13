# CLI Test Plan - notion.py

Comprehensive test plan for the consolidated Notion CLI (`scripts/notion.py`).

## Test Organization

```
tests/cli/
├── test_cli_helpers.py          # Helper functions (unit tests)
├── test_cli_commands.py          # Command execution (integration)
├── test_cli_cache.py             # Cache operations
├── test_cli_diagnostics.py       # Diagnostic commands
├── test_cli_errors.py            # Error handling
└── conftest.py                   # Shared fixtures
```

## Coverage Target: ~90%

---

## 1. Helper Functions Unit Tests

### 1.1 Rich Text Creation

**File**: `test_cli_helpers.py`

#### Test: `test_create_rich_text_simple()`
**Scenario**: Create simple rich text without formatting
```python
result = create_rich_text("Hello world")
expected = [{
    "type": "text",
    "text": {"content": "Hello world"}
}]
```
**Assert**: Result matches expected structure

#### Test: `test_create_rich_text_with_annotations()`
**Scenario**: Create rich text with bold and italic
```python
result = create_rich_text("Bold text", annotations={"bold": True, "italic": True})
```
**Assert**: Annotations properly set

#### Test: `test_create_rich_text_with_link()`
**Scenario**: Create linked text
```python
result = create_rich_text("Link", link="https://example.com")
```
**Assert**: Link URL properly embedded

---

### 1.2 Property Creation

**File**: `test_cli_helpers.py`

#### Test: `test_create_property_title()`
**Scenario**: Create title property
```python
result = create_property("title", "My Title")
```
**Assert**: Correct structure with rich text array

#### Test: `test_create_property_number()`
**Scenario**: Create number property
```python
result = create_property("number", 42)
```
**Assert**: `{"number": 42}`

#### Test: `test_create_property_select()`
**Scenario**: Create select property
```python
result = create_property("select", "Option A")
```
**Assert**: `{"select": {"name": "Option A"}}`

#### Test: `test_create_property_multi_select()`
**Scenario**: Create multi-select with string list
```python
result = create_property("multi_select", ["Tag1", "Tag2"])
```
**Assert**: Array of name objects

#### Test: `test_create_property_date_string()`
**Scenario**: Create date from ISO string
```python
result = create_property("date", "2026-12-31")
```
**Assert**: `{"date": {"start": "2026-12-31"}}`

#### Test: `test_create_property_date_datetime()`
**Scenario**: Create date from datetime object
```python
from datetime import datetime
result = create_property("date", datetime(2026, 12, 31))
```
**Assert**: ISO format in start field

#### Test: `test_create_property_checkbox()`
**Scenario**: Create checkbox property
```python
result = create_property("checkbox", True)
```
**Assert**: `{"checkbox": True}`

#### Test: `test_create_property_invalid_type()`
**Scenario**: Use unsupported property type
```python
with pytest.raises(ValueError, match="Unsupported property type"):
    create_property("invalid_type", "value")
```
**Assert**: ValueError raised

---

### 1.3 Todo Properties Creation

**File**: `test_cli_helpers.py`

#### Test: `test_create_todo_properties_minimal()`
**Scenario**: Create todo with only title
```python
result = create_todo_properties(title="My Task")
```
**Assert**: Only Task property present

#### Test: `test_create_todo_properties_full()`
**Scenario**: Create todo with all properties
```python
result = create_todo_properties(
    title="Complete project",
    description="Finish all tasks",
    due_date="2026-12-31",
    priority="High",
    tags=["work", "urgent"],
    status="In Progress"
)
```
**Assert**: All properties present with correct structure

---

### 1.4 Filter Building

**File**: `test_cli_helpers.py`

#### Test: `test_build_filter_text_equals()`
**Scenario**: Build text equals filter
```python
result = build_filter("Status", "text", "equals", "Done")
```
**Assert**: Correct filter structure

#### Test: `test_build_filter_number_greater_than()`
**Scenario**: Build number comparison filter
```python
result = build_filter("Priority", "number", "greater_than", 5)
```
**Assert**: Correct numeric filter

#### Test: `test_build_filter_date_before()`
**Scenario**: Build date filter
```python
result = build_filter("Due Date", "date", "on_or_before", "2026-12-31")
```
**Assert**: Date filter structure

#### Test: `test_build_filter_is_empty()`
**Scenario**: Build empty filter without value
```python
result = build_filter("Description", "rich_text", "is_empty")
```
**Assert**: is_empty set to True, no value

---

### 1.5 Compound Filters

**File**: `test_cli_helpers.py`

#### Test: `test_build_compound_filter_and()`
**Scenario**: Combine filters with AND
```python
filters = [
    build_filter("Status", "select", "equals", "Done"),
    build_filter("Priority", "select", "equals", "High")
]
result = build_compound_filter(filters, "and")
```
**Assert**: `{"and": [filter1, filter2]}`

#### Test: `test_build_compound_filter_or()`
**Scenario**: Combine filters with OR
```python
result = build_compound_filter(filters, "or")
```
**Assert**: `{"or": [...]}`

#### Test: `test_build_compound_filter_invalid_operator()`
**Scenario**: Use invalid operator
```python
with pytest.raises(ValueError, match="Operator must be"):
    build_compound_filter(filters, "xor")
```
**Assert**: ValueError raised

---

### 1.6 Sort Building

**File**: `test_cli_helpers.py`

#### Test: `test_build_sorts_single()`
**Scenario**: Build single sort
```python
result = build_sorts([("Priority", "descending")])
```
**Assert**: Single sort object with correct structure

#### Test: `test_build_sorts_multiple()`
**Scenario**: Build multiple sorts
```python
result = build_sorts([
    ("Priority", "descending"),
    ("Due Date", "ascending")
])
```
**Assert**: Array with two sort objects

#### Test: `test_build_sorts_invalid_direction()`
**Scenario**: Use invalid direction
```python
with pytest.raises(ValueError, match="Invalid direction"):
    build_sorts([("Priority", "random")])
```
**Assert**: ValueError raised

---

### 1.7 Todo Filter Building

**File**: `test_cli_helpers.py`

#### Test: `test_build_todo_filter_none()`
**Scenario**: Build filter with no parameters
```python
result = build_todo_filter()
```
**Assert**: Returns None

#### Test: `test_build_todo_filter_single()`
**Scenario**: Build filter with one parameter
```python
result = build_todo_filter(status="In Progress")
```
**Assert**: Single filter (not compound)

#### Test: `test_build_todo_filter_multiple()`
**Scenario**: Build filter with multiple parameters
```python
result = build_todo_filter(
    status="In Progress",
    priority="High",
    due_before="2026-03-01"
)
```
**Assert**: Compound AND filter with all conditions

---

### 1.8 Block Creation - Text Blocks

**File**: `test_cli_helpers.py`

#### Test: `test_create_block_paragraph()`
**Scenario**: Create paragraph block
```python
result = create_block("paragraph", "Hello world")
```
**Assert**: Correct paragraph structure

#### Test: `test_create_block_heading_1()`
**Scenario**: Create heading_1 block
```python
result = create_block("heading_1", "Main Title")
```
**Assert**: Correct heading structure

#### Test: `test_create_block_heading_2()`
**Scenario**: Create heading_2 block
```python
result = create_block("heading_2", "Section")
```
**Assert**: Correct structure

#### Test: `test_create_block_heading_3()`
**Scenario**: Create heading_3 block
```python
result = create_block("heading_3", "Subsection")
```
**Assert**: Correct structure

#### Test: `test_create_block_bulleted_list_item()`
**Scenario**: Create bulleted list item
```python
result = create_block("bulleted_list_item", "Item 1")
```
**Assert**: Correct list item structure

#### Test: `test_create_block_numbered_list_item()`
**Scenario**: Create numbered list item
```python
result = create_block("numbered_list_item", "Step 1")
```
**Assert**: Correct structure

#### Test: `test_create_block_quote()`
**Scenario**: Create quote block
```python
result = create_block("quote", "Quote text")
```
**Assert**: Correct quote structure

#### Test: `test_create_block_toggle()`
**Scenario**: Create toggle block
```python
result = create_block("toggle", "Toggle content")
```
**Assert**: Correct structure

---

### 1.9 Block Creation - Special Text Blocks

**File**: `test_cli_helpers.py`

#### Test: `test_create_block_to_do_unchecked()`
**Scenario**: Create unchecked todo block
```python
result = create_block("to_do", "Task item")
```
**Assert**: checked=False by default

#### Test: `test_create_block_to_do_checked()`
**Scenario**: Create checked todo block
```python
result = create_block("to_do", "Task item", checked=True)
```
**Assert**: checked=True

#### Test: `test_create_block_code_plain()`
**Scenario**: Create code block without language
```python
result = create_block("code", "print('hello')")
```
**Assert**: language="plain text" by default

#### Test: `test_create_block_code_python()`
**Scenario**: Create code block with language
```python
result = create_block("code", "print('hello')", language="python")
```
**Assert**: language="python"

#### Test: `test_create_block_callout_default_icon()`
**Scenario**: Create callout without icon
```python
result = create_block("callout", "Important note")
```
**Assert**: icon emoji is default (💡)

#### Test: `test_create_block_callout_custom_icon()`
**Scenario**: Create callout with custom icon
```python
result = create_block("callout", "Warning", icon="⚠️")
```
**Assert**: icon emoji is ⚠️

---

### 1.10 Block Creation - Layout Blocks

**File**: `test_cli_helpers.py`

#### Test: `test_create_block_divider()`
**Scenario**: Create divider block
```python
result = create_block("divider")
```
**Assert**: `{"type": "divider", "divider": {}}`

#### Test: `test_create_block_table_of_contents()`
**Scenario**: Create table of contents
```python
result = create_block("table_of_contents")
```
**Assert**: Correct structure

#### Test: `test_create_block_breadcrumb()`
**Scenario**: Create breadcrumb block
```python
result = create_block("breadcrumb")
```
**Assert**: `{"type": "breadcrumb", "breadcrumb": {}}`

#### Test: `test_create_block_column_list()`
**Scenario**: Create column list
```python
result = create_block("column_list")
```
**Assert**: Correct structure

#### Test: `test_create_block_column()`
**Scenario**: Create column
```python
result = create_block("column")
```
**Assert**: Correct structure

---

### 1.11 Block Creation - Media Blocks

**File**: `test_cli_helpers.py`

#### Test: `test_create_block_image()`
**Scenario**: Create image block
```python
result = create_block("image", url="https://example.com/image.jpg")
```
**Assert**: External URL structure

#### Test: `test_create_block_video()`
**Scenario**: Create video block
```python
result = create_block("video", url="https://example.com/video.mp4")
```
**Assert**: Correct video structure

#### Test: `test_create_block_file()`
**Scenario**: Create file block
```python
result = create_block("file", url="https://example.com/doc.pdf")
```
**Assert**: Correct file structure

#### Test: `test_create_block_pdf()`
**Scenario**: Create PDF block
```python
result = create_block("pdf", url="https://example.com/document.pdf")
```
**Assert**: Correct structure

#### Test: `test_create_block_audio()`
**Scenario**: Create audio block
```python
result = create_block("audio", url="https://example.com/audio.mp3")
```
**Assert**: Correct structure

#### Test: `test_create_block_image_no_url()`
**Scenario**: Create image without URL
```python
with pytest.raises(ValueError, match="requires a url"):
    create_block("image")
```
**Assert**: ValueError raised

---

### 1.12 Block Creation - Special Blocks

**File**: `test_cli_helpers.py`

#### Test: `test_create_block_bookmark()`
**Scenario**: Create bookmark block
```python
result = create_block("bookmark", url="https://example.com")
```
**Assert**: Bookmark structure with URL

#### Test: `test_create_block_embed()`
**Scenario**: Create embed block
```python
result = create_block("embed", url="https://youtube.com/...")
```
**Assert**: Embed structure

#### Test: `test_create_block_link_preview()`
**Scenario**: Create link preview block
```python
result = create_block("link_preview", url="https://example.com")
```
**Assert**: Link preview structure

#### Test: `test_create_block_equation()`
**Scenario**: Create equation block
```python
result = create_block("equation", expression="E=mc^2")
```
**Assert**: Equation with expression

#### Test: `test_create_block_link_to_page()`
**Scenario**: Create link to page block
```python
result = create_block("link_to_page", page_id="abc123")
```
**Assert**: Link to page structure

#### Test: `test_create_block_link_to_page_no_id()`
**Scenario**: Create link to page without ID
```python
with pytest.raises(ValueError, match="requires page_id"):
    create_block("link_to_page")
```
**Assert**: ValueError raised

#### Test: `test_create_block_child_page()`
**Scenario**: Create child page block
```python
result = create_block("child_page", title="Sub Page")
```
**Assert**: Child page structure

#### Test: `test_create_block_child_database()`
**Scenario**: Create child database block
```python
result = create_block("child_database", title="Sub DB")
```
**Assert**: Child database structure

#### Test: `test_create_block_table()`
**Scenario**: Create table block
```python
result = create_block("table", table_width=3, has_column_header=True)
```
**Assert**: Table structure with width

#### Test: `test_create_block_unsupported_type()`
**Scenario**: Use unsupported block type
```python
with pytest.raises(ValueError, match="Unsupported block type"):
    create_block("invalid_block_type")
```
**Assert**: ValueError raised

---

### 1.13 Utility Functions

**File**: `test_cli_helpers.py`

#### Test: `test_is_uuid_valid_with_hyphens()`
**Scenario**: Check valid UUID with hyphens
```python
result = is_uuid("123e4567-e89b-12d3-a456-426614174000")
```
**Assert**: Returns True

#### Test: `test_is_uuid_valid_without_hyphens()`
**Scenario**: Check valid UUID without hyphens
```python
result = is_uuid("123e4567e89b12d3a456426614174000")
```
**Assert**: Returns True

#### Test: `test_is_uuid_invalid_length()`
**Scenario**: Check invalid UUID (wrong length)
```python
result = is_uuid("123456")
```
**Assert**: Returns False

#### Test: `test_is_uuid_invalid_chars()`
**Scenario**: Check invalid UUID (non-hex chars)
```python
result = is_uuid("xyz12345678901234567890123456789")
```
**Assert**: Returns False

---

## 2. Cache Operations Tests

**File**: `test_cli_cache.py`

### 2.1 Cache Initialization

#### Test: `test_cache_init_creates_directory()`
**Scenario**: Initialize cache when directory doesn't exist
```python
cache = NotionCache(tmp_path / "cache.json")
```
**Assert**: Directory created

#### Test: `test_cache_init_loads_existing()`
**Scenario**: Load existing cache file
```python
# Create cache with data
cache1 = NotionCache(cache_file)
cache1.data["pages"]["id1"] = {"title": "Page"}
cache1._save()

# Load in new instance
cache2 = NotionCache(cache_file)
```
**Assert**: Data loaded correctly

#### Test: `test_cache_init_handles_corrupt_file()`
**Scenario**: Handle corrupted JSON file
```python
# Write invalid JSON
cache_file.write_text("invalid json {")

cache = NotionCache(cache_file)
```
**Assert**: Returns empty default structure

---

### 2.2 Cache Staleness

#### Test: `test_cache_is_stale_no_refresh()`
**Scenario**: Check staleness when never refreshed
```python
cache = NotionCache()
```
**Assert**: is_stale() returns True

#### Test: `test_cache_is_stale_recent_refresh()`
**Scenario**: Check staleness after recent refresh
```python
cache = NotionCache()
cache.data["last_refresh"] = datetime.now().isoformat()
cache._save()
```
**Assert**: is_stale() returns False

#### Test: `test_cache_is_stale_old_refresh()`
**Scenario**: Check staleness after 25 hours
```python
cache = NotionCache()
old_time = datetime.now() - timedelta(hours=25)
cache.data["last_refresh"] = old_time.isoformat()
```
**Assert**: is_stale() returns True

---

### 2.3 Cache Updates

#### Test: `test_update_from_search_pages()`
**Scenario**: Update cache with page results
```python
results = [{
    "object": "page",
    "id": "page-123",
    "properties": {"title": {"title": [{"plain_text": "My Page"}]}},
    "parent": {"page_id": "parent-123"},
    "url": "https://notion.so/page-123"
}]
cache.update_from_search(results)
```
**Assert**: Page added to cache with correct data

#### Test: `test_update_from_search_databases()`
**Scenario**: Update cache with database results
```python
results = [{
    "object": "database",
    "id": "db-123",
    "title": [{"plain_text": "My Database"}],
    "parent": {"page_id": "parent-123"}
}]
cache.update_from_search(results)
```
**Assert**: Database added to cache

#### Test: `test_update_from_search_updates_hierarchy()`
**Scenario**: Update cache hierarchy
```python
results = [{
    "object": "page",
    "id": "child-123",
    "parent": {"page_id": "parent-123"},
    # ... other fields
}]
cache.update_from_search(results)
```
**Assert**: Hierarchy includes child under parent

---

### 2.4 Cache Lookups

#### Test: `test_find_by_path_direct_title()`
**Scenario**: Find page by direct title
```python
cache.data["pages"]["page-123"] = {"title": "My Page", ...}
result = cache.find_by_path("My Page", "page")
```
**Assert**: Returns "page-123"

#### Test: `test_find_by_path_case_insensitive()`
**Scenario**: Find page with different case
```python
cache.data["pages"]["page-123"] = {"title": "My Page", ...}
result = cache.find_by_path("my page", "page")
```
**Assert**: Returns "page-123"

#### Test: `test_find_by_path_hierarchical()`
**Scenario**: Find page with parent/child path
```python
cache.data["pages"]["parent-123"] = {
    "title": "Parent",
    "parent_id": None
}
cache.data["pages"]["child-123"] = {
    "title": "Child",
    "parent_id": "parent-123"
}
result = cache.find_by_path("Parent/Child", "page")
```
**Assert**: Returns "child-123"

#### Test: `test_find_by_path_not_found()`
**Scenario**: Lookup non-existent page
```python
result = cache.find_by_path("Nonexistent", "page")
```
**Assert**: Returns None

#### Test: `test_get_title_found()`
**Scenario**: Get title for existing ID
```python
cache.data["pages"]["page-123"] = {"title": "My Page"}
result = cache.get_title("page-123")
```
**Assert**: Returns "My Page"

#### Test: `test_get_title_not_found()`
**Scenario**: Get title for non-existent ID
```python
result = cache.get_title("nonexistent")
```
**Assert**: Returns None

---

## 3. Command Execution Tests (Integration)

**File**: `test_cli_commands.py`

### 3.1 List Commands

#### Test: `test_list_pages_success()`
**Scenario**: List all pages
```python
result = runner.invoke(cli, ['list', 'pages'])
```
**Assert**: Exit code 0, JSON output with pages

#### Test: `test_list_databases_success()`
**Scenario**: List all databases
```python
result = runner.invoke(cli, ['list', 'databases'])
```
**Assert**: Exit code 0, JSON output with databases

#### Test: `test_list_pages_no_api_key()`
**Scenario**: List without API key
```python
result = runner.invoke(cli, ['list', 'pages'])
```
**Assert**: Exit code 1, error message

#### Test: `test_list_with_refresh()`
**Scenario**: List with cache refresh
```python
result = runner.invoke(cli, ['list', 'pages', '--refresh'])
```
**Assert**: Cache refreshed, results returned

---

### 3.2 Search Command

#### Test: `test_search_all()`
**Scenario**: Search without query
```python
result = runner.invoke(cli, ['search'])
```
**Assert**: Returns all pages and databases

#### Test: `test_search_with_query()`
**Scenario**: Search with text query
```python
result = runner.invoke(cli, ['search', 'project'])
```
**Assert**: Results filtered by query

#### Test: `test_search_filter_page()`
**Scenario**: Search only pages
```python
result = runner.invoke(cli, ['search', '--type', 'page'])
```
**Assert**: Only pages in results

#### Test: `test_search_filter_database()`
**Scenario**: Search only databases
```python
result = runner.invoke(cli, ['search', '--type', 'database'])
```
**Assert**: Only databases in results

---

### 3.3 Add Page Commands

#### Test: `test_add_page_minimal()`
**Scenario**: Add page with only title and parent
```python
result = runner.invoke(cli, [
    'add', 'page',
    '--title', 'Test Page',
    '--parent', 'parent-id'
])
```
**Assert**: Page created successfully

#### Test: `test_add_page_with_icon_emoji()`
**Scenario**: Add page with emoji icon
```python
result = runner.invoke(cli, [
    'add', 'page',
    '--title', 'Test Page',
    '--parent', 'parent-id',
    '--icon', '📝'
])
```
**Assert**: Page created with emoji icon

#### Test: `test_add_page_with_icon_url()`
**Scenario**: Add page with URL icon
```python
result = runner.invoke(cli, [
    'add', 'page',
    '--title', 'Test Page',
    '--parent', 'parent-id',
    '--icon', 'https://example.com/icon.png'
])
```
**Assert**: Page created with external icon

#### Test: `test_add_page_with_cover()`
**Scenario**: Add page with cover image
```python
result = runner.invoke(cli, [
    'add', 'page',
    '--title', 'Test Page',
    '--parent', 'parent-id',
    '--cover', 'https://example.com/cover.jpg'
])
```
**Assert**: Page created with cover

#### Test: `test_add_page_with_content()`
**Scenario**: Add page with initial content
```python
result = runner.invoke(cli, [
    'add', 'page',
    '--title', 'Test Page',
    '--parent', 'parent-id',
    '--content', 'Initial content'
])
```
**Assert**: Page created with paragraph block

#### Test: `test_add_page_no_parent()`
**Scenario**: Add page without parent or env var
```python
result = runner.invoke(cli, [
    'add', 'page',
    '--title', 'Test Page'
])
```
**Assert**: Exit code 1, error message

---

### 3.4 Add Database Commands

#### Test: `test_add_database_minimal()`
**Scenario**: Add database with only title
```python
result = runner.invoke(cli, [
    'add', 'database',
    '--title', 'Tasks',
    '--parent', 'parent-id'
])
```
**Assert**: Database created with default schema

#### Test: `test_add_database_template_tasks()`
**Scenario**: Add database with tasks template
```python
result = runner.invoke(cli, [
    'add', 'database',
    '--title', 'Tasks',
    '--parent', 'parent-id',
    '--template', 'tasks'
])
```
**Assert**: Database created with task properties

#### Test: `test_add_database_template_notes()`
**Scenario**: Add database with notes template
```python
result = runner.invoke(cli, [
    'add', 'database',
    '--title', 'Notes',
    '--parent', 'parent-id',
    '--template', 'notes'
])
```
**Assert**: Database created with note properties

#### Test: `test_add_database_custom_properties()`
**Scenario**: Add database with custom schema
```python
result = runner.invoke(cli, [
    'add', 'database',
    '--title', 'CRM',
    '--parent', 'parent-id',
    '--properties', '{"Name": {"title": {}}, "Email": {"email": {}}}'
])
```
**Assert**: Database created with custom properties

#### Test: `test_add_database_invalid_json()`
**Scenario**: Add database with invalid JSON
```python
result = runner.invoke(cli, [
    'add', 'database',
    '--title', 'DB',
    '--parent', 'parent-id',
    '--properties', 'invalid json'
])
```
**Assert**: Exit code 1, JSON error message

---

### 3.5 Add Todo Commands

#### Test: `test_add_todo_minimal()`
**Scenario**: Add todo with only title
```python
result = runner.invoke(cli, [
    'add', 'todo',
    '--title', 'My Task',
    '--database', 'db-id'
])
```
**Assert**: Todo created

#### Test: `test_add_todo_full()`
**Scenario**: Add todo with all properties
```python
result = runner.invoke(cli, [
    'add', 'todo',
    '--title', 'Complete project',
    '--database', 'db-id',
    '--description', 'All tasks',
    '--due-date', '2026-12-31',
    '--priority', 'High',
    '--tags', 'work,urgent',
    '--status', 'In Progress'
])
```
**Assert**: Todo created with all properties

#### Test: `test_add_todo_no_database()`
**Scenario**: Add todo without database
```python
result = runner.invoke(cli, [
    'add', 'todo',
    '--title', 'Task'
])
```
**Assert**: Exit code 1, error message

---

### 3.6 Query Database Commands

#### Test: `test_query_database_no_filter()`
**Scenario**: Query database without filters
```python
result = runner.invoke(cli, [
    'query', 'database', 'db-id'
])
```
**Assert**: All results returned

#### Test: `test_query_database_with_status()`
**Scenario**: Query with status filter
```python
result = runner.invoke(cli, [
    'query', 'database', 'db-id',
    '--status', 'In Progress'
])
```
**Assert**: Filtered results

#### Test: `test_query_database_with_priority()`
**Scenario**: Query with priority filter
```python
result = runner.invoke(cli, [
    'query', 'database', 'db-id',
    '--priority', 'High'
])
```
**Assert**: Filtered results

#### Test: `test_query_database_multiple_filters()`
**Scenario**: Query with multiple filter shortcuts
```python
result = runner.invoke(cli, [
    'query', 'database', 'db-id',
    '--status', 'In Progress',
    '--priority', 'High',
    '--due-before', '2026-03-01'
])
```
**Assert**: Compound filter applied

#### Test: `test_query_database_custom_filter()`
**Scenario**: Query with custom JSON filter
```python
result = runner.invoke(cli, [
    'query', 'database', 'db-id',
    '--filter', '{"property": "Status", "status": {"equals": "Done"}}'
])
```
**Assert**: Custom filter applied

#### Test: `test_query_database_with_sorts()`
**Scenario**: Query with sorting
```python
result = runner.invoke(cli, [
    'query', 'database', 'db-id',
    '--sorts', '[{"property": "Priority", "direction": "descending"}]'
])
```
**Assert**: Results sorted

#### Test: `test_query_database_all_pages()`
**Scenario**: Query with auto-pagination
```python
result = runner.invoke(cli, [
    'query', 'database', 'db-id',
    '--all'
])
```
**Assert**: All pages fetched

---

### 3.7 Blocks Add Commands

#### Test: `test_blocks_add_paragraph()`
**Scenario**: Add paragraph block
```python
result = runner.invoke(cli, [
    'blocks', 'add', 'page-id',
    '--type', 'paragraph',
    '--text', 'Hello world'
])
```
**Assert**: Block created

#### Test: `test_blocks_add_code()`
**Scenario**: Add code block
```python
result = runner.invoke(cli, [
    'blocks', 'add', 'page-id',
    '--type', 'code',
    '--text', 'print("hello")',
    '--language', 'python'
])
```
**Assert**: Code block with language

#### Test: `test_blocks_add_to_do_checked()`
**Scenario**: Add checked todo block
```python
result = runner.invoke(cli, [
    'blocks', 'add', 'page-id',
    '--type', 'to_do',
    '--text', 'Task',
    '--checked'
])
```
**Assert**: Todo block with checked=True

#### Test: `test_blocks_add_callout()`
**Scenario**: Add callout block
```python
result = runner.invoke(cli, [
    'blocks', 'add', 'page-id',
    '--type', 'callout',
    '--text', 'Note',
    '--icon', '💡'
])
```
**Assert**: Callout with custom icon

#### Test: `test_blocks_add_divider()`
**Scenario**: Add divider block
```python
result = runner.invoke(cli, [
    'blocks', 'add', 'page-id',
    '--type', 'divider'
])
```
**Assert**: Divider created (no text required)

#### Test: `test_blocks_add_image()`
**Scenario**: Add image block
```python
result = runner.invoke(cli, [
    'blocks', 'add', 'page-id',
    '--type', 'image',
    '--url', 'https://example.com/image.jpg'
])
```
**Assert**: Image block created

---

### 3.8 Get Commands

#### Test: `test_get_page()`
**Scenario**: Get page by ID
```python
result = runner.invoke(cli, ['get', 'page', 'page-id'])
```
**Assert**: Page data returned

#### Test: `test_get_database()`
**Scenario**: Get database by ID
```python
result = runner.invoke(cli, ['get', 'database', 'db-id'])
```
**Assert**: Database data returned

#### Test: `test_get_block()`
**Scenario**: Get block by ID
```python
result = runner.invoke(cli, ['get', 'block', 'block-id'])
```
**Assert**: Block data returned

---

### 3.9 Update Commands

#### Test: `test_update_page_title()`
**Scenario**: Update page title
```python
result = runner.invoke(cli, [
    'update', 'page', 'page-id',
    '--title', 'New Title'
])
```
**Assert**: Page updated

#### Test: `test_update_page_archive()`
**Scenario**: Archive page
```python
result = runner.invoke(cli, [
    'update', 'page', 'page-id',
    '--archive'
])
```
**Assert**: Page archived

#### Test: `test_update_page_restore()`
**Scenario**: Restore archived page
```python
result = runner.invoke(cli, [
    'update', 'page', 'page-id',
    '--restore'
])
```
**Assert**: Page restored

#### Test: `test_update_database_title()`
**Scenario**: Update database title
```python
result = runner.invoke(cli, [
    'update', 'database', 'db-id',
    '--title', 'New Title'
])
```
**Assert**: Database updated

#### Test: `test_update_block_text()`
**Scenario**: Update block content
```python
result = runner.invoke(cli, [
    'update', 'block', 'block-id',
    '--text', 'Updated content'
])
```
**Assert**: Block updated

---

### 3.10 Delete Commands

#### Test: `test_delete_page()`
**Scenario**: Delete page (archive)
```python
result = runner.invoke(cli, ['delete', 'page', 'page-id'])
```
**Assert**: Page archived

#### Test: `test_delete_block()`
**Scenario**: Delete block
```python
result = runner.invoke(cli, ['delete', 'block', 'block-id'])
```
**Assert**: Block deleted

---

### 3.11 Move Commands

#### Test: `test_move_page()`
**Scenario**: Move page to new parent
```python
result = runner.invoke(cli, [
    'move', 'page', 'page-id',
    '--to', 'new-parent-id'
])
```
**Assert**: Page moved

---

### 3.12 Blocks Subtasks Commands

#### Test: `test_subtasks_add()`
**Scenario**: Add subtask to todo
```python
result = runner.invoke(cli, [
    'blocks', 'subtasks', 'add', 'todo-block-id',
    '--text', 'Subtask 1'
])
```
**Assert**: Subtask created

#### Test: `test_subtasks_list()`
**Scenario**: List subtasks
```python
result = runner.invoke(cli, [
    'blocks', 'subtasks', 'list', 'todo-block-id'
])
```
**Assert**: Subtasks returned

#### Test: `test_subtasks_check()`
**Scenario**: Check subtask
```python
result = runner.invoke(cli, [
    'blocks', 'subtasks', 'check', 'subtask-id'
])
```
**Assert**: Subtask marked complete

#### Test: `test_subtasks_uncheck()`
**Scenario**: Uncheck subtask
```python
result = runner.invoke(cli, [
    'blocks', 'subtasks', 'uncheck', 'subtask-id'
])
```
**Assert**: Subtask marked incomplete

---

## 4. Diagnostic Commands Tests

**File**: `test_cli_diagnostics.py`

### 4.1 Verify Connection

#### Test: `test_verify_connection_success()`
**Scenario**: Verify with valid API key
```python
result = runner.invoke(cli, ['verify-connection'])
```
**Assert**: Exit code 0, success message, user info

#### Test: `test_verify_connection_invalid_key()`
**Scenario**: Verify with invalid API key
```python
result = runner.invoke(cli, ['verify-connection'], env={'NOTION_API_KEY': 'invalid'})
```
**Assert**: Exit code 1, authentication error

#### Test: `test_verify_connection_no_key()`
**Scenario**: Verify without API key
```python
result = runner.invoke(cli, ['verify-connection'])
```
**Assert**: Exit code 1, missing API key error

#### Test: `test_verify_connection_network_error()`
**Scenario**: Verify with network error
```python
# Mock httpx to raise RequestError
result = runner.invoke(cli, ['verify-connection'])
```
**Assert**: Exit code 1, connection error message

---

### 4.2 Check Config

#### Test: `test_check_config_all_set()`
**Scenario**: Check config with all variables set
```python
result = runner.invoke(cli, ['check-config'], env={
    'NOTION_API_KEY': 'ntn_1234567890abcdef',
    'NOTION_DATABASE_ID': 'db-123',
    'NOTION_PARENT_PAGE_ID': 'page-123'
})
```
**Assert**: All variables shown as set, API key masked

#### Test: `test_check_config_partial()`
**Scenario**: Check config with some variables set
```python
result = runner.invoke(cli, ['check-config'], env={
    'NOTION_API_KEY': 'ntn_1234567890abcdef'
})
```
**Assert**: API key set, others not set

#### Test: `test_check_config_none_set()`
**Scenario**: Check config with no variables set
```python
result = runner.invoke(cli, ['check-config'], env={})
```
**Assert**: All variables shown as not set

#### Test: `test_check_config_env_file_exists()`
**Scenario**: Check config with .env file present
```python
# Create .env file
result = runner.invoke(cli, ['check-config'])
```
**Assert**: env_file.exists = True

#### Test: `test_check_config_api_key_masked()`
**Scenario**: Verify API key masking
```python
result = runner.invoke(cli, ['check-config'], env={
    'NOTION_API_KEY': 'ntn_1234567890abcdef'
})
output = json.loads(result.output)
```
**Assert**: API key value ends with "...", length shown

---

## 5. Error Handling Tests

**File**: `test_cli_errors.py`

### 5.1 Authentication Errors

#### Test: `test_error_invalid_api_key()`
**Scenario**: Use invalid API key
```python
result = runner.invoke(cli, ['list', 'pages'], env={'NOTION_API_KEY': 'invalid'})
```
**Assert**: 401 error message

#### Test: `test_error_missing_api_key()`
**Scenario**: No API key provided
```python
result = runner.invoke(cli, ['list', 'pages'], env={})
```
**Assert**: Error message about missing key

---

### 5.2 Not Found Errors

#### Test: `test_error_page_not_found()`
**Scenario**: Get non-existent page
```python
result = runner.invoke(cli, ['get', 'page', 'nonexistent'])
```
**Assert**: Error message about not found

#### Test: `test_error_database_not_found()`
**Scenario**: Get non-existent database
```python
result = runner.invoke(cli, ['get', 'database', 'nonexistent'])
```
**Assert**: Error message about not found

---

### 5.3 Validation Errors

#### Test: `test_error_missing_required_param()`
**Scenario**: Add page without title
```python
result = runner.invoke(cli, ['add', 'page', '--parent', 'parent-id'])
```
**Assert**: Error about missing required option

#### Test: `test_error_invalid_choice()`
**Scenario**: Use invalid choice for enum
```python
result = runner.invoke(cli, [
    'add', 'todo',
    '--title', 'Task',
    '--database', 'db-id',
    '--priority', 'InvalidPriority'
])
```
**Assert**: Error about invalid choice

#### Test: `test_error_invalid_json()`
**Scenario**: Provide invalid JSON
```python
result = runner.invoke(cli, [
    'add', 'database',
    '--title', 'DB',
    '--parent', 'parent-id',
    '--properties', 'invalid json {'
])
```
**Assert**: JSON decode error

---

### 5.4 Permission Errors

#### Test: `test_error_no_access_to_page()`
**Scenario**: Access page without permission
```python
result = runner.invoke(cli, ['get', 'page', 'no-access-page-id'])
```
**Assert**: 403 or 404 error message

---

### 5.5 Network Errors

#### Test: `test_error_connection_timeout()`
**Scenario**: Connection timeout
```python
# Mock httpx to timeout
result = runner.invoke(cli, ['list', 'pages'])
```
**Assert**: Timeout error message

#### Test: `test_error_connection_refused()`
**Scenario**: Connection refused
```python
# Mock httpx to refuse connection
result = runner.invoke(cli, ['list', 'pages'])
```
**Assert**: Connection error message

---

### 5.6 Rate Limit Errors

#### Test: `test_error_rate_limit()`
**Scenario**: Hit rate limit
```python
# Mock API to return 429
result = runner.invoke(cli, ['list', 'pages'])
```
**Assert**: Rate limit error message

---

## 6. Test Fixtures

**File**: `conftest.py`

### Fixtures to Create:

```python
@pytest.fixture
def runner():
    """Click CLI test runner."""
    return CliRunner()

@pytest.fixture
def temp_cache(tmp_path):
    """Temporary cache directory."""
    cache_dir = tmp_path / ".cache" / "notion-cli"
    cache_dir.mkdir(parents=True)
    return cache_dir / "cache.json"

@pytest.fixture
def mock_api_client():
    """Mock httpx AsyncClient for API calls."""
    # Use respx or pytest-httpx
    pass

@pytest.fixture
def sample_page_data():
    """Sample page API response."""
    return {
        "object": "page",
        "id": "page-123",
        "properties": {
            "title": {
                "title": [{"plain_text": "Test Page"}]
            }
        },
        "parent": {"page_id": "parent-123"},
        "url": "https://notion.so/page-123"
    }

@pytest.fixture
def sample_database_data():
    """Sample database API response."""
    return {
        "object": "database",
        "id": "db-123",
        "title": [{"plain_text": "Test DB"}],
        "properties": {
            "Name": {"type": "title"},
            "Status": {"type": "select"}
        }
    }

@pytest.fixture
def sample_block_data():
    """Sample block API response."""
    return {
        "object": "block",
        "id": "block-123",
        "type": "paragraph",
        "paragraph": {
            "rich_text": [{"plain_text": "Test content"}]
        }
    }
```

---

## 7. Coverage Summary

### Expected Coverage by Module:

- **Helper Functions**: 95%+ (pure functions, easy to test)
- **Cache Operations**: 90%+ (some edge cases around file I/O)
- **Command Execution**: 85%+ (integration tests)
- **Error Handling**: 80%+ (many error paths to cover)

### Total Expected Coverage: ~90%

---

## 8. Test Execution

### Run All Tests:
```bash
pytest tests/cli/ -v
```

### Run Specific Test File:
```bash
pytest tests/cli/test_cli_helpers.py -v
```

### Run with Coverage:
```bash
pytest tests/cli/ --cov=scripts.notion --cov-report=term-missing
```

### Run Only Unit Tests (fast):
```bash
pytest tests/cli/test_cli_helpers.py tests/cli/test_cli_cache.py -v
```

### Run Only Integration Tests (slower):
```bash
pytest tests/cli/test_cli_commands.py -v
```

---

## 9. Test Data Requirements

### Mock API Responses Needed:

1. **Authentication**: Valid/invalid user info
2. **Search**: Page and database results with pagination
3. **Pages**: CRUD responses
4. **Databases**: CRUD responses, query results
5. **Blocks**: All 30+ block types responses
6. **Errors**: 401, 403, 404, 429, 500 responses

### Sample Data Files:

```
tests/cli/fixtures/
├── page_response.json
├── database_response.json
├── block_responses/
│   ├── paragraph.json
│   ├── heading_1.json
│   ├── code.json
│   └── ... (all block types)
├── error_responses/
│   ├── 401_unauthorized.json
│   ├── 404_not_found.json
│   └── 429_rate_limit.json
└── query_results.json
```

---

## 10. Continuous Integration

### GitHub Actions Workflow:

```yaml
name: CLI Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.10'
      - name: Install dependencies
        run: |
          pip install uv
          uv pip install -e ".[test]"
      - name: Run CLI tests
        run: pytest tests/cli/ --cov=scripts.notion --cov-report=xml
      - name: Upload coverage
        uses: codecov/codecov-action@v3
```

---

## Summary

This test plan covers:

- ✅ **140+ test cases** across all functionality
- ✅ **Unit tests** for all helper functions (70+ tests)
- ✅ **Integration tests** for all commands (50+ tests)
- ✅ **Cache operations** (15+ tests)
- ✅ **Error handling** (15+ tests)
- ✅ **Diagnostic commands** (10+ tests)

**Estimated test code**: ~2000-2500 lines
**Expected coverage**: ~90%
**Execution time**: ~30 seconds (unit), ~2 minutes (full suite with integration)
