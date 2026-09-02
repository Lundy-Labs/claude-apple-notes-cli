"""Core API argument shaping (no osascript)."""

from __future__ import annotations

from apple_notes import notes


def test_find_notes_by_title_passes_whose_args(monkeypatch):
    seen: list[tuple[str, list[str] | None]] = []

    def fake_run_json(name, args=None):
        seen.append((name, args))
        return [{"id": "x", "name": "02 September", "folder": "Planner"}]

    monkeypatch.setattr(notes, "run_json", fake_run_json)
    result = notes.find_notes_by_title("02 September")
    assert seen == [("find_by_title", ["02 September", ""])]
    assert result[0].title == "02 September"
    assert result[0].folder == "Planner"


def test_find_notes_by_title_scopes_folder(monkeypatch):
    seen: list = []

    def fake_run_json(name, args=None):
        seen.append(args)
        return []

    monkeypatch.setattr(notes, "run_json", fake_run_json)
    notes.find_notes_by_title("02 September", folder="Planner")
    assert seen == [["02 September", "Planner"]]


def test_search_title_only_skips_body_folders(monkeypatch):
    seen: list = []

    def fake_run_json(name, args=None):
        seen.append((name, args))
        return []

    monkeypatch.setattr(notes, "run_json", fake_run_json)
    notes.search_notes("02 September", title_only=True)
    assert seen[0][0] == "search_notes"
    query, folder, title_only, body_folders = seen[0][1]
    assert query == "02 September"
    assert folder == ""
    assert title_only == "1"
    assert body_folders == ""


def test_search_body_defaults_to_small_folder_set(monkeypatch):
    seen: list = []

    def fake_run_json(name, args=None):
        seen.append(args)
        return []

    monkeypatch.setattr(notes, "run_json", fake_run_json)
    notes.search_notes("tailscale")
    query, folder, title_only, body_folders = seen[0]
    assert query == "tailscale"
    assert folder == ""
    assert title_only == "0"
    assert "Claude Memory" in body_folders
    assert "Claude Exports" in body_folders
    assert "Planner" not in body_folders


def test_search_body_with_folder_stays_scoped(monkeypatch):
    seen: list = []

    def fake_run_json(name, args=None):
        seen.append(args)
        return []

    monkeypatch.setattr(notes, "run_json", fake_run_json)
    notes.search_notes("weather", folder="Planner")
    _, folder, title_only, body_folders = seen[0]
    assert folder == "Planner"
    assert title_only == "0"
    assert body_folders == "Planner"


def test_list_notes_passes_limit(monkeypatch):
    seen: list = []

    def fake_run_json(name, args=None):
        seen.append((name, args))
        return []

    monkeypatch.setattr(notes, "run_json", fake_run_json)
    notes.list_notes(folder="Notes", limit=50)
    assert seen == [("list_notes", ["Notes", "50"])]


def test_read_note_html_skips_markdown(monkeypatch):
    def fake_run_json(name, args=None):
        return {
            "id": "x",
            "name": "t",
            "folder": "Claude Memory",
            "body": "<div><h2>Weather</h2></div>",
        }

    monkeypatch.setattr(notes, "run_json", fake_run_json)
    note = notes.read_note("x", html=True)
    assert note.body_html == "<div><h2>Weather</h2></div>"
    assert note.body_markdown is None
