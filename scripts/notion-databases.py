#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "httpx",
#     "click",
#     "python-dotenv",
#     "structlog",
#     "pydantic",
# ]
# ///
"""
Notion Databases API - Database and todo operations.

Usage:
    # Create a new database
    uv run scripts/notion-databases.py create --parent-page-id <id> --title "My DB" \\
        --properties '{"Name": {"title": {}}, "Status": {"select": {}}}'

    # Query a database
    uv run scripts/notion-databases.py query --database-id <id>

    # Query with filters
    uv run scripts/notion-databases.py query --database-id <id> \\
        --filter '{"property": "Status", "select": {"equals": "Done"}}'

    # Add a todo item
    uv run scripts/notion-databases.py add-todo --database-id <id> \\
        --title "My task" --description "Details" --priority "High"

    # Search todos
    uv run scripts/notion-databases.py search-todos --database-id <id> \\
        --status "In Progress"

    # Get database info
    uv run scripts/notion-databases.py info --database-id <id>

Environment Variables:
    NOTION_API_KEY        - Required: Notion integration token
    NOTION_DATABASE_ID    - Optional: Default database ID
    NOTION_PARENT_PAGE_ID - Optional: Default parent page ID for new databases
"""

import sys
import os
import json
import asyncio
from pathlib import Path
from datetime import datetime

# Add src to Python path for local imports
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

import click
import httpx
from dotenv import load_dotenv

from notion_api_mcp.api.databases import DatabasesAPI
from notion_api_mcp.api.pages import PagesAPI
from notion_api_mcp.utils.auth import get_auth_headers

# Load .env file if it exists
env_path = project_root / ".env"
if env_path.exists():
    load_dotenv(env_path)


@click.group()
def databases():
    """Manage Notion databases and todos."""
    pass


@databases.command()
@click.option('--api-key', envvar='NOTION_API_KEY', help='Notion API key')
@click.option('--parent-page-id', envvar='NOTION_PARENT_PAGE_ID', help='Parent page ID')
@click.option('--title', required=True, help='Database title')
@click.option('--properties', required=True, help='Database properties schema as JSON')
def create(api_key: str | None, parent_page_id: str | None, title: str, properties: str):
    """
    Create a new Notion database.

    Example:
        uv run scripts/notion-databases.py create --parent-page-id xyz \\
            --title "Tasks" \\
            --properties '{"Name": {"title": {}}, "Status": {"select": {"options": [{"name": "Todo"}, {"name": "Done"}]}}}'
    """
    if not api_key:
        click.echo("❌ Error: --api-key required or set NOTION_API_KEY", err=True)
        sys.exit(1)

    if not parent_page_id:
        click.echo("❌ Error: --parent-page-id required or set NOTION_PARENT_PAGE_ID", err=True)
        sys.exit(1)

    async def _create():
        try:
            # Parse properties JSON
            try:
                props = json.loads(properties)
            except json.JSONDecodeError as e:
                return {
                    "success": False,
                    "error": f"Invalid JSON in --properties: {e}"
                }

            headers = get_auth_headers(api_key)
            async with httpx.AsyncClient(
                base_url="https://api.notion.com/v1/",
                headers=headers,
                timeout=30.0
            ) as client:
                api = DatabasesAPI(client)
                result = await api.create_database(parent_page_id, title, props)

                return {
                    "success": True,
                    "database": {
                        "id": result.get("id"),
                        "url": result.get("url"),
                        "title": title,
                        "created_time": result.get("created_time")
                    }
                }

        except httpx.HTTPStatusError as e:
            return {
                "success": False,
                "error": f"HTTP {e.response.status_code}: {e.response.text}"
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"Error: {str(e)}"
            }

    result = asyncio.run(_create())
    click.echo(json.dumps(result, indent=2))
    sys.exit(0 if result.get("success") else 1)


@databases.command()
@click.option('--api-key', envvar='NOTION_API_KEY', help='Notion API key')
@click.option('--database-id', envvar='NOTION_DATABASE_ID', help='Database ID')
@click.option('--filter', help='Filter conditions as JSON')
@click.option('--sort', help='Sort configuration as JSON array')
@click.option('--page-size', type=int, default=100, help='Page size (default: 100)')
def query(api_key: str | None, database_id: str | None, filter: str | None,
          sort: str | None, page_size: int):
    """
    Query a Notion database.

    Examples:
        # Query all items
        uv run scripts/notion-databases.py query --database-id abc123

        # Query with filter
        uv run scripts/notion-databases.py query --database-id abc123 \\
            --filter '{"property": "Status", "select": {"equals": "Done"}}'

        # Query with sort
        uv run scripts/notion-databases.py query --database-id abc123 \\
            --sort '[{"property": "Created", "direction": "descending"}]'
    """
    if not api_key:
        click.echo("❌ Error: --api-key required or set NOTION_API_KEY", err=True)
        sys.exit(1)

    if not database_id:
        click.echo("❌ Error: --database-id required or set NOTION_DATABASE_ID", err=True)
        sys.exit(1)

    async def _query():
        try:
            # Parse filter if provided
            filter_conditions = None
            if filter:
                try:
                    filter_conditions = json.loads(filter)
                except json.JSONDecodeError as e:
                    return {
                        "success": False,
                        "error": f"Invalid JSON in --filter: {e}"
                    }

            # Parse sort if provided
            sorts = None
            if sort:
                try:
                    sorts = json.loads(sort)
                except json.JSONDecodeError as e:
                    return {
                        "success": False,
                        "error": f"Invalid JSON in --sort: {e}"
                    }

            headers = get_auth_headers(api_key)
            async with httpx.AsyncClient(
                base_url="https://api.notion.com/v1/",
                headers=headers,
                timeout=30.0
            ) as client:
                api = DatabasesAPI(client)
                result = await api.query_database(
                    database_id=database_id,
                    filter_conditions=filter_conditions,
                    sorts=sorts,
                    page_size=page_size
                )

                return {
                    "success": True,
                    "results": result.get("results", []),
                    "has_more": result.get("has_more", False),
                    "next_cursor": result.get("next_cursor")
                }

        except httpx.HTTPStatusError as e:
            return {
                "success": False,
                "error": f"HTTP {e.response.status_code}: {e.response.text}"
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"Error: {str(e)}"
            }

    result = asyncio.run(_query())
    click.echo(json.dumps(result, indent=2))
    sys.exit(0 if result.get("success") else 1)


@databases.command()
@click.option('--api-key', envvar='NOTION_API_KEY', help='Notion API key')
@click.option('--database-id', envvar='NOTION_DATABASE_ID', help='Database ID')
@click.option('--title', required=True, help='Todo title/task name')
@click.option('--description', help='Todo description')
@click.option('--due-date', help='Due date (YYYY-MM-DD format)')
@click.option('--priority', type=click.Choice(['Low', 'Medium', 'High']), help='Priority level')
@click.option('--tags', help='Comma-separated tags')
@click.option('--status', default='Not Started', help='Initial status (default: Not Started)')
def add_todo(api_key: str | None, database_id: str | None, title: str,
             description: str | None, due_date: str | None, priority: str | None,
             tags: str | None, status: str):
    """
    Add a todo item to a database.

    Example:
        uv run scripts/notion-databases.py add-todo --database-id abc123 \\
            --title "Complete project" \\
            --description "Finish all tasks" \\
            --due-date "2026-12-31" \\
            --priority "High" \\
            --tags "work,urgent"
    """
    if not api_key:
        click.echo("❌ Error: --api-key required or set NOTION_API_KEY", err=True)
        sys.exit(1)

    if not database_id:
        click.echo("❌ Error: --database-id required or set NOTION_DATABASE_ID", err=True)
        sys.exit(1)

    async def _add_todo():
        try:
            headers = get_auth_headers(api_key)
            async with httpx.AsyncClient(
                base_url="https://api.notion.com/v1/",
                headers=headers,
                timeout=30.0
            ) as client:
                pages_api = PagesAPI(client)

                # Parse tags
                tag_list = []
                if tags:
                    tag_list = [tag.strip() for tag in tags.split(',')]

                # Create todo properties
                properties = pages_api.create_todo_properties(
                    title=title,
                    description=description,
                    due_date=due_date,
                    priority=priority,
                    tags=tag_list,
                    status=status
                )

                # Create the page
                result = await pages_api.create_page(
                    parent_id=database_id,
                    properties=properties,
                    is_database=True
                )

                return {
                    "success": True,
                    "todo": {
                        "id": result.get("id"),
                        "url": result.get("url"),
                        "title": title,
                        "created_time": result.get("created_time")
                    }
                }

        except httpx.HTTPStatusError as e:
            return {
                "success": False,
                "error": f"HTTP {e.response.status_code}: {e.response.text}"
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"Error: {str(e)}"
            }

    result = asyncio.run(_add_todo())
    click.echo(json.dumps(result, indent=2))
    sys.exit(0 if result.get("success") else 1)


@databases.command()
@click.option('--api-key', envvar='NOTION_API_KEY', help='Notion API key')
@click.option('--database-id', envvar='NOTION_DATABASE_ID', help='Database ID')
@click.option('--status', help='Filter by status')
@click.option('--priority', type=click.Choice(['Low', 'Medium', 'High']), help='Filter by priority')
@click.option('--tag', help='Filter by tag')
@click.option('--overdue-only', is_flag=True, help='Show only overdue tasks')
def search_todos(api_key: str | None, database_id: str | None, status: str | None,
                 priority: str | None, tag: str | None, overdue_only: bool):
    """
    Search and filter todos in a database.

    Examples:
        # Search by status
        uv run scripts/notion-databases.py search-todos --database-id abc123 --status "In Progress"

        # Search by priority
        uv run scripts/notion-databases.py search-todos --database-id abc123 --priority "High"

        # Find overdue tasks
        uv run scripts/notion-databases.py search-todos --database-id abc123 --overdue-only
    """
    if not api_key:
        click.echo("❌ Error: --api-key required or set NOTION_API_KEY", err=True)
        sys.exit(1)

    if not database_id:
        click.echo("❌ Error: --database-id required or set NOTION_DATABASE_ID", err=True)
        sys.exit(1)

    async def _search_todos():
        try:
            headers = get_auth_headers(api_key)
            async with httpx.AsyncClient(
                base_url="https://api.notion.com/v1/",
                headers=headers,
                timeout=30.0
            ) as client:
                db_api = DatabasesAPI(client)

                # Build filter
                filters = []

                if status:
                    filters.append({
                        "property": "Status",
                        "select": {"equals": status}
                    })

                if priority:
                    filters.append({
                        "property": "Priority",
                        "select": {"equals": priority}
                    })

                if tag:
                    filters.append({
                        "property": "Tags",
                        "multi_select": {"contains": tag}
                    })

                if overdue_only:
                    filters.append({
                        "property": "Due Date",
                        "date": {"before": datetime.now().isoformat()}
                    })

                # Combine filters with AND
                filter_conditions = None
                if filters:
                    if len(filters) == 1:
                        filter_conditions = filters[0]
                    else:
                        filter_conditions = {
                            "and": filters
                        }

                # Query database
                result = await db_api.query_database(
                    database_id=database_id,
                    filter_conditions=filter_conditions,
                    sorts=[{"property": "Due Date", "direction": "ascending"}]
                )

                return {
                    "success": True,
                    "todos": result.get("results", []),
                    "count": len(result.get("results", [])),
                    "has_more": result.get("has_more", False)
                }

        except httpx.HTTPStatusError as e:
            return {
                "success": False,
                "error": f"HTTP {e.response.status_code}: {e.response.text}"
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"Error: {str(e)}"
            }

    result = asyncio.run(_search_todos())
    click.echo(json.dumps(result, indent=2))
    sys.exit(0 if result.get("success") else 1)


@databases.command()
@click.option('--api-key', envvar='NOTION_API_KEY', help='Notion API key')
@click.option('--database-id', envvar='NOTION_DATABASE_ID', help='Database ID')
def info(api_key: str | None, database_id: str | None):
    """
    Get database information and schema.

    Example:
        uv run scripts/notion-databases.py info --database-id abc123
    """
    if not api_key:
        click.echo("❌ Error: --api-key required or set NOTION_API_KEY", err=True)
        sys.exit(1)

    if not database_id:
        click.echo("❌ Error: --database-id required or set NOTION_DATABASE_ID", err=True)
        sys.exit(1)

    async def _get_info():
        try:
            headers = get_auth_headers(api_key)
            async with httpx.AsyncClient(
                base_url="https://api.notion.com/v1/",
                headers=headers,
                timeout=30.0
            ) as client:
                response = await client.get(f"databases/{database_id}")
                response.raise_for_status()
                db_info = response.json()

                # Extract title
                title = "Untitled"
                if db_info.get("title") and len(db_info["title"]) > 0:
                    title = db_info["title"][0].get("plain_text", "Untitled")

                # Extract property schema
                properties = {}
                for prop_name, prop_data in db_info.get("properties", {}).items():
                    properties[prop_name] = {
                        "type": prop_data.get("type"),
                        "id": prop_data.get("id")
                    }

                return {
                    "success": True,
                    "database": {
                        "id": db_info.get("id"),
                        "title": title,
                        "url": db_info.get("url"),
                        "created_time": db_info.get("created_time"),
                        "last_edited_time": db_info.get("last_edited_time"),
                        "archived": db_info.get("archived", False),
                        "properties": properties
                    }
                }

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                return {
                    "success": False,
                    "error": f"Database not found or integration lacks access: {database_id}"
                }
            return {
                "success": False,
                "error": f"HTTP {e.response.status_code}: {e.response.text}"
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"Error: {str(e)}"
            }

    result = asyncio.run(_get_info())
    click.echo(json.dumps(result, indent=2))
    sys.exit(0 if result.get("success") else 1)


if __name__ == "__main__":
    databases()
