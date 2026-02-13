# CLI Scripts Migration Guide

This guide helps you understand how to use the new standalone CLI scripts alongside or instead of the MCP server.

## Overview

The Notion API MCP project now provides two ways to interact with Notion:

1. **MCP Server** (Original) - For AI-powered interactions via Claude Desktop
2. **CLI Scripts** (New) - For direct command-line usage and automation

Both approaches use the same underlying API client code, so functionality is identical.

## Quick Comparison

| Feature | MCP Server | CLI Scripts |
|---------|------------|-------------|
| **Usage** | Via Claude Desktop/MCP clients | Direct `uv run` commands |
| **Setup** | Requires config in Claude Desktop | Just set environment variables |
| **Dependencies** | Manual installation | Auto-installed via PEP 723 |
| **Best for** | Conversational AI workflows | Shell scripts, automation, CI/CD |
| **Installation** | `uv pip install -e .` | No installation needed |

## MCP Server → CLI Script Mapping

### Diagnostics

**MCP Server:**
```
# Use verify_connection tool via Claude
"Please verify my Notion API connection"
```

**CLI Scripts:**
```bash
uv run scripts/notion-utils.py verify-connection
uv run scripts/notion-utils.py get-database-info --database-id <id>
uv run scripts/notion-utils.py check-config
```

### Page Operations

**MCP Server:**
```
# Ask Claude
"Create a page titled 'My Page' in database <id>"
"Get page <id>"
"Archive page <id>"
```

**CLI Scripts:**
```bash
uv run scripts/notion-pages.py create --database-id <id> --title "My Page"
uv run scripts/notion-pages.py get <page-id>
uv run scripts/notion-pages.py archive <page-id>
uv run scripts/notion-pages.py restore <page-id>
```

### Database & Todo Operations

**MCP Server:**
```
# Ask Claude
"Add a todo: Complete project, priority High, due 2026-12-31"
"Search for todos with status In Progress"
```

**CLI Scripts:**
```bash
uv run scripts/notion-databases.py add-todo --database-id <id> \
    --title "Complete project" \
    --priority "High" \
    --due-date "2026-12-31"

uv run scripts/notion-databases.py search-todos --database-id <id> \
    --status "In Progress"

uv run scripts/notion-databases.py query --database-id <id> \
    --filter '{"property": "Status", "select": {"equals": "Done"}}'
```

### Block/Content Operations

**MCP Server:**
```
# Ask Claude
"Add content to page <id>: Hello world"
```

**CLI Scripts:**
```bash
uv run scripts/notion-blocks.py add <page-id> --text "Hello world"

uv run scripts/notion-blocks.py get <block-id>
uv run scripts/notion-blocks.py list-children <page-id>
uv run scripts/notion-blocks.py update <block-id> --content '{...}'
uv run scripts/notion-blocks.py delete <block-id>
```

## Configuration

### MCP Server Configuration

**Location:** `~/Library/Application Support/Claude/claude_desktop_config.json`

```json
{
  "mcpServers": {
    "notion-api": {
      "command": "/path/to/.venv/bin/python",
      "args": ["-m", "notion_api_mcp"],
      "env": {
        "NOTION_API_KEY": "ntn_...",
        "NOTION_DATABASE_ID": "...",
        "NOTION_PARENT_PAGE_ID": "..."
      }
    }
  }
}
```

### CLI Scripts Configuration

**Option 1: Environment Variables**
```bash
export NOTION_API_KEY="ntn_..."
export NOTION_DATABASE_ID="..."
export NOTION_PARENT_PAGE_ID="..."
```

**Option 2: .env File**
```bash
# Create .env in project root
cat > .env << EOF
NOTION_API_KEY=ntn_...
NOTION_DATABASE_ID=...
NOTION_PARENT_PAGE_ID=...
EOF
```

**Option 3: CLI Flags**
```bash
uv run scripts/notion-pages.py create \
    --api-key "ntn_..." \
    --database-id "..." \
    --title "My Page"
```

## Use Cases

### When to Use MCP Server

✅ **Best for:**
- Working with Claude Desktop
- Conversational workflows ("create a todo for me")
- Complex multi-step operations guided by AI
- Natural language task descriptions

❌ **Not ideal for:**
- Shell scripting
- CI/CD pipelines
- Cron jobs
- Quick one-off commands

### When to Use CLI Scripts

✅ **Best for:**
- Shell scripts and automation
- CI/CD pipelines
- Cron jobs and scheduled tasks
- Quick command-line operations
- Non-interactive workflows

❌ **Not ideal for:**
- Exploratory work where you're unsure what to do
- Complex workflows requiring decision-making
- Tasks better described in natural language

## Migration Strategies

### Strategy 1: Gradual Migration

Keep both MCP server and CLI scripts:
- Use MCP server for interactive work with Claude
- Use CLI scripts for automation and scripting
- Both share the same `.env` configuration

### Strategy 2: CLI-First

Use CLI scripts exclusively:
```bash
# Create aliases for common operations
alias notion-verify="uv run scripts/notion-utils.py verify-connection"
alias notion-add-todo="uv run scripts/notion-databases.py add-todo"

# Add to shell automation
./scripts/backup-notion.sh  # Your custom script using CLI tools
```

### Strategy 3: MCP-First

Continue using MCP server, use CLI for specific automation:
```bash
# Keep using Claude Desktop for main work
# Use CLI only for scheduled tasks
0 9 * * * /usr/bin/uv run /path/to/scripts/notion-databases.py add-todo \
    --title "Daily standup" --due-date "$(date +%Y-%m-%d)"
```

## Example: Automation Workflow

### Before (MCP Server only)

Had to manually ask Claude to create recurring tasks.

### After (CLI Scripts)

Create a shell script for automated task creation:

```bash
#!/bin/bash
# daily-tasks.sh

export NOTION_DATABASE_ID="your-db-id"
export NOTION_API_KEY="ntn_..."

# Add daily standup task
uv run scripts/notion-databases.py add-todo \
    --title "Daily Standup" \
    --due-date "$(date +%Y-%m-%d)" \
    --priority "Medium" \
    --tags "meeting,daily"

# Check for overdue tasks
uv run scripts/notion-databases.py search-todos \
    --overdue-only

echo "Daily tasks created!"
```

Then schedule with cron:
```bash
# Run every weekday at 9 AM
0 9 * * 1-5 /path/to/daily-tasks.sh
```

## Advanced: Combining Both

You can use both approaches together:

```bash
# Use CLI to create structured data
uv run scripts/notion-databases.py add-todo \
    --title "Review PR #123" \
    --priority "High" \
    --output json > /tmp/todo.json

# Then ask Claude to analyze and act on it
# "Claude, check my Notion todos and prioritize my day"
```

## Troubleshooting

### CLI Scripts Not Finding Dependencies

The scripts use PEP 723 inline dependencies. If you see import errors:
```bash
# Try running with --refresh
uv run --refresh scripts/notion-utils.py verify-connection
```

### MCP Server Still Running

Both can run simultaneously - they're independent:
```bash
# CLI doesn't interfere with MCP server
uv run scripts/notion-pages.py create --database-id <id> --title "Test"

# Claude Desktop MCP continues working normally
```

### Environment Variables Not Loading

Check your `.env` file location:
```bash
# Should be in project root
cat .env

# Check what's loaded
uv run scripts/notion-utils.py check-config
```

## Getting Help

### CLI Scripts
```bash
# Each script has detailed help
uv run scripts/notion-utils.py --help
uv run scripts/notion-pages.py --help
uv run scripts/notion-pages.py create --help  # Command-specific help
```

### MCP Server

See existing documentation:
- [Configuration](configuration.md)
- [Architecture](ARCHITECTURE.md)
- [Features](features.md)

## Summary

The CLI scripts provide a new way to interact with Notion API directly from the command line, perfect for automation and scripting. The MCP server remains available for AI-powered workflows through Claude Desktop.

**Key takeaways:**
- ✅ Both approaches use the same underlying code
- ✅ Both can be used simultaneously
- ✅ CLI scripts require no installation (PEP 723)
- ✅ Choose the right tool for your use case
- ✅ Configuration can be shared via `.env` file
