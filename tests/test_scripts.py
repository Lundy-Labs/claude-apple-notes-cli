"""Static checks on the JXA templates that actually run."""

from __future__ import annotations

from pathlib import Path

from apple_notes.backend import load_script

SCRIPTS = Path(__file__).resolve().parents[1] / "src" / "apple_notes" / "scripts"


def _raw(name: str) -> str:
    return (SCRIPTS / f"{name}.applescript").read_text(encoding="utf-8")


def test_no_update_note_script():
    assert not (SCRIPTS / "update_note.applescript").exists()


def test_find_by_title_uses_whose_name_not_body_scan():
    raw = _raw("find_by_title")
    src = load_script("find_by_title")
    assert "whose({name: title})" in raw
    assert "function run" in raw
    assert "note.plaintext()" not in raw
    assert ".plaintext()" not in raw
    assert "findNoteById" not in raw
    # Concatenated lib must provide whose helpers, not a nested note scan.
    assert "function findNoteById" in src
    assert "Notes.notes.whose({id:" in src


def test_read_append_delete_use_whose_id_or_byid():
    for name in ("read_note", "append_note", "delete_note"):
        raw = _raw(name)
        src = load_script(name)
        assert "findNoteById" in raw
        assert "note.plaintext()" not in raw
        assert ".plaintext()" not in raw
        assert "notes[n].id()" not in raw
        assert "whose({id:" in src
        assert "byId" in src


def test_append_refuses_planner_dailies():
    """Safety rail: assigning body on a Planner DD Month note strips nav links."""
    raw = _raw("append_note")
    assert "note.body =" in raw
    assert "Planner" in raw
    assert "strips Forever Notes nav links" in raw


def test_list_uses_bulk_specifier_not_per_note_loop():
    raw = _raw("list_notes")
    assert "recordsFromSpecifier" in raw
    assert "note.plaintext()" not in raw
    assert ".plaintext()" not in raw
    assert "notes[n].name()" not in raw
    assert "folder.notes" in raw


def test_search_is_title_first_and_body_is_folder_scoped():
    raw = _raw("search_notes")
    assert "whose({name:" in raw
    assert "titleOnly" in raw
    assert "foldersToScan" in raw
    # The operation script must not walk every account calling plaintext.
    assert "for (let a = 0; a < accounts.length" not in raw
    assert "Never the library" in raw
    # plaintext() allowed only as last resort inside one resolved folder.
    assert "folder.notes.whose({plaintext:" in raw
