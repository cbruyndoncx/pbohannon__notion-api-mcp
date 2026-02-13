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
Notion Blocks API - Block content operations.

Usage:
    # Add text block to a page
    uv run scripts/notion-blocks.py add <page-id> --text "Hello, world!"

    # Add blocks from JSON
    uv run scripts/notion-blocks.py add <page-id> --blocks '[{"type": "paragraph", ...}]'

    # Get block content
    uv run scripts/notion-blocks.py get <block-id>

    # Update block content
    uv run scripts/notion-blocks.py update <block-id> --content '{"paragraph": {...}}'

    # Delete a block
    uv run scripts/notion-blocks.py delete <block-id>

    # List child blocks
    uv run scripts/notion-blocks.py list-children <block-id>

Environment Variables:
    NOTION_API_KEY - Required: Notion integration token
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

from notion_api_mcp.api.blocks import BlocksAPI
from notion_api_mcp.utils.auth import get_auth_headers

# Load .env file if it exists
env_path = project_root / ".env"
if env_path.exists():
    load_dotenv(env_path)


@click.group()
def blocks():
    """Manage Notion blocks - add, read, update, delete content."""
    pass


@blocks.command()
@click.argument('block-id')
@click.option('--api-key', envvar='NOTION_API_KEY', help='Notion API key')
@click.option('--text', help='Simple text to add as paragraph')
@click.option('--blocks', help='Block objects as JSON array')
@click.option('--after', help='Block ID to insert after (for positioning)')
def add(block_id: str, api_key: str | None, text: str | None,
        blocks: str | None, after: str | None):
    """
    Add content blocks to a page or block.

    Examples:
        # Add simple text
        uv run scripts/notion-blocks.py add abc123 --text "Hello"

        # Add multiple blocks from JSON
        uv run scripts/notion-blocks.py add abc123 --blocks '[
            {"type": "paragraph", "paragraph": {"rich_text": [{"text": {"content": "First"}}]}},
            {"type": "heading_1", "heading_1": {"rich_text": [{"text": {"content": "Title"}}]}}
        ]'

        # Add after a specific block
        uv run scripts/notion-blocks.py add abc123 --text "After" --after xyz789
    """
    if not api_key:
        click.echo("❌ Error: --api-key required or set NOTION_API_KEY", err=True)
        sys.exit(1)

    if not text and not blocks:
        click.echo("❌ Error: --text or --blocks required", err=True)
        sys.exit(1)

    async def _add():
        try:
            # Build blocks array
            blocks_array = []

            if text:
                # Create simple paragraph block
                blocks_array.append({
                    "type": "paragraph",
                    "paragraph": {
                        "rich_text": [
                            {
                                "type": "text",
                                "text": {"content": text}
                            }
                        ]
                    }
                })

            if blocks:
                try:
                    custom_blocks = json.loads(blocks)
                    if isinstance(custom_blocks, list):
                        blocks_array.extend(custom_blocks)
                    else:
                        blocks_array.append(custom_blocks)
                except json.JSONDecodeError as e:
                    return {
                        "success": False,
                        "error": f"Invalid JSON in --blocks: {e}"
                    }

            headers = get_auth_headers(api_key)
            async with httpx.AsyncClient(
                base_url="https://api.notion.com/v1/",
                headers=headers,
                timeout=30.0
            ) as client:
                api = BlocksAPI(client)
                result = await api.append_children(
                    block_id=block_id,
                    blocks=blocks_array,
                    after=after
                )

                # Handle single or batched results
                if isinstance(result, list):
                    total_blocks = sum(len(r.get("results", [])) for r in result)
                    return {
                        "success": True,
                        "message": f"Added {total_blocks} blocks in {len(result)} batches",
                        "batches": len(result),
                        "results": result
                    }
                else:
                    return {
                        "success": True,
                        "message": f"Added {len(result.get('results', []))} blocks",
                        "results": result.get("results", [])
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

    result = asyncio.run(_add())
    click.echo(json.dumps(result, indent=2))
    sys.exit(0 if result.get("success") else 1)


@blocks.command()
@click.argument('block-id')
@click.option('--api-key', envvar='NOTION_API_KEY', help='Notion API key')
def get(block_id: str, api_key: str | None):
    """
    Get block content by ID.

    Example:
        uv run scripts/notion-blocks.py get abc123
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
                api = BlocksAPI(client)
                result = await api.get_block(block_id)

                return {
                    "success": True,
                    "block": result
                }

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                return {
                    "success": False,
                    "error": f"Block not found or integration lacks access: {block_id}"
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


@blocks.command()
@click.argument('block-id')
@click.option('--api-key', envvar='NOTION_API_KEY', help='Notion API key')
@click.option('--page-size', type=int, default=100, help='Page size (default: 100)')
def list_children(block_id: str, api_key: str | None, page_size: int):
    """
    List child blocks of a parent block.

    Example:
        uv run scripts/notion-blocks.py list-children abc123
    """
    if not api_key:
        click.echo("❌ Error: --api-key required or set NOTION_API_KEY", err=True)
        sys.exit(1)

    async def _list():
        try:
            headers = get_auth_headers(api_key)
            async with httpx.AsyncClient(
                base_url="https://api.notion.com/v1/",
                headers=headers,
                timeout=30.0
            ) as client:
                api = BlocksAPI(client)
                result = await api.list_block_children(
                    block_id=block_id,
                    page_size=page_size
                )

                return {
                    "success": True,
                    "results": result.get("results", []),
                    "count": len(result.get("results", [])),
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

    result = asyncio.run(_list())
    click.echo(json.dumps(result, indent=2))
    sys.exit(0 if result.get("success") else 1)


@blocks.command()
@click.argument('block-id')
@click.option('--api-key', envvar='NOTION_API_KEY', help='Notion API key')
@click.option('--content', required=True, help='Updated block content as JSON')
def update(block_id: str, api_key: str | None, content: str):
    """
    Update block content.

    Example:
        uv run scripts/notion-blocks.py update abc123 \\
            --content '{"paragraph": {"rich_text": [{"text": {"content": "Updated text"}}]}}'
    """
    if not api_key:
        click.echo("❌ Error: --api-key required or set NOTION_API_KEY", err=True)
        sys.exit(1)

    async def _update():
        try:
            # Parse content JSON
            try:
                content_obj = json.loads(content)
            except json.JSONDecodeError as e:
                return {
                    "success": False,
                    "error": f"Invalid JSON in --content: {e}"
                }

            headers = get_auth_headers(api_key)
            async with httpx.AsyncClient(
                base_url="https://api.notion.com/v1/",
                headers=headers,
                timeout=30.0
            ) as client:
                api = BlocksAPI(client)
                result = await api.update_block(block_id, content_obj)

                return {
                    "success": True,
                    "block": {
                        "id": result.get("id"),
                        "type": result.get("type"),
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


@blocks.command()
@click.argument('block-id')
@click.option('--api-key', envvar='NOTION_API_KEY', help='Notion API key')
@click.confirmation_option(prompt='Are you sure you want to delete this block?')
def delete(block_id: str, api_key: str | None):
    """
    Delete a block.

    Example:
        uv run scripts/notion-blocks.py delete abc123
    """
    if not api_key:
        click.echo("❌ Error: --api-key required or set NOTION_API_KEY", err=True)
        sys.exit(1)

    async def _delete():
        try:
            headers = get_auth_headers(api_key)
            async with httpx.AsyncClient(
                base_url="https://api.notion.com/v1/",
                headers=headers,
                timeout=30.0
            ) as client:
                api = BlocksAPI(client)
                result = await api.delete_block(block_id)

                return {
                    "success": True,
                    "message": f"Block {block_id} deleted successfully",
                    "block": {
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

    result = asyncio.run(_delete())
    click.echo(json.dumps(result, indent=2))
    sys.exit(0 if result.get("success") else 1)


if __name__ == "__main__":
    blocks()
