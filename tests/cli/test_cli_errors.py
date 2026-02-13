"""
Tests for CLI error handling and edge cases.
"""
import json
from unittest.mock import patch, MagicMock, AsyncMock
from pathlib import Path

import pytest
import httpx

# Import the CLI module
import sys
scripts_dir = Path(__file__).parent.parent.parent / "scripts"
sys.path.insert(0, str(scripts_dir))

from notion import cli


class TestAuthenticationErrors:
    """Tests for authentication-related errors."""

    def test_list_missing_api_key(self, runner, monkeypatch):
        """List command fails when NOTION_API_KEY is missing."""
        monkeypatch.delenv("NOTION_API_KEY", raising=False)

        result = runner.invoke(cli, ['list', 'pages'])

        assert result.exit_code != 0
        assert "NOTION_API_KEY" in result.output or "API key" in result.output


class TestValidationErrors:
    """Tests for validation and input errors."""

    def test_add_page_missing_title(self, runner, monkeypatch):
        """Add page fails when title is missing."""
        monkeypatch.setenv("NOTION_API_KEY", "ntn_test_key_123")

        result = runner.invoke(cli, ['add', 'page', '--parent', 'parent-123'])

        assert result.exit_code != 0
        # Click will complain about missing required option
        assert "Missing option" in result.output or "--title" in result.output

    def test_list_invalid_entity_choice(self, runner, monkeypatch):
        """List command rejects invalid entity type."""
        monkeypatch.setenv("NOTION_API_KEY", "ntn_test_key_123")

        result = runner.invoke(cli, ['list', 'invalid_entity'])

        assert result.exit_code != 0
        # Click will validate the choice
        assert "Invalid value" in result.output or "choice" in result.output.lower()

    def test_get_invalid_entity_choice(self, runner, monkeypatch):
        """Get command rejects invalid entity type."""
        monkeypatch.setenv("NOTION_API_KEY", "ntn_test_key_123")

        result = runner.invoke(cli, ['get', 'invalid_entity', 'some-id'])

        assert result.exit_code != 0
        # Click will validate the choice
        assert "Invalid value" in result.output or "choice" in result.output.lower()

    def test_delete_invalid_entity_choice(self, runner, monkeypatch):
        """Delete command rejects invalid entity type."""
        monkeypatch.setenv("NOTION_API_KEY", "ntn_test_key_123")

        result = runner.invoke(cli, ['delete', 'invalid_entity', 'some-id'])

        assert result.exit_code != 0
        # Click will validate the choice
        assert "Invalid value" in result.output or "choice" in result.output.lower()

    def test_add_todo_missing_database_and_env(self, runner, monkeypatch):
        """Add todo fails when database is not provided and env var not set."""
        monkeypatch.setenv("NOTION_API_KEY", "ntn_test_key_123")
        monkeypatch.delenv("NOTION_DATABASE_ID", raising=False)

        result = runner.invoke(cli, [
            'add', 'todo',
            '--title', 'Test Todo'
        ])

        assert result.exit_code != 0
        # Should error about missing database
        assert "database" in result.output.lower() or "NOTION_DATABASE_ID" in result.output


class TestEdgeCases:
    """Tests for edge cases and unusual inputs."""

    def test_command_with_no_args(self, runner):
        """CLI with no arguments shows help."""
        result = runner.invoke(cli, [])

        # Should show usage/help, not crash
        assert result.exit_code in [0, 2]  # 0 for help, 2 for missing command
        assert "Usage:" in result.output or "Commands:" in result.output

    def test_unknown_command(self, runner):
        """Unknown command shows error."""
        result = runner.invoke(cli, ['nonexistent-command'])

        assert result.exit_code != 0
        assert "No such command" in result.output or "Error" in result.output

    def test_help_flag(self, runner):
        """Help flag works."""
        result = runner.invoke(cli, ['--help'])

        assert result.exit_code == 0
        assert "Usage:" in result.output
        assert "Commands:" in result.output

    def test_add_help(self, runner):
        """Add subcommand help works."""
        result = runner.invoke(cli, ['add', '--help'])

        assert result.exit_code == 0
        assert "Commands:" in result.output
        assert "page" in result.output
        assert "database" in result.output

    def test_blocks_help(self, runner):
        """Blocks subcommand help works."""
        result = runner.invoke(cli, ['blocks', '--help'])

        assert result.exit_code == 0
        assert "Commands:" in result.output or "Usage:" in result.output
