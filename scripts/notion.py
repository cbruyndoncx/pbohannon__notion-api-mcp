#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "httpx",
#     "click",
#     "python-dotenv",
#     "structlog",
# ]
# ///
"""
Notion CLI - Human-friendly command-line interface for Notion API.

Usage:
    notion.py list pages
    notion.py list databases
    notion.py search "project"
    notion.py add page --title "Meeting Notes" --parent "Work/Projects"
    notion.py add database --title "Tasks" --parent "Work"
    notion.py add todo --title "Complete project" --database "Tasks"
    notion.py add block --parent "Quick Notes" --text "New idea"
    notion.py blocks add "Quick Notes" --type paragraph --text "Hello"
    notion.py get page "Work/Meeting Notes"
    notion.py get database "Tasks"
    notion.py get block <block-id>
    notion.py update page "Meeting Notes" --title "Project Meeting"
    notion.py update database "Tasks" --title "My Tasks"
    notion.py update block <block-id> --text "Updated content"
    notion.py delete page "Old Notes"
    notion.py query database "Tasks" --status "In Progress"
    notion.py search todos --database "Tasks" --priority "High"
    notion.py move page "Note" --to "Archive"
    notion.py blocks subtasks add <todo-block-id> --text "Subtask"
    notion.py refresh-cache

Features:
    - Human-readable names instead of IDs
    - Path-like syntax for hierarchical pages (e.g., "Parent/Child")
    - Smart caching to minimize API calls
    - REST-like verb structure (add, get, update, delete, list, search, query, move)
    - Complete Notion API coverage: databases, todos, all block types, properties

Environment Variables:
    NOTION_API_KEY - Required: Notion integration token
    NOTION_DATABASE_ID - Optional: Default database for todos
    NOTION_PARENT_PAGE_ID - Optional: Default parent for new pages/databases
"""

import sys
import os
import json
import asyncio
from pathlib import Path
from typing import Dict, Any, Optional, List, Union
from datetime import datetime, timedelta

# Save built-in types before they get shadowed by function names
_list = list
_dict = dict

# Add src to Python path for local imports
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

import click
import httpx
from dotenv import load_dotenv

# Load .env file if it exists
env_path = project_root / ".env"
if env_path.exists():
    load_dotenv(env_path)

# Cache location
CACHE_DIR = Path.home() / ".cache" / "notion-cli"
CACHE_FILE = CACHE_DIR / "cache.json"
CACHE_TTL_HOURS = 24


class NotionCache:
    """Manages local cache of Notion pages and databases for name→ID resolution."""

    def __init__(self, cache_path: Path = CACHE_FILE):
        self.cache_path = cache_path
        self.cache_path.parent.mkdir(parents=True, exist_ok=True)
        self.data = self._load()

    def _load(self) -> Dict[str, Any]:
        """Load cache from disk."""
        if not self.cache_path.exists():
            return {
                "pages": {},
                "databases": {},
                "hierarchy": {},  # parent_id → [child_ids]
                "last_refresh": None
            }

        try:
            with open(self.cache_path, 'r') as f:
                return json.load(f)
        except Exception:
            return {
                "pages": {},
                "databases": {},
                "hierarchy": {},
                "last_refresh": None
            }

    def _save(self):
        """Save cache to disk."""
        with open(self.cache_path, 'w') as f:
            json.dump(self.data, f, indent=2)

    def is_stale(self) -> bool:
        """Check if cache needs refresh."""
        if not self.data.get("last_refresh"):
            return True

        last_refresh = datetime.fromisoformat(self.data["last_refresh"])
        return datetime.now() - last_refresh > timedelta(hours=CACHE_TTL_HOURS)

    def update_from_search(self, results: List[Dict[str, Any]]):
        """Update cache from search results."""
        for item in results:
            obj_type = item.get("object")
            item_id = item.get("id")

            # Extract title
            title = "Untitled"
            if obj_type == "page":
                props = item.get("properties", {})
                title_prop = props.get("title") or props.get("Name")
                if title_prop and title_prop.get("title"):
                    title = title_prop["title"][0].get("plain_text", "Untitled")
            elif obj_type == "database":
                if item.get("title") and len(item["title"]) > 0:
                    title = item["title"][0].get("plain_text", "Untitled")

            # Get parent info
            parent = item.get("parent", {})
            parent_id = parent.get("page_id") or parent.get("database_id") or parent.get("workspace")

            # Store in cache
            cache_entry = {
                "id": item_id,
                "title": title,
                "parent_id": parent_id,
                "url": item.get("url"),
                "last_seen": datetime.now().isoformat(),
                "archived": item.get("archived", False)
            }

            if obj_type == "page":
                self.data["pages"][item_id] = cache_entry
            elif obj_type == "database":
                self.data["databases"][item_id] = cache_entry

            # Update hierarchy
            if parent_id and parent_id != "workspace":
                if parent_id not in self.data["hierarchy"]:
                    self.data["hierarchy"][parent_id] = []
                if item_id not in self.data["hierarchy"][parent_id]:
                    self.data["hierarchy"][parent_id].append(item_id)

        self.data["last_refresh"] = datetime.now().isoformat()
        self._save()

    def find_by_path(self, path: str, obj_type: str = "page") -> Optional[str]:
        """
        Resolve a path like 'Parent/Child/Page' to a page ID.

        Args:
            path: Slash-separated path or direct title
            obj_type: 'page' or 'database'

        Returns:
            ID if found, None otherwise
        """
        parts = [p.strip() for p in path.split("/")]

        if len(parts) == 1:
            # Direct lookup by title
            return self._find_by_title(parts[0], obj_type)

        # Traverse hierarchy
        current_id = None
        for i, part in enumerate(parts):
            if i == 0:
                # Find root by title
                current_id = self._find_by_title(part, obj_type, parent_id=None)
            else:
                # Find child by title under current parent
                current_id = self._find_by_title(part, obj_type, parent_id=current_id)

            if not current_id:
                return None

        return current_id

    def _find_by_title(self, title: str, obj_type: str, parent_id: Optional[str] = None) -> Optional[str]:
        """Find item by title, optionally filtering by parent."""
        collection = self.data.get("pages" if obj_type == "page" else "databases", {})

        matches = []
        for item_id, item in collection.items():
            if item["title"].lower() == title.lower():
                if parent_id is None or item.get("parent_id") == parent_id:
                    matches.append(item_id)

        # Return first match (could enhance to handle ambiguity)
        return matches[0] if matches else None

    def get_title(self, item_id: str) -> Optional[str]:
        """Get title for a given ID."""
        for collection in ["pages", "databases"]:
            item = self.data.get(collection, {}).get(item_id)
            if item:
                return item["title"]
        return None


# ============================================================================
# Helper Functions - Property, Filter, Block Builders
# ============================================================================

def create_rich_text(content: str, annotations: Optional[Dict[str, bool]] = None, link: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Create rich text array for Notion API.

    Args:
        content: Text content
        annotations: Formatting (bold, italic, etc.)
        link: Optional URL for link

    Returns:
        Rich text array
    """
    text_obj = {"content": content}
    if link:
        text_obj["link"] = {"url": link}

    rich_text_item = {
        "type": "text",
        "text": text_obj
    }

    if annotations:
        rich_text_item["annotations"] = annotations

    return [rich_text_item]


def create_property(prop_type: str, value: Any, property_name: Optional[str] = None) -> Dict[str, Any]:
    """
    Create a Notion property of any type.

    Args:
        prop_type: Property type (title, rich_text, number, select, multi_select, date, etc.)
        value: Property value
        property_name: Property name (for schema definitions)

    Returns:
        Property object for Notion API
    """
    if prop_type == "title":
        if isinstance(value, str):
            return {"title": create_rich_text(value)}
        return {"title": value}

    elif prop_type == "rich_text":
        if isinstance(value, str):
            return {"rich_text": create_rich_text(value)}
        return {"rich_text": value}

    elif prop_type == "number":
        return {"number": value}

    elif prop_type == "select":
        if isinstance(value, str):
            return {"select": {"name": value}}
        return {"select": value}

    elif prop_type == "multi_select":
        if isinstance(value, _list) and all(isinstance(v, str) for v in value):
            return {"multi_select": [{"name": v} for v in value]}
        return {"multi_select": value}

    elif prop_type == "date":
        if isinstance(value, str):
            return {"date": {"start": value}}
        elif isinstance(value, datetime):
            return {"date": {"start": value.isoformat()}}
        return {"date": value}

    elif prop_type == "checkbox":
        return {"checkbox": bool(value)}

    elif prop_type == "url":
        return {"url": value}

    elif prop_type == "email":
        return {"email": value}

    elif prop_type == "phone_number":
        return {"phone_number": value}

    elif prop_type == "status":
        if isinstance(value, str):
            return {"status": {"name": value}}
        return {"status": value}

    else:
        raise ValueError(f"Unsupported property type: {prop_type}")


def create_todo_properties(
    title: str,
    description: Optional[str] = None,
    due_date: Optional[str] = None,
    priority: Optional[str] = None,
    tags: Optional[List[str]] = None,
    status: Optional[str] = None,
    assignee: Optional[str] = None
) -> Dict[str, Any]:
    """
    Create properties for a todo item (follows MCP server pattern).

    Args:
        title: Todo title
        description: Optional description
        due_date: Optional due date (ISO format)
        priority: Optional priority level
        tags: Optional tags list
        status: Optional status
        assignee: Optional assignee (note: requires user ID, not name)

    Returns:
        Properties dict for page creation
    """
    properties: Dict[str, Any] = {
        "Task": create_property("title", title)
    }

    if description:
        properties["Description"] = create_property("rich_text", description)

    if due_date:
        properties["Due Date"] = create_property("date", due_date)

    if priority:
        properties["Priority"] = create_property("select", priority)

    if tags:
        properties["Tags"] = create_property("multi_select", tags)

    if status:
        properties["Status"] = create_property("status", status)

    # Note: assignee requires actual Notion user IDs
    # if assignee:
    #     properties["Assignee"] = {"people": [{"id": assignee}]}

    return properties


def build_filter(property_name: str, filter_type: str, condition: str, value: Any = None) -> Dict[str, Any]:
    """
    Build a Notion API filter for database queries.

    Args:
        property_name: Property to filter on
        filter_type: Type of filter (text, number, checkbox, select, date, etc.)
        condition: Condition (equals, contains, before, after, etc.)
        value: Value to filter by (None for is_empty/is_not_empty)

    Returns:
        Filter object
    """
    filter_obj = {"property": property_name, filter_type: {}}

    if value is None and condition in ["is_empty", "is_not_empty"]:
        filter_obj[filter_type][condition] = True
    else:
        filter_obj[filter_type][condition] = value

    return filter_obj


def build_compound_filter(filters: List[Dict[str, Any]], operator: str = "and") -> Dict[str, Any]:
    """
    Build a compound filter with AND/OR logic.

    Args:
        filters: List of filter objects
        operator: 'and' or 'or'

    Returns:
        Compound filter object
    """
    if operator not in ("and", "or"):
        raise ValueError("Operator must be 'and' or 'or'")

    return {operator: filters}


def build_sorts(sorts: List[tuple]) -> List[Dict[str, Any]]:
    """
    Build sort specifications.

    Args:
        sorts: List of (property_name, direction) tuples

    Returns:
        List of sort objects
    """
    sort_objects = []
    for prop, direction in sorts:
        if direction not in ("ascending", "descending"):
            raise ValueError(f"Invalid direction: {direction}")
        sort_objects.append({
            "property": prop,
            "direction": direction
        })
    return sort_objects


def build_todo_filter(
    status: Optional[str] = None,
    priority: Optional[str] = None,
    due_before: Optional[str] = None,
    due_after: Optional[str] = None,
    tags: Optional[str] = None
) -> Optional[Dict[str, Any]]:
    """
    Build filter for todo searches with common shortcuts.

    Args:
        status: Status value
        priority: Priority value
        due_before: Due before date
        due_after: Due after date
        tags: Tag to filter by

    Returns:
        Filter object or None if no filters
    """
    conditions = []

    if status:
        conditions.append(build_filter("Status", "status", "equals", status))

    if priority:
        conditions.append(build_filter("Priority", "select", "equals", priority))

    if due_before:
        conditions.append(build_filter("Due Date", "date", "on_or_before", due_before))

    if due_after:
        conditions.append(build_filter("Due Date", "date", "on_or_after", due_after))

    if tags:
        conditions.append(build_filter("Tags", "multi_select", "contains", tags))

    if not conditions:
        return None

    if len(conditions) == 1:
        return conditions[0]

    return build_compound_filter(conditions, "and")


def create_block(
    block_type: str,
    content: Optional[str] = None,
    annotations: Optional[Dict[str, bool]] = None,
    **kwargs: Any
) -> Dict[str, Any]:
    """
    Universal block creator supporting all Notion block types.

    Supported types:
        Text: paragraph, heading_1/2/3, bulleted_list_item, numbered_list_item,
              to_do, toggle, quote, code, callout
        Media: image, video, file, pdf, audio, bookmark, embed, link_preview
        Layout: divider, table_of_contents, breadcrumb, column_list, column
        Special: equation, table, table_row, link_to_page, child_page, child_database

    Args:
        block_type: Block type name
        content: Text content (for text blocks)
        annotations: Text formatting options
        **kwargs: Block-specific options (language for code, checked for to_do, etc.)

    Returns:
        Block object for Notion API
    """
    # Special blocks without content
    if block_type == "divider":
        return {"type": "divider", "divider": {}}

    if block_type == "table_of_contents":
        return {"type": "table_of_contents", "table_of_contents": {"color": kwargs.get("color", "default")}}

    if block_type == "breadcrumb":
        return {"type": "breadcrumb", "breadcrumb": {}}

    if block_type == "column_list":
        return {"type": "column_list", "column_list": {}}

    if block_type == "column":
        return {"type": "column", "column": {}}

    # Text blocks
    if block_type in ["paragraph", "heading_1", "heading_2", "heading_3", "quote", "callout", "toggle"]:
        block_content = {}
        if content:
            block_content["rich_text"] = create_rich_text(content, annotations)

        # Callout-specific properties
        if block_type == "callout":
            block_content["icon"] = {"emoji": kwargs.get("icon", "💡")}
            block_content["color"] = kwargs.get("color", "default")

        return {"type": block_type, block_type: block_content}

    # List items
    if block_type in ["bulleted_list_item", "numbered_list_item"]:
        block_content = {}
        if content:
            block_content["rich_text"] = create_rich_text(content, annotations)
        return {"type": block_type, block_type: block_content}

    # To-do blocks
    if block_type == "to_do":
        block_content = {
            "checked": kwargs.get("checked", False)
        }
        if content:
            block_content["rich_text"] = create_rich_text(content, annotations)
        return {"type": "to_do", "to_do": block_content}

    # Code blocks
    if block_type == "code":
        block_content = {
            "language": kwargs.get("language", "plain text")
        }
        if content:
            block_content["rich_text"] = create_rich_text(content, annotations)
        return {"type": "code", "code": block_content}

    # Equation blocks
    if block_type == "equation":
        return {
            "type": "equation",
            "equation": {"expression": kwargs.get("expression", content or "")}
        }

    # Media blocks (image, video, file, pdf, audio)
    if block_type in ["image", "video", "file", "pdf", "audio"]:
        url = kwargs.get("url", content)
        if not url:
            raise ValueError(f"{block_type} requires a url")

        return {
            "type": block_type,
            block_type: {
                "type": "external",
                "external": {"url": url}
            }
        }

    # Bookmark and embed
    if block_type in ["bookmark", "embed", "link_preview"]:
        url = kwargs.get("url", content)
        if not url:
            raise ValueError(f"{block_type} requires a url")

        return {
            "type": block_type,
            block_type: {"url": url}
        }

    # Link to page
    if block_type == "link_to_page":
        page_id = kwargs.get("page_id")
        if not page_id:
            raise ValueError("link_to_page requires page_id")

        return {
            "type": "link_to_page",
            "link_to_page": {
                "type": "page_id",
                "page_id": page_id
            }
        }

    # Child page
    if block_type == "child_page":
        title = kwargs.get("title", content)
        if not title:
            raise ValueError("child_page requires title")

        return {
            "type": "child_page",
            "child_page": {"title": title}
        }

    # Child database
    if block_type == "child_database":
        title = kwargs.get("title", content)
        if not title:
            raise ValueError("child_database requires title")

        return {
            "type": "child_database",
            "child_database": {"title": title}
        }

    # Table (simplified - full table creation is complex)
    if block_type == "table":
        table_width = kwargs.get("table_width", 2)
        has_column_header = kwargs.get("has_column_header", False)
        has_row_header = kwargs.get("has_row_header", False)

        return {
            "type": "table",
            "table": {
                "table_width": table_width,
                "has_column_header": has_column_header,
                "has_row_header": has_row_header
            }
        }

    raise ValueError(f"Unsupported block type: {block_type}")


# ============================================================================
# Auth and Utility Functions
# ============================================================================

def get_auth_headers(api_key: str | None = None) -> dict:
    """Get Notion API authentication headers."""
    if api_key is None:
        api_key = os.getenv("NOTION_API_KEY")

    if not api_key or api_key.strip() == "":
        raise ValueError("No API key provided and NOTION_API_KEY environment variable not set")

    return {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "Notion-Version": "2022-06-28"
    }


def is_uuid(value: str) -> bool:
    """Check if a string looks like a Notion UUID."""
    # Notion IDs are 32 hex chars, sometimes with hyphens
    cleaned = value.replace("-", "")
    return len(cleaned) == 32 and all(c in "0123456789abcdef" for c in cleaned.lower())


async def search_notion(api_key: str, query: str = "", filter_type: Optional[str] = None) -> List[Dict[str, Any]]:
    """Search Notion API and return all results."""
    headers = get_auth_headers(api_key)
    all_results = []

    async with httpx.AsyncClient(
        base_url="https://api.notion.com/v1/",
        headers=headers,
        timeout=30.0
    ) as client:
        start_cursor = None
        has_more = True

        while has_more:
            body = {
                "page_size": 100,
                "sort": {
                    "direction": "descending",
                    "timestamp": "last_edited_time"
                }
            }

            if query:
                body["query"] = query

            if filter_type:
                body["filter"] = {
                    "value": filter_type,
                    "property": "object"
                }

            if start_cursor:
                body["start_cursor"] = start_cursor

            response = await client.post("search", json=body)
            response.raise_for_status()
            data = response.json()

            all_results.extend(data.get("results", []))
            has_more = data.get("has_more", False)
            start_cursor = data.get("next_cursor")

    return all_results


def resolve_id(cache: NotionCache, name_or_id: str, obj_type: str, api_key: str) -> str:
    """
    Resolve a human-readable name or path to an ID.

    Args:
        cache: NotionCache instance
        name_or_id: Either a UUID, title, or path like "Parent/Child"
        obj_type: 'page' or 'database'
        api_key: Notion API key for fallback search

    Returns:
        Resolved ID

    Raises:
        click.ClickException if not found
    """
    # If it's already a UUID, return it
    if is_uuid(name_or_id):
        return name_or_id

    # Try cache lookup
    resolved_id = cache.find_by_path(name_or_id, obj_type)
    if resolved_id:
        return resolved_id

    # Fallback: search API
    click.echo(f"🔍 '{name_or_id}' not in cache, searching...", err=True)
    results = asyncio.run(search_notion(api_key, query=name_or_id.split("/")[-1], filter_type=obj_type))

    if results:
        cache.update_from_search(results)
        resolved_id = cache.find_by_path(name_or_id, obj_type)
        if resolved_id:
            return resolved_id

    raise click.ClickException(f"Could not find {obj_type} '{name_or_id}'")


# ============================================================================
# CLI Commands
# ============================================================================

@click.group()
def cli():
    """Notion CLI - Human-friendly interface to Notion API."""
    pass


# ============================================================================
# LIST commands
# ============================================================================

@cli.command()
@click.argument('entity', type=click.Choice(['pages', 'databases']))
@click.option('--api-key', envvar='NOTION_API_KEY', help='Notion API key')
@click.option('--refresh', is_flag=True, help='Force cache refresh')
def list(entity: str, api_key: str, refresh: bool):
    """
    List all pages or databases.

    Examples:
        notion.py list pages
        notion.py list databases
        notion.py list pages --refresh
    """
    if not api_key:
        click.echo("❌ Error: NOTION_API_KEY required", err=True)
        sys.exit(1)

    cache = NotionCache()

    # Refresh cache if needed
    if refresh or cache.is_stale():
        click.echo("🔄 Refreshing cache...", err=True)
        results = asyncio.run(search_notion(api_key))
        cache.update_from_search(results)

    # Display results
    collection = cache.data.get(entity, {})

    if not collection:
        click.echo(f"No {entity} found. Try: notion.py list {entity} --refresh")
        return

    items = []
    for item_id, item in collection.items():
        if not item.get("archived", False):
            items.append({
                "title": item["title"],
                "id": item_id,
                "url": item.get("url", ""),
                "last_seen": item.get("last_seen", "")
            })

    # Sort by title
    items.sort(key=lambda x: x["title"])

    click.echo(json.dumps({"success": True, "count": len(items), entity: items}, indent=2))


# ============================================================================
# SEARCH command
# ============================================================================

@cli.command()
@click.argument('query', required=False, default='')
@click.option('--api-key', envvar='NOTION_API_KEY', help='Notion API key')
@click.option('--type', 'filter_type', type=click.Choice(['page', 'database']), help='Filter by type')
def search(query: str, api_key: str, filter_type: Optional[str]):
    """
    Search for pages and databases.

    Examples:
        notion.py search "project"
        notion.py search --type page "meeting"
        notion.py search
    """
    if not api_key:
        click.echo("❌ Error: NOTION_API_KEY required", err=True)
        sys.exit(1)

    results = asyncio.run(search_notion(api_key, query, filter_type))

    # Update cache
    cache = NotionCache()
    cache.update_from_search(results)

    # Format results
    formatted = []
    for item in results:
        obj_type = item.get("object")

        # Extract title
        title = "Untitled"
        if obj_type == "page":
            props = item.get("properties", {})
            title_prop = props.get("title") or props.get("Name")
            if title_prop and title_prop.get("title"):
                title = title_prop["title"][0].get("plain_text", "Untitled")
        elif obj_type == "database":
            if item.get("title") and len(item["title"]) > 0:
                title = item["title"][0].get("plain_text", "Untitled")

        formatted.append({
            "id": item.get("id"),
            "type": obj_type,
            "title": title,
            "url": item.get("url"),
            "archived": item.get("archived", False)
        })

    click.echo(json.dumps({"success": True, "count": len(formatted), "results": formatted}, indent=2))


# ============================================================================
# ADD commands
# ============================================================================

@cli.group()
def add():
    """Add entities (page, database, todo, block)."""
    pass


@add.command()
@click.option('--title', required=True, help='Page title')
@click.option('--parent', help='Parent page or database (name or path)')
@click.option('--parent-type', type=click.Choice(['page', 'database']), default='page', help='Parent type')
@click.option('--icon', help='Page icon (emoji or URL)')
@click.option('--cover', help='Cover image URL')
@click.option('--content', help='Initial text content (creates paragraph block)')
@click.option('--properties', help='Page properties as JSON (for database parents)')
@click.option('--after', help='Block ID or page name to position after')
@click.option('--position', type=click.Choice(['start', 'end']), help='Position (start or end)')
@click.option('--api-key', envvar='NOTION_API_KEY', help='Notion API key')
def page(
    title: str,
    parent: Optional[str],
    parent_type: str,
    icon: Optional[str],
    cover: Optional[str],
    content: Optional[str],
    properties: Optional[str],
    after: Optional[str],
    position: Optional[str],
    api_key: str
):
    """
    Add a new page with optional icon, cover, and content.

    Examples:
        notion.py add page --title "Meeting Notes" --parent "Work/Projects"
        notion.py add page --title "New Task" --parent "Tasks" --parent-type database
        notion.py add page --title "Page" --parent "Notes" --icon "📝" --cover "https://example.com/cover.jpg"
        notion.py add page --title "Page" --parent "Notes" --content "Initial content"
    """
    if not api_key:
        click.echo("❌ Error: NOTION_API_KEY required", err=True)
        sys.exit(1)

    if not parent:
        parent = os.getenv("NOTION_PARENT_PAGE_ID")
        if not parent:
            click.echo("❌ Error: --parent required or set NOTION_PARENT_PAGE_ID", err=True)
            sys.exit(1)

    cache = NotionCache()
    parent_id = resolve_id(cache, parent, parent_type, api_key)

    # Resolve 'after' block ID if provided
    after_block_id = None
    if after:
        if is_uuid(after):
            after_block_id = after
        else:
            # Try to find block by searching for heading/text
            async def find_block():
                headers = get_auth_headers(api_key)
                async with httpx.AsyncClient(base_url="https://api.notion.com/v1", headers=headers, timeout=30.0) as client:
                    response = await client.get(f"/blocks/{parent_id}/children")
                    response.raise_for_status()
                    result = response.json()

                    for block in result.get("results", []):
                        block_type = block["type"]
                        if block_type in ["heading_1", "heading_2", "heading_3", "paragraph"]:
                            rich_text = block[block_type].get("rich_text", [])
                            text = rich_text[0].get("plain_text", "") if rich_text else ""
                            if after.lower() in text.lower():
                                return block["id"]
                    return None

            after_block_id = asyncio.run(find_block())
            if not after_block_id:
                click.echo(f"❌ Error: Could not find block matching '{after}'", err=True)
                sys.exit(1)

    async def _create():
        headers = get_auth_headers(api_key)
        headers["Notion-Version"] = "2025-09-03"  # Use latest API version

        async with httpx.AsyncClient(
            base_url="https://api.notion.com/v1",
            headers=headers,
            timeout=30.0
        ) as client:
            body = {
                "parent": {
                    "type": "database_id" if parent_type == "database" else "page_id",
                    "database_id" if parent_type == "database" else "page_id": parent_id
                },
                "properties": {
                    "title": {
                        "title": [{"type": "text", "text": {"content": title}}]
                    }
                }
            }

            # Add custom properties if provided
            if properties:
                try:
                    custom_props = json.loads(properties)
                    body["properties"].update(custom_props)
                except json.JSONDecodeError:
                    click.echo("❌ Error: Invalid JSON in --properties", err=True)
                    sys.exit(1)

            # Add icon
            if icon:
                if icon.startswith("http"):
                    body["icon"] = {"type": "external", "external": {"url": icon}}
                else:
                    body["icon"] = {"type": "emoji", "emoji": icon}

            # Add cover
            if cover:
                body["cover"] = {"type": "external", "external": {"url": cover}}

            # Add initial content
            if content:
                body["children"] = [create_block("paragraph", content)]

            # Add position parameter if specified
            if after_block_id:
                body["position"] = {
                    "type": "after_block",
                    "after_block": {"id": after_block_id}
                }
            elif position:
                body["position"] = {"type": f"page_{position}"}

            response = await client.post("/pages", json=body)
            response.raise_for_status()
            return response.json()

    result = asyncio.run(_create())

    # Update cache
    results = asyncio.run(search_notion(api_key))
    cache = NotionCache()
    cache.update_from_search(results)

    click.echo(json.dumps({"success": True, "page": result}, indent=2))


@add.command()
@click.option('--title', required=True, help='Database title')
@click.option('--parent', help='Parent page (name or path)')
@click.option('--properties', help='Database properties schema as JSON')
@click.option('--template', type=click.Choice(['tasks', 'notes', 'contacts']), help='Use a predefined template')
@click.option('--api-key', envvar='NOTION_API_KEY', help='Notion API key')
def database(title: str, parent: Optional[str], properties: Optional[str], template: Optional[str], api_key: str):
    """
    Create a new database.

    Examples:
        notion.py add database --title "Tasks" --parent "Work" --template tasks
        notion.py add database --title "CRM" --parent "Work" --properties '{"Name": {"title": {}}, "Status": {"select": {"options": [{"name": "Active"}]}}}'
    """
    if not api_key:
        click.echo("❌ Error: NOTION_API_KEY required", err=True)
        sys.exit(1)

    if not parent:
        parent = os.getenv("NOTION_PARENT_PAGE_ID")
        if not parent:
            click.echo("❌ Error: --parent required or set NOTION_PARENT_PAGE_ID", err=True)
            sys.exit(1)

    cache = NotionCache()
    parent_id = resolve_id(cache, parent, "page", api_key)

    # Build properties schema
    if properties:
        try:
            props_schema = json.loads(properties)
        except json.JSONDecodeError:
            click.echo("❌ Error: Invalid JSON in --properties", err=True)
            sys.exit(1)
    elif template == "tasks":
        props_schema = {
            "Task": {"title": {}},
            "Status": {
                "status": {
                    "options": [
                        {"name": "Not Started", "color": "gray"},
                        {"name": "In Progress", "color": "blue"},
                        {"name": "Done", "color": "green"}
                    ]
                }
            },
            "Priority": {
                "select": {
                    "options": [
                        {"name": "Low", "color": "gray"},
                        {"name": "Medium", "color": "yellow"},
                        {"name": "High", "color": "red"}
                    ]
                }
            },
            "Due Date": {"date": {}},
            "Tags": {"multi_select": {}}
        }
    elif template == "notes":
        props_schema = {
            "Name": {"title": {}},
            "Category": {"select": {}},
            "Created": {"created_time": {}},
            "Last Edited": {"last_edited_time": {}}
        }
    elif template == "contacts":
        props_schema = {
            "Name": {"title": {}},
            "Email": {"email": {}},
            "Phone": {"phone_number": {}},
            "Company": {"rich_text": {}},
            "Tags": {"multi_select": {}}
        }
    else:
        props_schema = {
            "Name": {"title": {}}
        }

    async def _create():
        headers = get_auth_headers(api_key)
        async with httpx.AsyncClient(
            base_url="https://api.notion.com/v1",
            headers=headers,
            timeout=30.0
        ) as client:
            body = {
                "parent": {
                    "type": "page_id",
                    "page_id": parent_id
                },
                "title": create_rich_text(title),
                "properties": props_schema
            }

            response = await client.post("/databases", json=body)
            response.raise_for_status()
            return response.json()

    result = asyncio.run(_create())

    # Update cache
    results = asyncio.run(search_notion(api_key))
    cache = NotionCache()
    cache.update_from_search(results)

    click.echo(json.dumps({"success": True, "database": result}, indent=2))


@add.command()
@click.option('--database', help='Database name or ID (or use NOTION_DATABASE_ID env var)')
@click.option('--title', required=True, help='Todo title')
@click.option('--description', help='Todo description')
@click.option('--due-date', help='Due date (ISO format: YYYY-MM-DD)')
@click.option('--priority', type=click.Choice(['Low', 'Medium', 'High']), help='Priority level')
@click.option('--tags', help='Comma-separated tags')
@click.option('--status', help='Status (e.g., Not Started, In Progress, Done)')
@click.option('--api-key', envvar='NOTION_API_KEY', help='Notion API key')
def todo(
    database: Optional[str],
    title: str,
    description: Optional[str],
    due_date: Optional[str],
    priority: Optional[str],
    tags: Optional[str],
    status: Optional[str],
    api_key: str
):
    """
    Add a todo item to a database.

    Examples:
        notion.py add todo --title "Complete project" --database "Tasks"
        notion.py add todo --title "Task" --description "Details" --due-date "2026-12-31" --priority High --tags "work,urgent" --status "In Progress"
    """
    if not api_key:
        click.echo("❌ Error: NOTION_API_KEY required", err=True)
        sys.exit(1)

    if not database:
        database = os.getenv("NOTION_DATABASE_ID")
        if not database:
            click.echo("❌ Error: --database required or set NOTION_DATABASE_ID", err=True)
            sys.exit(1)

    cache = NotionCache()
    database_id = resolve_id(cache, database, "database", api_key)

    # Parse tags
    tag_list = [t.strip() for t in tags.split(",")] if tags else None

    # Create todo properties
    props = create_todo_properties(
        title=title,
        description=description,
        due_date=due_date,
        priority=priority,
        tags=tag_list,
        status=status
    )

    async def _create():
        headers = get_auth_headers(api_key)
        async with httpx.AsyncClient(
            base_url="https://api.notion.com/v1",
            headers=headers,
            timeout=30.0
        ) as client:
            body = {
                "parent": {
                    "type": "database_id",
                    "database_id": database_id
                },
                "properties": props
            }

            response = await client.post("/pages", json=body)
            response.raise_for_status()
            return response.json()

    result = asyncio.run(_create())
    click.echo(json.dumps({"success": True, "todo": result}, indent=2))


@add.command()
@click.option('--parent', required=True, help='Parent page (name or path)')
@click.option('--text', help='Plain text content')
@click.option('--heading', help='Heading text (creates heading_2 block)')
@click.option('--api-key', envvar='NOTION_API_KEY', help='Notion API key')
def block(parent: str, text: Optional[str], heading: Optional[str], api_key: str):
    """
    Add a block to a page (legacy command - use 'blocks add' for more options).

    Examples:
        notion.py add block --parent "Quick Notes" --text "New idea"
        notion.py add block --parent "Work/Meeting Notes" --heading "Action Items"
    """
    if not api_key:
        click.echo("❌ Error: NOTION_API_KEY required", err=True)
        sys.exit(1)

    if not text and not heading:
        click.echo("❌ Error: Either --text or --heading required", err=True)
        sys.exit(1)

    cache = NotionCache()
    parent_id = resolve_id(cache, parent, "page", api_key)

    async def _add_block():
        headers = get_auth_headers(api_key)
        async with httpx.AsyncClient(
            base_url="https://api.notion.com/v1",
            headers=headers,
            timeout=30.0
        ) as client:
            # Build block
            if heading:
                block_obj = create_block("heading_2", heading)
            else:
                block_obj = create_block("paragraph", text)

            response = await client.patch(
                f"/blocks/{parent_id}/children",
                json={"children": [block_obj]}
            )
            response.raise_for_status()
            return response.json()

    result = asyncio.run(_add_block())
    click.echo(json.dumps({"success": True, "result": result}, indent=2))


# ============================================================================
# GET command
# ============================================================================

@cli.command()
@click.argument('entity', type=click.Choice(['page', 'database', 'block']))
@click.argument('identifier')
@click.option('--api-key', envvar='NOTION_API_KEY', help='Notion API key')
def get(entity: str, identifier: str, api_key: str):
    """
    Get a page, database, or block.

    Examples:
        notion.py get page "Meeting Notes"
        notion.py get page "Work/Projects/Q1 Planning"
        notion.py get database "Tasks"
        notion.py get block abc123...
    """
    if not api_key:
        click.echo("❌ Error: NOTION_API_KEY required", err=True)
        sys.exit(1)

    # Resolve ID if needed
    if entity in ["page", "database"]:
        cache = NotionCache()
        item_id = resolve_id(cache, identifier, entity, api_key)
    else:
        item_id = identifier

    async def _get():
        headers = get_auth_headers(api_key)
        async with httpx.AsyncClient(
            base_url="https://api.notion.com/v1",
            headers=headers,
            timeout=30.0
        ) as client:
            if entity == "block":
                endpoint = f"blocks/{item_id}"
            else:
                endpoint = f"{entity}s/{item_id}"

            response = await client.get(endpoint)
            response.raise_for_status()
            return response.json()

    result = asyncio.run(_get())
    click.echo(json.dumps({"success": True, entity: result}, indent=2))


# ============================================================================
# QUERY command
# ============================================================================

@cli.group()
def query():
    """Query databases with filters and sorts."""
    pass


@query.command()
@click.argument('database')
@click.option('--filter', 'filter_json', help='Filter as JSON')
@click.option('--sorts', 'sorts_json', help='Sorts as JSON array')
@click.option('--status', help='Filter by status (shortcut)')
@click.option('--priority', help='Filter by priority (shortcut)')
@click.option('--due-before', help='Filter by due date before (YYYY-MM-DD)')
@click.option('--due-after', help='Filter by due date after (YYYY-MM-DD)')
@click.option('--tags', help='Filter by tag (shortcut)')
@click.option('--page-size', type=int, default=100, help='Results per page')
@click.option('--all', 'fetch_all', is_flag=True, help='Fetch all pages with auto-pagination')
@click.option('--api-key', envvar='NOTION_API_KEY', help='Notion API key')
def database(
    database: str,
    filter_json: Optional[str],
    sorts_json: Optional[str],
    status: Optional[str],
    priority: Optional[str],
    due_before: Optional[str],
    due_after: Optional[str],
    tags: Optional[str],
    page_size: int,
    fetch_all: bool,
    api_key: str
):
    """
    Query a database with filters and sorting.

    Examples:
        notion.py query database "Tasks" --status "In Progress"
        notion.py query database "Tasks" --priority High --due-before "2026-03-01"
        notion.py query database "Tasks" --filter '{"property": "Status", "status": {"equals": "Done"}}'
        notion.py query database "Tasks" --sorts '[{"property": "Priority", "direction": "descending"}]'
        notion.py query database "Tasks" --all
    """
    if not api_key:
        click.echo("❌ Error: NOTION_API_KEY required", err=True)
        sys.exit(1)

    cache = NotionCache()
    database_id = resolve_id(cache, database, "database", api_key)

    # Build filter
    filter_obj = None
    if filter_json:
        try:
            filter_obj = json.loads(filter_json)
        except json.JSONDecodeError:
            click.echo("❌ Error: Invalid JSON in --filter", err=True)
            sys.exit(1)
    elif any([status, priority, due_before, due_after, tags]):
        filter_obj = build_todo_filter(
            status=status,
            priority=priority,
            due_before=due_before,
            due_after=due_after,
            tags=tags
        )

    # Build sorts
    sorts = None
    if sorts_json:
        try:
            sorts = json.loads(sorts_json)
        except json.JSONDecodeError:
            click.echo("❌ Error: Invalid JSON in --sorts", err=True)
            sys.exit(1)

    async def _query():
        headers = get_auth_headers(api_key)
        async with httpx.AsyncClient(
            base_url="https://api.notion.com/v1",
            headers=headers,
            timeout=30.0
        ) as client:
            all_results = []
            start_cursor = None
            has_more = True

            while has_more:
                body = {"page_size": page_size}

                if filter_obj:
                    body["filter"] = filter_obj
                if sorts:
                    body["sorts"] = sorts
                if start_cursor:
                    body["start_cursor"] = start_cursor

                response = await client.post(
                    f"/databases/{database_id}/query",
                    json=body
                )
                response.raise_for_status()
                data = response.json()

                all_results.extend(data.get("results", []))

                if fetch_all:
                    has_more = data.get("has_more", False)
                    start_cursor = data.get("next_cursor")
                else:
                    has_more = False

            return {
                "success": True,
                "count": len(all_results),
                "results": all_results
            }

    result = asyncio.run(_query())
    click.echo(json.dumps(result, indent=2))


# ============================================================================
# TODOS command (search todos)
# ============================================================================

@cli.group()
def todos():
    """Todo management commands."""
    pass


@todos.command()
@click.option('--database', help='Database name or ID')
@click.option('--status', help='Filter by status')
@click.option('--priority', help='Filter by priority')
@click.option('--due-before', help='Due before date (YYYY-MM-DD)')
@click.option('--due-after', help='Due after date (YYYY-MM-DD)')
@click.option('--tags', help='Filter by tag')
@click.option('--limit', type=int, default=20, help='Max results')
@click.option('--api-key', envvar='NOTION_API_KEY', help='Notion API key')
def search(
    database: Optional[str],
    status: Optional[str],
    priority: Optional[str],
    due_before: Optional[str],
    due_after: Optional[str],
    tags: Optional[str],
    limit: int,
    api_key: str
):
    """
    Search todos with filters.

    Examples:
        notion.py todos search --database "Tasks" --status "In Progress"
        notion.py todos search --priority High --due-before "2026-03-01"
        notion.py todos search --tags urgent
    """
    if not api_key:
        click.echo("❌ Error: NOTION_API_KEY required", err=True)
        sys.exit(1)

    if not database:
        database = os.getenv("NOTION_DATABASE_ID")
        if not database:
            click.echo("❌ Error: --database required or set NOTION_DATABASE_ID", err=True)
            sys.exit(1)

    cache = NotionCache()
    database_id = resolve_id(cache, database, "database", api_key)

    # Build filter
    filter_obj = build_todo_filter(
        status=status,
        priority=priority,
        due_before=due_before,
        due_after=due_after,
        tags=tags
    )

    async def _search():
        headers = get_auth_headers(api_key)
        async with httpx.AsyncClient(
            base_url="https://api.notion.com/v1",
            headers=headers,
            timeout=30.0
        ) as client:
            body = {"page_size": limit}
            if filter_obj:
                body["filter"] = filter_obj

            response = await client.post(
                f"/databases/{database_id}/query",
                json=body
            )
            response.raise_for_status()
            data = response.json()

            return {
                "success": True,
                "count": len(data.get("results", [])),
                "todos": data.get("results", [])
            }

    result = asyncio.run(_search())
    click.echo(json.dumps(result, indent=2))


# ============================================================================
# BLOCKS commands
# ============================================================================

@cli.group()
def blocks():
    """Manage blocks (content)."""
    pass


@blocks.command()
@click.argument('parent')
@click.option('--type', 'block_type', required=True,
              type=click.Choice([
                  'paragraph', 'heading_1', 'heading_2', 'heading_3',
                  'bulleted_list_item', 'numbered_list_item', 'to_do', 'toggle',
                  'quote', 'code', 'callout', 'divider', 'table_of_contents',
                  'breadcrumb', 'equation', 'image', 'video', 'file', 'pdf',
                  'audio', 'bookmark', 'embed', 'link_preview', 'link_to_page',
                  'child_page', 'child_database'
              ]),
              help='Block type')
@click.option('--text', help='Text content')
@click.option('--url', help='URL (for media/bookmark/embed blocks)')
@click.option('--language', help='Language (for code blocks)')
@click.option('--icon', help='Icon emoji (for callout blocks)')
@click.option('--checked', is_flag=True, help='Checked status (for to_do blocks)')
@click.option('--expression', help='Math expression (for equation blocks)')
@click.option('--page-id', help='Page ID (for link_to_page blocks)')
@click.option('--title', help='Title (for child_page/child_database blocks)')
@click.option('--after', help='Block ID to position after')
@click.option('--api-key', envvar='NOTION_API_KEY', help='Notion API key')
def add(
    parent: str,
    block_type: str,
    text: Optional[str],
    url: Optional[str],
    language: Optional[str],
    icon: Optional[str],
    checked: bool,
    expression: Optional[str],
    page_id: Optional[str],
    title: Optional[str],
    after: Optional[str],
    api_key: str
):
    """
    Add a block of any type to a page.

    Examples:
        notion.py blocks add "Notes" --type paragraph --text "Hello world"
        notion.py blocks add "Notes" --type heading_2 --text "Section Title"
        notion.py blocks add "Notes" --type bulleted_list_item --text "Item 1"
        notion.py blocks add "Notes" --type to_do --text "Task" --checked
        notion.py blocks add "Notes" --type code --text "print('hello')" --language python
        notion.py blocks add "Notes" --type callout --text "Important note" --icon "💡"
        notion.py blocks add "Notes" --type divider
        notion.py blocks add "Notes" --type image --url "https://example.com/image.jpg"
        notion.py blocks add "Notes" --type equation --expression "E=mc^2"
    """
    if not api_key:
        click.echo("❌ Error: NOTION_API_KEY required", err=True)
        sys.exit(1)

    cache = NotionCache()
    parent_id = resolve_id(cache, parent, "page", api_key)

    # Build block based on type
    try:
        if block_type == "code":
            block_obj = create_block(block_type, text, language=language or "plain text")
        elif block_type == "callout":
            block_obj = create_block(block_type, text, icon=icon or "💡")
        elif block_type == "to_do":
            block_obj = create_block(block_type, text, checked=checked)
        elif block_type == "equation":
            block_obj = create_block(block_type, expression=expression or text)
        elif block_type in ["image", "video", "file", "pdf", "audio", "bookmark", "embed", "link_preview"]:
            block_obj = create_block(block_type, url=url)
        elif block_type == "link_to_page":
            block_obj = create_block(block_type, page_id=page_id)
        elif block_type in ["child_page", "child_database"]:
            block_obj = create_block(block_type, title=title or text)
        else:
            block_obj = create_block(block_type, text)
    except ValueError as e:
        click.echo(f"❌ Error: {e}", err=True)
        sys.exit(1)

    async def _add():
        headers = get_auth_headers(api_key)
        async with httpx.AsyncClient(
            base_url="https://api.notion.com/v1",
            headers=headers,
            timeout=30.0
        ) as client:
            body = {"children": [block_obj]}
            if after:
                body["after"] = after

            response = await client.patch(
                f"/blocks/{parent_id}/children",
                json=body
            )
            response.raise_for_status()
            return response.json()

    result = asyncio.run(_add())
    click.echo(json.dumps({"success": True, "result": result}, indent=2))


@blocks.command()
@click.argument('parent')
@click.option('--api-key', envvar='NOTION_API_KEY', help='Notion API key')
def list(parent: str, api_key: str):
    """
    List all blocks in a page.

    Examples:
        notion.py blocks list "Quick Note"
        notion.py blocks list "Work/Projects"
    """
    if not api_key:
        click.echo("❌ Error: NOTION_API_KEY required", err=True)
        sys.exit(1)

    cache = NotionCache()
    parent_id = resolve_id(cache, parent, "page", api_key)

    async def _list_blocks():
        headers = get_auth_headers(api_key)
        async with httpx.AsyncClient(
            base_url="https://api.notion.com/v1",
            headers=headers,
            timeout=30.0
        ) as client:
            response = await client.get(f"/blocks/{parent_id}/children")
            response.raise_for_status()
            result = response.json()

            # Format blocks for readability
            formatted_blocks = []
            for block in result.get("results", []):
                block_type = block["type"]
                block_info = {
                    "id": block["id"],
                    "type": block_type,
                }

                # Extract text content based on type
                if block_type in ["paragraph", "heading_1", "heading_2", "heading_3", "quote", "callout", "toggle"]:
                    rich_text = block[block_type].get("rich_text", [])
                    text = rich_text[0].get("plain_text", "") if rich_text else ""
                    block_info["text"] = text
                elif block_type == "child_page":
                    block_info["title"] = block["child_page"]["title"]
                elif block_type == "to_do":
                    rich_text = block["to_do"].get("rich_text", [])
                    text = rich_text[0].get("plain_text", "") if rich_text else ""
                    block_info["text"] = text
                    block_info["checked"] = block["to_do"].get("checked", False)
                elif block_type in ["bulleted_list_item", "numbered_list_item"]:
                    rich_text = block[block_type].get("rich_text", [])
                    text = rich_text[0].get("plain_text", "") if rich_text else ""
                    block_info["text"] = text
                elif block_type == "code":
                    rich_text = block["code"].get("rich_text", [])
                    text = rich_text[0].get("plain_text", "") if rich_text else ""
                    block_info["text"] = text
                    block_info["language"] = block["code"].get("language", "plain text")

                formatted_blocks.append(block_info)

            return {"success": True, "count": len(formatted_blocks), "blocks": formatted_blocks}

    result = asyncio.run(_list_blocks())
    click.echo(json.dumps(result, indent=2))


@blocks.command()
@click.argument('block_id')
@click.option('--api-key', envvar='NOTION_API_KEY', help='Notion API key')
def delete(block_id: str, api_key: str):
    """
    Delete a block.

    Examples:
        notion.py blocks delete abc123...
    """
    if not api_key:
        click.echo("❌ Error: NOTION_API_KEY required", err=True)
        sys.exit(1)

    async def _delete():
        headers = get_auth_headers(api_key)
        async with httpx.AsyncClient(
            base_url="https://api.notion.com/v1",
            headers=headers,
            timeout=30.0
        ) as client:
            response = await client.delete(f"/blocks/{block_id}")
            response.raise_for_status()
            return {"success": True, "deleted": block_id}

    result = asyncio.run(_delete())
    click.echo(json.dumps(result, indent=2))


# ============================================================================
# BLOCKS SUBTASKS commands
# ============================================================================

@blocks.group()
def subtasks():
    """Manage todo subtasks."""
    pass


@subtasks.command()
@click.argument('todo_block_id')
@click.option('--text', required=True, help='Subtask text')
@click.option('--checked', is_flag=True, help='Mark as completed')
@click.option('--api-key', envvar='NOTION_API_KEY', help='Notion API key')
def add(todo_block_id: str, text: str, checked: bool, api_key: str):
    """
    Add a subtask to a todo block.

    Examples:
        notion.py blocks subtasks add abc123... --text "Subtask 1"
        notion.py blocks subtasks add abc123... --text "Completed subtask" --checked
    """
    if not api_key:
        click.echo("❌ Error: NOTION_API_KEY required", err=True)
        sys.exit(1)

    async def _add():
        headers = get_auth_headers(api_key)
        async with httpx.AsyncClient(
            base_url="https://api.notion.com/v1",
            headers=headers,
            timeout=30.0
        ) as client:
            subtask_block = create_block("to_do", text, checked=checked)

            response = await client.patch(
                f"/blocks/{todo_block_id}/children",
                json={"children": [subtask_block]}
            )
            response.raise_for_status()
            return response.json()

    result = asyncio.run(_add())
    click.echo(json.dumps({"success": True, "result": result}, indent=2))


@subtasks.command()
@click.argument('todo_block_id')
@click.option('--api-key', envvar='NOTION_API_KEY', help='Notion API key')
def list(todo_block_id: str, api_key: str):
    """
    List subtasks of a todo block.

    Examples:
        notion.py blocks subtasks list abc123...
    """
    if not api_key:
        click.echo("❌ Error: NOTION_API_KEY required", err=True)
        sys.exit(1)

    async def _list():
        headers = get_auth_headers(api_key)
        async with httpx.AsyncClient(
            base_url="https://api.notion.com/v1",
            headers=headers,
            timeout=30.0
        ) as client:
            response = await client.get(f"/blocks/{todo_block_id}/children")
            response.raise_for_status()
            result = response.json()

            # Filter for to_do blocks
            subtasks = []
            for block in result.get("results", []):
                if block["type"] == "to_do":
                    rich_text = block["to_do"].get("rich_text", [])
                    text = rich_text[0].get("plain_text", "") if rich_text else ""
                    subtasks.append({
                        "id": block["id"],
                        "text": text,
                        "checked": block["to_do"].get("checked", False)
                    })

            return {"success": True, "count": len(subtasks), "subtasks": subtasks}

    result = asyncio.run(_list())
    click.echo(json.dumps(result, indent=2))


@subtasks.command()
@click.argument('subtask_block_id')
@click.option('--api-key', envvar='NOTION_API_KEY', help='Notion API key')
def check(subtask_block_id: str, api_key: str):
    """
    Mark a subtask as completed.

    Examples:
        notion.py blocks subtasks check abc123...
    """
    if not api_key:
        click.echo("❌ Error: NOTION_API_KEY required", err=True)
        sys.exit(1)

    async def _check():
        headers = get_auth_headers(api_key)
        async with httpx.AsyncClient(
            base_url="https://api.notion.com/v1",
            headers=headers,
            timeout=30.0
        ) as client:
            response = await client.patch(
                f"/blocks/{subtask_block_id}",
                json={"to_do": {"checked": True}}
            )
            response.raise_for_status()
            return response.json()

    result = asyncio.run(_check())
    click.echo(json.dumps({"success": True, "result": result}, indent=2))


@subtasks.command()
@click.argument('subtask_block_id')
@click.option('--api-key', envvar='NOTION_API_KEY', help='Notion API key')
def uncheck(subtask_block_id: str, api_key: str):
    """
    Mark a subtask as incomplete.

    Examples:
        notion.py blocks subtasks uncheck abc123...
    """
    if not api_key:
        click.echo("❌ Error: NOTION_API_KEY required", err=True)
        sys.exit(1)

    async def _uncheck():
        headers = get_auth_headers(api_key)
        async with httpx.AsyncClient(
            base_url="https://api.notion.com/v1",
            headers=headers,
            timeout=30.0
        ) as client:
            response = await client.patch(
                f"/blocks/{subtask_block_id}",
                json={"to_do": {"checked": False}}
            )
            response.raise_for_status()
            return response.json()

    result = asyncio.run(_uncheck())
    click.echo(json.dumps({"success": True, "result": result}, indent=2))


# ============================================================================
# UPDATE command
# ============================================================================

@cli.command()
@click.argument('entity', type=click.Choice(['page', 'database', 'block']))
@click.argument('identifier')
@click.option('--title', help='New title')
@click.option('--properties', help='Updated properties as JSON (for databases)')
@click.option('--text', help='New text content (for blocks)')
@click.option('--archive', is_flag=True, help='Archive the entity')
@click.option('--restore', is_flag=True, help='Restore an archived entity')
@click.option('--api-key', envvar='NOTION_API_KEY', help='Notion API key')
def update(
    entity: str,
    identifier: str,
    title: Optional[str],
    properties: Optional[str],
    text: Optional[str],
    archive: bool,
    restore: bool,
    api_key: str
):
    """
    Update a page, database, or block.

    Examples:
        notion.py update page "Meeting Notes" --title "Project Meeting"
        notion.py update page "Old Page" --archive
        notion.py update page "Old Page" --restore
        notion.py update database "Tasks" --title "My Tasks"
        notion.py update block abc123... --text "Updated content"
    """
    if not api_key:
        click.echo("❌ Error: NOTION_API_KEY required", err=True)
        sys.exit(1)

    if archive and restore:
        click.echo("❌ Error: Cannot both archive and restore", err=True)
        sys.exit(1)

    # Resolve ID if needed
    if entity in ["page", "database"]:
        cache = NotionCache()
        item_id = resolve_id(cache, identifier, entity, api_key)
    else:
        item_id = identifier

    async def _update():
        headers = get_auth_headers(api_key)
        async with httpx.AsyncClient(
            base_url="https://api.notion.com/v1",
            headers=headers,
            timeout=30.0
        ) as client:
            body = {}

            if entity == "page":
                if title:
                    body["properties"] = {
                        "title": {
                            "title": create_rich_text(title)
                        }
                    }
                if archive:
                    body["archived"] = True
                elif restore:
                    body["archived"] = False

                endpoint = f"/pages/{item_id}"

            elif entity == "database":
                if title:
                    body["title"] = create_rich_text(title)
                if properties:
                    try:
                        body["properties"] = json.loads(properties)
                    except json.JSONDecodeError:
                        click.echo("❌ Error: Invalid JSON in --properties", err=True)
                        sys.exit(1)
                if archive:
                    body["archived"] = True
                elif restore:
                    body["archived"] = False

                endpoint = f"/databases/{item_id}"

            else:  # block
                if text:
                    # Get current block to determine type
                    get_response = await client.get(f"/blocks/{item_id}")
                    get_response.raise_for_status()
                    block_data = get_response.json()
                    block_type = block_data["type"]

                    # Update based on block type
                    if block_type in ["paragraph", "heading_1", "heading_2", "heading_3", "quote", "callout", "toggle"]:
                        body[block_type] = {"rich_text": create_rich_text(text)}
                    elif block_type in ["bulleted_list_item", "numbered_list_item"]:
                        body[block_type] = {"rich_text": create_rich_text(text)}
                    elif block_type == "to_do":
                        body["to_do"] = {"rich_text": create_rich_text(text)}
                    elif block_type == "code":
                        current_lang = block_data["code"].get("language", "plain text")
                        body["code"] = {
                            "rich_text": create_rich_text(text),
                            "language": current_lang
                        }
                    else:
                        click.echo(f"❌ Error: Cannot update text for block type: {block_type}", err=True)
                        sys.exit(1)

                endpoint = f"/blocks/{item_id}"

            if not body:
                click.echo("❌ Error: No updates specified", err=True)
                sys.exit(1)

            response = await client.patch(endpoint, json=body)
            response.raise_for_status()
            return response.json()

    result = asyncio.run(_update())

    # Refresh cache if page or database
    if entity in ["page", "database"]:
        results = asyncio.run(search_notion(api_key))
        cache = NotionCache()
        cache.update_from_search(results)

    click.echo(json.dumps({"success": True, entity: result}, indent=2))


# ============================================================================
# DELETE command
# ============================================================================

@cli.command()
@click.argument('entity', type=click.Choice(['page', 'block']))
@click.argument('identifier')
@click.option('--api-key', envvar='NOTION_API_KEY', help='Notion API key')
def delete(entity: str, identifier: str, api_key: str):
    """
    Delete a page or block.

    Examples:
        notion.py delete page "Old Notes"
        notion.py delete block abc123...
    """
    if not api_key:
        click.echo("❌ Error: NOTION_API_KEY required", err=True)
        sys.exit(1)

    if entity == "page":
        cache = NotionCache()
        item_id = resolve_id(cache, identifier, "page", api_key)
    else:
        item_id = identifier

    async def _delete():
        headers = get_auth_headers(api_key)
        async with httpx.AsyncClient(
            base_url="https://api.notion.com/v1",
            headers=headers,
            timeout=30.0
        ) as client:
            if entity == "page":
                # Archive page (Notion doesn't allow permanent deletion via API)
                response = await client.patch(
                    f"/pages/{item_id}",
                    json={"archived": True}
                )
            else:
                response = await client.delete(f"/blocks/{item_id}")

            response.raise_for_status()
            return {"success": True, "deleted": item_id, "type": entity}

    result = asyncio.run(_delete())

    # Refresh cache if page
    if entity == "page":
        results = asyncio.run(search_notion(api_key))
        cache = NotionCache()
        cache.update_from_search(results)

    click.echo(json.dumps(result, indent=2))


# ============================================================================
# MOVE command
# ============================================================================

@cli.group()
def move():
    """Move pages to new parents."""
    pass


@move.command()
@click.argument('page')
@click.option('--to', 'new_parent', required=True, help='New parent page (name or path)')
@click.option('--api-key', envvar='NOTION_API_KEY', help='Notion API key')
def page(page: str, new_parent: str, api_key: str):
    """
    Move a page to a new parent.

    Examples:
        notion.py move page "Old Note" --to "Archive"
        notion.py move page "Meeting Notes" --to "Work/2026"
    """
    if not api_key:
        click.echo("❌ Error: NOTION_API_KEY required", err=True)
        sys.exit(1)

    cache = NotionCache()
    page_id = resolve_id(cache, page, "page", api_key)
    new_parent_id = resolve_id(cache, new_parent, "page", api_key)

    async def _move():
        headers = get_auth_headers(api_key)
        async with httpx.AsyncClient(
            base_url="https://api.notion.com/v1",
            headers=headers,
            timeout=30.0
        ) as client:
            # Use update page with new parent
            response = await client.patch(
                f"/pages/{page_id}",
                json={
                    "parent": {
                        "type": "page_id",
                        "page_id": new_parent_id
                    }
                }
            )
            response.raise_for_status()
            return response.json()

    result = asyncio.run(_move())

    # Refresh cache
    results = asyncio.run(search_notion(api_key))
    cache = NotionCache()
    cache.update_from_search(results)

    click.echo(json.dumps({"success": True, "page": result}, indent=2))


# ============================================================================
# REFRESH-CACHE command
# ============================================================================

@cli.command()
@click.option('--api-key', envvar='NOTION_API_KEY', help='Notion API key')
def refresh_cache(api_key: str):
    """
    Refresh the local cache of pages and databases.

    Example:
        notion.py refresh-cache
    """
    if not api_key:
        click.echo("❌ Error: NOTION_API_KEY required", err=True)
        sys.exit(1)

    click.echo("🔄 Refreshing cache from Notion API...", err=True)

    results = asyncio.run(search_notion(api_key))
    cache = NotionCache()
    cache.update_from_search(results)

    pages_count = len(cache.data.get("pages", {}))
    databases_count = len(cache.data.get("databases", {}))

    click.echo(json.dumps({
        "success": True,
        "cached_pages": pages_count,
        "cached_databases": databases_count,
        "cache_file": str(CACHE_FILE)
    }, indent=2))


# ============================================================================
# DIAGNOSTIC commands
# ============================================================================

@cli.command()
@click.option('--api-key', envvar='NOTION_API_KEY', help='Notion API key')
def verify_connection(api_key: str):
    """
    Verify Notion API connection and authentication.

    Tests the connection by fetching the current user's information.

    Example:
        notion.py verify-connection
    """
    if not api_key:
        click.echo("❌ Error: NOTION_API_KEY required", err=True)
        sys.exit(1)

    async def _verify():
        try:
            headers = get_auth_headers(api_key)
            async with httpx.AsyncClient(
                base_url="https://api.notion.com/v1/",
                headers=headers,
                timeout=30.0
            ) as client:
                response = await client.get("users/me")
                response.raise_for_status()
                user_info = response.json()

                return {
                    "success": True,
                    "message": "✅ Successfully connected to Notion API",
                    "user": {
                        "id": user_info.get("id"),
                        "name": user_info.get("name"),
                        "type": user_info.get("type"),
                        "bot": user_info.get("bot", {})
                    }
                }
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 401:
                return {
                    "success": False,
                    "error": "Authentication failed - invalid API key"
                }
            return {
                "success": False,
                "error": f"HTTP {e.response.status_code}: {e.response.text}"
            }
        except httpx.RequestError as e:
            return {
                "success": False,
                "error": f"Connection error: {str(e)}"
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"Unexpected error: {str(e)}"
            }

    result = asyncio.run(_verify())
    click.echo(json.dumps(result, indent=2))
    sys.exit(0 if result.get("success") else 1)


@cli.command()
def check_config():
    """
    Check current environment configuration.

    Displays which environment variables are set and their values (masked for API key).

    Example:
        notion.py check-config
    """
    config = {
        "NOTION_API_KEY": os.getenv("NOTION_API_KEY"),
        "NOTION_DATABASE_ID": os.getenv("NOTION_DATABASE_ID"),
        "NOTION_PARENT_PAGE_ID": os.getenv("NOTION_PARENT_PAGE_ID"),
    }

    result = {
        "configuration": {}
    }

    for key, value in config.items():
        if value:
            # Mask API key for security
            if key == "NOTION_API_KEY":
                masked_value = value[:10] + "..." if len(value) > 10 else "***"
                result["configuration"][key] = {
                    "set": True,
                    "value": masked_value,
                    "length": len(value)
                }
            else:
                result["configuration"][key] = {
                    "set": True,
                    "value": value
                }
        else:
            result["configuration"][key] = {
                "set": False,
                "value": None
            }

    # Check .env file existence
    env_file = project_root / ".env"
    result["env_file"] = {
        "path": str(env_file),
        "exists": env_file.exists()
    }

    click.echo(json.dumps(result, indent=2))


if __name__ == "__main__":
    cli()
