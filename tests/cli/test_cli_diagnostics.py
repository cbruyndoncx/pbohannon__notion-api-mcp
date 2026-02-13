"""
Tests for CLI diagnostic commands (verify-connection, check-config).
"""
import json
import os
from unittest.mock import patch, MagicMock, AsyncMock
from pathlib import Path

import pytest
import httpx

# Import the CLI module
import sys
scripts_dir = Path(__file__).parent.parent.parent / "scripts"
sys.path.insert(0, str(scripts_dir))

from notion import verify_connection, check_config


class TestVerifyConnection:
    """Tests for verify-connection command."""

    def test_verify_connection_success(self, runner, monkeypatch):
        """Successful connection verification."""
        # Mock environment variables
        monkeypatch.setenv("NOTION_API_KEY", "ntn_test_key_123")

        # Mock httpx client
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "object": "user",
            "id": "user-123",
            "name": "Test User",
            "type": "person"
        }

        mock_client = AsyncMock()
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None
        mock_client.get = AsyncMock(return_value=mock_response)

        with patch("notion.httpx.AsyncClient", return_value=mock_client):
            result = runner.invoke(verify_connection)

        assert result.exit_code == 0
        # Parse JSON output
        output_data = json.loads(result.output)
        assert output_data["success"] is True
        assert "✅" in output_data["message"]
        assert output_data["user"]["id"] == "user-123"
        assert output_data["user"]["name"] == "Test User"

    def test_verify_connection_missing_api_key(self, runner, monkeypatch):
        """Fail when NOTION_API_KEY is not set."""
        # Remove NOTION_API_KEY from environment
        monkeypatch.delenv("NOTION_API_KEY", raising=False)

        result = runner.invoke(verify_connection)

        assert result.exit_code != 0
        assert "NOTION_API_KEY" in result.output

    def test_verify_connection_invalid_api_key(self, runner, monkeypatch):
        """Fail with 401 when API key is invalid."""
        monkeypatch.setenv("NOTION_API_KEY", "ntn_invalid_key")

        # Mock 401 response
        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_response.text = "Unauthorized"
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "Unauthorized",
            request=MagicMock(),
            response=mock_response
        )

        mock_client = AsyncMock()
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None
        mock_client.get = AsyncMock(return_value=mock_response)

        with patch("notion.httpx.AsyncClient", return_value=mock_client):
            result = runner.invoke(verify_connection)

        assert result.exit_code != 0
        # Parse JSON output
        output_data = json.loads(result.output)
        assert output_data["success"] is False
        assert "invalid API key" in output_data["error"].lower() or "authentication" in output_data["error"].lower()

    def test_verify_connection_network_error(self, runner, monkeypatch):
        """Handle network errors gracefully."""
        monkeypatch.setenv("NOTION_API_KEY", "ntn_test_key_123")

        # Mock network error
        mock_client = AsyncMock()
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None
        mock_client.get = AsyncMock(side_effect=httpx.ConnectError("Connection failed"))

        with patch("notion.httpx.AsyncClient", return_value=mock_client):
            result = runner.invoke(verify_connection)

        assert result.exit_code != 0
        # Parse JSON output
        output_data = json.loads(result.output)
        assert output_data["success"] is False
        assert "connection" in output_data["error"].lower()

    def test_verify_connection_timeout(self, runner, monkeypatch):
        """Handle timeout errors."""
        monkeypatch.setenv("NOTION_API_KEY", "ntn_test_key_123")

        # Mock timeout
        mock_client = AsyncMock()
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None
        mock_client.get = AsyncMock(side_effect=httpx.TimeoutException("Request timed out"))

        with patch("notion.httpx.AsyncClient", return_value=mock_client):
            result = runner.invoke(verify_connection)

        assert result.exit_code != 0
        # Parse JSON output
        output_data = json.loads(result.output)
        assert output_data["success"] is False
        assert "connection" in output_data["error"].lower() or "timeout" in output_data["error"].lower()


class TestCheckConfig:
    """Tests for check-config command."""

    def test_check_config_all_set(self, runner, monkeypatch):
        """All configuration variables are set."""
        monkeypatch.setenv("NOTION_API_KEY", "ntn_test_key_123")
        monkeypatch.setenv("NOTION_DATABASE_ID", "db-123")
        monkeypatch.setenv("NOTION_PARENT_PAGE_ID", "page-123")

        result = runner.invoke(check_config)

        assert result.exit_code == 0
        # Parse JSON output
        output_data = json.loads(result.output)

        # Check all variables are marked as set
        assert output_data["configuration"]["NOTION_API_KEY"]["set"] is True
        assert "..." in output_data["configuration"]["NOTION_API_KEY"]["value"]  # Masked

        assert output_data["configuration"]["NOTION_DATABASE_ID"]["set"] is True
        assert output_data["configuration"]["NOTION_DATABASE_ID"]["value"] == "db-123"

        assert output_data["configuration"]["NOTION_PARENT_PAGE_ID"]["set"] is True
        assert output_data["configuration"]["NOTION_PARENT_PAGE_ID"]["value"] == "page-123"

    def test_check_config_only_api_key(self, runner, monkeypatch):
        """Only NOTION_API_KEY is set (minimum requirement)."""
        monkeypatch.setenv("NOTION_API_KEY", "ntn_test_key_123")
        monkeypatch.delenv("NOTION_DATABASE_ID", raising=False)
        monkeypatch.delenv("NOTION_PARENT_PAGE_ID", raising=False)

        result = runner.invoke(check_config)

        assert result.exit_code == 0
        # Parse JSON output
        output_data = json.loads(result.output)

        # API key is set
        assert output_data["configuration"]["NOTION_API_KEY"]["set"] is True

        # Other vars are not set
        assert output_data["configuration"]["NOTION_DATABASE_ID"]["set"] is False
        assert output_data["configuration"]["NOTION_DATABASE_ID"]["value"] is None

        assert output_data["configuration"]["NOTION_PARENT_PAGE_ID"]["set"] is False
        assert output_data["configuration"]["NOTION_PARENT_PAGE_ID"]["value"] is None

    def test_check_config_missing_api_key(self, runner, monkeypatch):
        """Missing NOTION_API_KEY should be flagged."""
        monkeypatch.delenv("NOTION_API_KEY", raising=False)
        monkeypatch.delenv("NOTION_DATABASE_ID", raising=False)
        monkeypatch.delenv("NOTION_PARENT_PAGE_ID", raising=False)

        result = runner.invoke(check_config)

        assert result.exit_code == 0  # Command succeeds but shows not set
        # Parse JSON output
        output_data = json.loads(result.output)

        # All variables should be marked as not set
        assert output_data["configuration"]["NOTION_API_KEY"]["set"] is False
        assert output_data["configuration"]["NOTION_API_KEY"]["value"] is None

    def test_check_config_masks_api_key(self, runner, monkeypatch):
        """API key should be masked in output."""
        monkeypatch.setenv("NOTION_API_KEY", "ntn_secret_key_should_be_masked_123456")

        result = runner.invoke(check_config)

        assert result.exit_code == 0
        # Parse JSON output
        output_data = json.loads(result.output)

        # Should NOT show full key
        assert "should_be_masked" not in result.output
        # Should show masked version
        masked_value = output_data["configuration"]["NOTION_API_KEY"]["value"]
        assert "..." in masked_value
        assert len(masked_value) < len("ntn_secret_key_should_be_masked_123456")

    def test_check_config_shows_env_file_location(self, runner, monkeypatch):
        """Show .env file location information."""
        monkeypatch.setenv("NOTION_API_KEY", "ntn_test_key_123")

        result = runner.invoke(check_config)

        assert result.exit_code == 0
        # Parse JSON output
        output_data = json.loads(result.output)

        # Should have env_file section
        assert "env_file" in output_data
        assert "path" in output_data["env_file"]
        assert ".env" in output_data["env_file"]["path"]
        assert "exists" in output_data["env_file"]
