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
Notion API Utilities - Diagnostic and configuration tools.

Usage:
    uv run scripts/notion-utils.py verify-connection
    uv run scripts/notion-utils.py get-database-info
    uv run scripts/notion-utils.py check-config
    uv run scripts/notion-utils.py search
    uv run scripts/notion-utils.py search --query "project" --filter page

Environment Variables:
    NOTION_API_KEY        - Required: Notion integration token
    NOTION_DATABASE_ID    - Optional: Default database ID
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

# Load .env file if it exists
env_path = project_root / ".env"
if env_path.exists():
    load_dotenv(env_path)


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


@click.group()
def cli():
    """Notion API diagnostic and utility commands."""
    pass


@cli.command()
@click.option('--api-key', envvar='NOTION_API_KEY', help='Notion API key (or set NOTION_API_KEY)')
def verify_connection(api_key: str | None):
    """
    Verify Notion API connection and authentication.

    Tests the connection by fetching the current user's information.
    """
    if not api_key:
        click.echo("❌ Error: --api-key required or set NOTION_API_KEY environment variable", err=True)
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
@click.option('--api-key', envvar='NOTION_API_KEY', help='Notion API key (or set NOTION_API_KEY)')
@click.option('--database-id', envvar='NOTION_DATABASE_ID', help='Database ID (or set NOTION_DATABASE_ID)')
def get_database_info(api_key: str | None, database_id: str | None):
    """
    Get information about a configured Notion database.

    Retrieves database metadata including properties, title, and URL.
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

                # Extract property names and types
                properties = {}
                for prop_name, prop_data in db_info.get("properties", {}).items():
                    properties[prop_name] = prop_data.get("type")

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
            elif e.response.status_code == 401:
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

    result = asyncio.run(_get_info())
    click.echo(json.dumps(result, indent=2))
    sys.exit(0 if result.get("success") else 1)


@cli.command()
def check_config():
    """
    Check current environment configuration.

    Displays which environment variables are set and their values (masked for API key).
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


@cli.command()
@click.option('--api-key', envvar='NOTION_API_KEY', help='Notion API key (or set NOTION_API_KEY)')
@click.option('--query', default='', help='Search query text (empty = return all)')
@click.option('--filter', type=click.Choice(['page', 'database']), help='Filter results by type')
@click.option('--sort', type=click.Choice(['ascending', 'descending']), default='descending',
              help='Sort by last edited time')
@click.option('--page-size', default=100, type=int, help='Number of results per page (max 100)')
@click.option('--all-pages', is_flag=True, help='Fetch all pages (not just first page of results)')
def search(api_key: str | None, query: str, filter: str | None, sort: str, page_size: int, all_pages: bool):
    """
    Search all pages and databases accessible to the integration.

    Examples:
        # List all pages and databases
        uv run scripts/notion-utils.py search

        # Search for specific content
        uv run scripts/notion-utils.py search --query "project"

        # Filter by type
        uv run scripts/notion-utils.py search --filter page
        uv run scripts/notion-utils.py search --filter database

        # Get all results (with pagination)
        uv run scripts/notion-utils.py search --all-pages
    """
    if not api_key:
        click.echo("❌ Error: --api-key required or set NOTION_API_KEY", err=True)
        sys.exit(1)

    async def _search():
        try:
            headers = get_auth_headers(api_key)
            async with httpx.AsyncClient(
                base_url="https://api.notion.com/v1/",
                headers=headers,
                timeout=30.0
            ) as client:
                all_results = []
                start_cursor = None
                has_more = True

                while has_more:
                    # Build request body
                    body = {
                        "page_size": min(page_size, 100),
                        "sort": {
                            "direction": sort,
                            "timestamp": "last_edited_time"
                        }
                    }

                    if query:
                        body["query"] = query

                    if filter:
                        body["filter"] = {
                            "value": filter,
                            "property": "object"
                        }

                    if start_cursor:
                        body["start_cursor"] = start_cursor

                    # Make request
                    response = await client.post("search", json=body)
                    response.raise_for_status()
                    data = response.json()

                    # Collect results
                    all_results.extend(data.get("results", []))

                    # Check pagination
                    has_more = data.get("has_more", False)
                    start_cursor = data.get("next_cursor")

                    # If not fetching all pages, break after first request
                    if not all_pages:
                        break

                # Format results
                formatted_results = []
                for item in all_results:
                    obj_type = item.get("object")

                    # Extract title
                    title = "Untitled"
                    if obj_type == "page":
                        # Pages have title in properties
                        props = item.get("properties", {})
                        title_prop = props.get("title") or props.get("Name")
                        if title_prop and title_prop.get("title"):
                            title = title_prop["title"][0].get("plain_text", "Untitled")
                    elif obj_type == "database":
                        # Databases have title at root level
                        if item.get("title") and len(item["title"]) > 0:
                            title = item["title"][0].get("plain_text", "Untitled")

                    formatted_results.append({
                        "id": item.get("id"),
                        "type": obj_type,
                        "title": title,
                        "url": item.get("url"),
                        "created_time": item.get("created_time"),
                        "last_edited_time": item.get("last_edited_time"),
                        "archived": item.get("archived", False)
                    })

                return {
                    "success": True,
                    "total_results": len(formatted_results),
                    "has_more": has_more if not all_pages else False,
                    "results": formatted_results
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

    result = asyncio.run(_search())
    click.echo(json.dumps(result, indent=2))
    sys.exit(0 if result.get("success") else 1)


if __name__ == "__main__":
    cli()
