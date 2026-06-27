"""Memory conventions: a dedicated 'Claude Memory' folder with stable-named
notes Claude reads to learn about the user instead of scanning the whole library.

AGENT OWNERSHIP: Agent D (memory.py + export.py + README).

Convention notes in DEFAULT_FOLDER:
    Profile      - who the user is, role, context
    Preferences  - how they like Claude to work
    Projects     - what they're building
    Log          - append-only running notes Claude adds over time
"""

from __future__ import annotations

from . import notes
from .models import Note
from .notes import DEFAULT_FOLDER

MEMORY_KEYS = ("Profile", "Preferences", "Projects", "Log")


def _find_note(key: str) -> Note | None:
    """Locate the memory note titled ``key`` in DEFAULT_FOLDER, or None.

    Titles in Apple Notes are not unique, so we match exactly (case-sensitively)
    on the first note whose title equals ``key``. We prefer ``list_notes`` (a
    cheap title+id listing) and fall back to ``search_notes``.
    """
    candidates = notes.list_notes(folder=DEFAULT_FOLDER)
    for note in candidates:
        if note.title == key:
            return note
    # Fall back to a search in case listing is paginated/scoped differently.
    for note in notes.search_notes(key, folder=DEFAULT_FOLDER):
        if note.title == key:
            return note
    return None


def memory_get(key: str) -> str:
    """Return the Markdown body of memory note ``key`` (one of MEMORY_KEYS).
    Returns '' if the note does not exist yet."""
    note = _find_note(key)
    if note is None:
        return ""
    # list/search return title+id only; fetch the full body.
    full = notes.read_note(note.id)
    return full.body_markdown or ""


def memory_set(key: str, body_markdown: str, append: bool = False) -> None:
    """Create or replace memory note ``key``. If ``append``, add to it instead
    (useful for 'Log'). Creates the memory folder/note on first use."""
    existing = _find_note(key)

    if append:
        if existing is None:
            # Nothing to append to yet — create it (title from first line).
            notes.create_note(key, body_markdown, folder=DEFAULT_FOLDER)
        else:
            notes.append_note(existing.id, body_markdown)
        return

    # Replace semantics: drop any existing note, then create fresh. Notes are
    # addressed by stable id, so this is safe even with duplicate titles.
    if existing is not None:
        notes.delete_note(existing.id)
    notes.create_note(key, body_markdown, folder=DEFAULT_FOLDER)
