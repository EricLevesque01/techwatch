"""Integration tests for the CLI interface."""

from __future__ import annotations

import os

import pytest
from typer.testing import CliRunner

# Set test database URL before importing the app
os.environ["DATABASE_URL"] = "sqlite:///test_techwatch.db"
os.environ["TECHWATCH_COUNTRY"] = "US"
os.environ["TECHWATCH_CURRENCY"] = "USD"

from techwatch.cli.app import app  # noqa: E402
from techwatch.config import reset_settings  # noqa: E402
from techwatch.persistence.database import init_db, reset_engine  # noqa: E402

runner = CliRunner()


@pytest.fixture(autouse=True)
def _clean_db(tmp_path):
    """Reset database and settings for each test."""
    os.environ["DATABASE_URL"] = f"sqlite:///{tmp_path}/test.db"
    reset_settings()
    reset_engine()
    init_db()
    yield
    reset_settings()
    reset_engine()


class TestVersion:
    def test_version_flag(self):
        result = runner.invoke(app, ["--version"])
        assert result.exit_code == 0
        assert "techwatch" in result.stdout
        assert "0.1.0" in result.stdout


class TestSearch:
    def test_search_basic(self):
        result = runner.invoke(app, ["search", "used thinkpad x1"])
        assert result.exit_code == 0
        assert "Searching" in result.stdout

    def test_search_with_budget(self):
        result = runner.invoke(app, ["search", "laptop", "--budget", "900"])
        assert result.exit_code == 0
        assert "900" in result.stdout

    def test_search_with_conditions(self):
        result = runner.invoke(
            app,
            ["search", "monitor", "--conditions", "new,open_box"],
        )
        assert result.exit_code == 0
        assert "new" in result.stdout


class TestWatch:
    def test_watch_create(self):
        result = runner.invoke(
            app,
            [
                "watch", "create", "oled monitor",
                "--budget", "650",
                "--schedule", "0 9 * * *",
            ],
        )
        assert result.exit_code == 0
        assert "Watch created" in result.stdout

    def test_watch_list_empty(self):
        result = runner.invoke(app, ["watch", "list"])
        assert result.exit_code == 0
        assert "No watches found" in result.stdout

    def test_watch_lifecycle(self):
        import re

        # Create
        result = runner.invoke(app, ["watch", "create", "test query"])
        assert result.exit_code == 0
        assert "Watch created" in result.stdout

        # Extract watch ID (12-char hex string) from output
        match = re.search(r"Watch created.*?([a-f0-9]{12})", result.stdout)
        assert match, f"Could not find watch ID in output: {result.stdout}"
        watch_id = match.group(1)

        # List
        result = runner.invoke(app, ["watch", "list"])
        assert result.exit_code == 0
        # Watch ID may be truncated in table; check first 5 chars
        assert watch_id[:5] in result.stdout

        # Pause
        result = runner.invoke(app, ["watch", "pause", watch_id])
        assert result.exit_code == 0
        assert "paused" in result.stdout

        # Resume
        result = runner.invoke(app, ["watch", "resume", watch_id])
        assert result.exit_code == 0
        assert "resumed" in result.stdout

        # Delete
        result = runner.invoke(app, ["watch", "delete", watch_id, "--yes"])
        assert result.exit_code == 0
        assert "deleted" in result.stdout


class TestSource:
    def test_source_test_unknown(self):
        result = runner.invoke(app, ["source", "test", "fakeadapter"])
        assert result.exit_code == 1

    def test_source_test_structured(self):
        result = runner.invoke(app, ["source", "test", "structured"])
        assert result.exit_code == 0
        assert "no credentials" in result.stdout.lower()


class TestHelp:
    def test_main_help(self):
        result = runner.invoke(app, ["--help"])
        assert result.exit_code == 0
        assert "search" in result.stdout
        assert "watch" in result.stdout

    def test_search_help(self):
        result = runner.invoke(app, ["search", "--help"])
        assert result.exit_code == 0
        assert "budget" in result.stdout.lower()

    def test_watch_help(self):
        result = runner.invoke(app, ["watch", "--help"])
        assert result.exit_code == 0
        assert "create" in result.stdout
