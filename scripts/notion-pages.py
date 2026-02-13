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
Notion Pages API - Page lifecycle operations.

Usage:
    # Create a page in a database
    uv run scripts/notion-pages.py create --parent-id <db-id> --title "My Page" --parent-type database

    # Create a page under another page
    uv run scripts/notion-pages.py create --parent-id <page-id> --title "Child Page" --parent-type page

    # Get page information
    uv run scripts/notion-pages.py get <page-id>

    # Update page properties
    uv run scripts/notion-pages.py update <page-id> --properties '{"Title": {"title": [...]}}'

    # Archive a page
    uv run scripts/notion-pages.py archive <page-id>

    # Restore an archived page
    uv run scripts/notion-pages.py restore <page-id>

    # Get a specific property value
    uv run scripts/notion-pages.py get-property <page-id> <property-id>

Environment Variables:
    NOTION_API_KEY        - Required: Notion integration token
    NOTION_DATABASE_ID    - Optional: Default database ID for parent
    NOTION_PARENT_PAGE_ID - Optional: Default parent page ID
"""

import sys
import os
import json
import asyncio
from pathlib import Path

# Add src to Python path for local imports
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

import click
import httpx
from dotenv import load_dotenv

from notion_api_mcp.api.pages import PagesAPI
from notion_api_mcp.utils.auth import get_auth_headers

# Load .env file if it exists
env_path = project_root / ".env"
if env_path.exists():
    load_dotenv(env_path)


@click.group()
def pages():
    """Manage Notion pages - create, read, update, archive."""
    pass


@pages.command()
@click.option('--api-key', envvar='NOTION_API_KEY', help='Notion API key (or set NOTION_API_KEY)')
@click.option('--parent-id', help='Parent database or page ID (or use --database-id/--page-id)')
@click.option('--database-id', envvar='NOTION_DATABASE_ID', help='Parent database ID (or set NOTION_DATABASE_ID)')
@click.option('--page-id', help='Parent page ID')
@click.option('--parent-type', type=click.Choice(['database', 'page']), default='database', help='Parent type (default: database)')
@click.option('--title', required=True, help='Page title')
@click.option('--properties', help='Additional properties as JSON')
@click.option('--content', help='Initial page content blocks as JSON')
def create(api_key: str | None, parent_id: str | None, database_id: str | None,
           page_id: str | None, parent_type: str, title: str,
           properties: str | None, content: str | None):
    """
    Create a new Notion page.

    Examples:
        # Create page in database with just title
        uv run scripts/notion-pages.py create --database-id abc123 --title "My Page"

        # Create page under another page
        uv run scripts/notion-pages.py create --page-id xyz789 --parent-type page --title "Child"

        # Create with custom properties
        uv run scripts/notion-pages.py create --database-id abc123 --title "Task" \\
            --properties '{"Status": {"select": {"name": "In Progress"}}}'
    """
    if not api_key:
        click.echo("❌ Error: --api-key required or set NOTION_API_KEY", err=True)
        sys.exit(1)

    # Determine parent ID from various sources
    if not parent_id:
        if parent_type == 'database' and database_id:
            parent_id = database_id
        elif parent_type == 'page' and page_id:
            parent_id = page_id
        else:
            click.echo(f"❌ Error: --parent-id or --{parent_type}-id required", err=True)
            sys.exit(1)

    async def _create():
        try:
            headers = get_auth_headers(api_key)
            async with httpx.AsyncClient(
                base_url="https://api.notion.com/v1/",
                headers=headers,
                timeout=30.0
            ) as client:
                api = PagesAPI(client)

                # Build base properties with title
                page_properties = {
                    "title": {
                        "title": [
                            {
                                "type": "text",
                                "text": {"content": title}
                            }
                        ]
                    }
                }

                # Merge additional properties if provided
                if properties:
                    try:
                        custom_props = json.loads(properties)
                        page_properties.update(custom_props)
                    except json.JSONDecodeError as e:
                        return {
                            "success": False,
                            "error": f"Invalid JSON in --properties: {e}"
                        }

                # Parse content blocks if provided
                children = None
                if content:
                    try:
                        children = json.loads(content)
                    except json.JSONDecodeError as e:
                        return {
                            "success": False,
                            "error": f"Invalid JSON in --content: {e}"
                        }

                is_database = parent_type == 'database'
                result = await api.create_page(
                    parent_id=parent_id,
                    properties=page_properties,
                    children=children,
                    is_database=is_database
                )

                return {
                    "success": True,
                    "page": {
                        "id": result.get("id"),
                        "url": result.get("url"),
                        "created_time": result.get("created_time"),
                        "parent": result.get("parent")
                    }
                }

        except httpx.HTTPStatusError as e:
            error_detail = e.response.text
            return {
                "success": False,
                "error": f"HTTP {e.response.status_code}: {error_detail}"
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"Error: {str(e)}"
            }

    result = asyncio.run(_create())
    click.echo(json.dumps(result, indent=2))
    sys.exit(0 if result.get("success") else 1)


@pages.command()
@click.argument('page-id')
@click.option('--api-key', envvar='NOTION_API_KEY', help='Notion API key')
def get(page_id: str, api_key: str | None):
    """
    Get page information by ID.

    Example:
        uv run scripts/notion-pages.py get abc123-def456-...
    """
    if not api_key:
        click.echo("❌ Error: --api-key required or set NOTION_API_KEY", err=True)
        sys.exit(1)

    async def _get():
        try:
            headers = get_auth_headers(api_key)
            async with httpx.AsyncClient(
                base_url="https://api.notion.com/v1/",
                headers=headers,
                timeout=30.0
            ) as client:
                api = PagesAPI(client)
                result = await api.get_page(page_id)

                return {
                    "success": True,
                    "page": result
                }

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                return {
                    "success": False,
                    "error": f"Page not found or integration lacks access: {page_id}"
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

    result = asyncio.run(_get())
    click.echo(json.dumps(result, indent=2))
    sys.exit(0 if result.get("success") else 1)


@pages.command()
@click.argument('page-id')
@click.option('--api-key', envvar='NOTION_API_KEY', help='Notion API key')
@click.option('--properties', required=True, help='Updated properties as JSON')
def update(page_id: str, api_key: str | None, properties: str):
    """
    Update page properties.

    Example:
        uv run scripts/notion-pages.py update abc123 \\
            --properties '{"Status": {"select": {"name": "Done"}}}'
    """
    if not api_key:
        click.echo("❌ Error: --api-key required or set NOTION_API_KEY", err=True)
        sys.exit(1)

    async def _update():
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
                api = PagesAPI(client)
                result = await api.update_page(page_id, props)

                return {
                    "success": True,
                    "page": {
                        "id": result.get("id"),
                        "url": result.get("url"),
                        "last_edited_time": result.get("last_edited_time")
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

    result = asyncio.run(_update())
    click.echo(json.dumps(result, indent=2))
    sys.exit(0 if result.get("success") else 1)


@pages.command()
@click.argument('page-id')
@click.option('--api-key', envvar='NOTION_API_KEY', help='Notion API key')
def archive(page_id: str, api_key: str | None):
    """
    Archive a page.

    Example:
        uv run scripts/notion-pages.py archive abc123
    """
    if not api_key:
        click.echo("❌ Error: --api-key required or set NOTION_API_KEY", err=True)
        sys.exit(1)

    async def _archive():
        try:
            headers = get_auth_headers(api_key)
            async with httpx.AsyncClient(
                base_url="https://api.notion.com/v1/",
                headers=headers,
                timeout=30.0
            ) as client:
                api = PagesAPI(client)
                result = await api.archive_page(page_id)

                return {
                    "success": True,
                    "message": f"Page {page_id} archived successfully",
                    "page": {
                        "id": result.get("id"),
                        "archived": result.get("archived")
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

    result = asyncio.run(_archive())
    click.echo(json.dumps(result, indent=2))
    sys.exit(0 if result.get("success") else 1)


@pages.command()
@click.argument('page-id')
@click.option('--api-key', envvar='NOTION_API_KEY', help='Notion API key')
def restore(page_id: str, api_key: str | None):
    """
    Restore an archived page.

    Example:
        uv run scripts/notion-pages.py restore abc123
    """
    if not api_key:
        click.echo("❌ Error: --api-key required or set NOTION_API_KEY", err=True)
        sys.exit(1)

    async def _restore():
        try:
            headers = get_auth_headers(api_key)
            async with httpx.AsyncClient(
                base_url="https://api.notion.com/v1/",
                headers=headers,
                timeout=30.0
            ) as client:
                api = PagesAPI(client)
                result = await api.restore_page(page_id)

                return {
                    "success": True,
                    "message": f"Page {page_id} restored successfully",
                    "page": {
                        "id": result.get("id"),
                        "archived": result.get("archived")
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

    result = asyncio.run(_restore())
    click.echo(json.dumps(result, indent=2))
    sys.exit(0 if result.get("success") else 1)


@pages.command()
@click.argument('page-id')
@click.argument('property-id')
@click.option('--api-key', envvar='NOTION_API_KEY', help='Notion API key')
def get_property(page_id: str, property_id: str, api_key: str | None):
    """
    Get a specific property value from a page.

    Example:
        uv run scripts/notion-pages.py get-property abc123 title
    """
    if not api_key:
        click.echo("❌ Error: --api-key required or set NOTION_API_KEY", err=True)
        sys.exit(1)

    async def _get_property():
        try:
            headers = get_auth_headers(api_key)
            async with httpx.AsyncClient(
                base_url="https://api.notion.com/v1/",
                headers=headers,
                timeout=30.0
            ) as client:
                api = PagesAPI(client)
                result = await api.get_page_property(page_id, property_id)

                return {
                    "success": True,
                    "property": result
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

    result = asyncio.run(_get_property())
    click.echo(json.dumps(result, indent=2))
    sys.exit(0 if result.get("success") else 1)


if __name__ == "__main__":
    pages()
