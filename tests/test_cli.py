"""CLI surface for find / search flags (backend mocked)."""

from __future__ import annotations

from typer.testing import CliRunner

from apple_notes.cli import app
from apple_notes.models import Note

runner = CliRunner()


def test_find_requires_title():
    result = runner.invoke(app, ["find"])
    assert result.exit_code != 0


def test_find_prints_matches(monkeypatch):
    def fake_find(title, folder=None):
        assert title == "02 September"
        assert folder is None
        return [Note(id="id1", title="02 September", folder="Planner")]

    monkeypatch.setattr("apple_notes.cli.core.find_notes_by_title", fake_find)
    result = runner.invoke(app, ["find", "--title", "02 September"])
    assert result.exit_code == 0
    assert "02 September" in result.stdout
    assert "id1" in result.stdout


def test_find_no_match_is_error(monkeypatch):
    monkeypatch.setattr(
        "apple_notes.cli.core.find_notes_by_title", lambda *a, **k: []
    )
    result = runner.invoke(app, ["find", "--title", "missing"])
    assert result.exit_code == 1
    assert "no note titled" in result.stderr


def test_search_passes_title_only(monkeypatch):
    seen: dict = {}

    def fake_search(query, folder=None, title_only=False):
        seen["query"] = query
        seen["folder"] = folder
        seen["title_only"] = title_only
        return []

    monkeypatch.setattr("apple_notes.cli.core.search_notes", fake_search)
    result = runner.invoke(app, ["search", "02 September", "--title-only"])
    assert result.exit_code == 0
    assert seen == {
        "query": "02 September",
        "folder": None,
        "title_only": True,
    }


def test_no_update_command():
    result = runner.invoke(app, ["update", "--help"])
    assert result.exit_code != 0
