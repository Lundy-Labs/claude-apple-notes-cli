"""Core API. This is the contract the CLI and MCP server both call, and the
single place that orchestrates the AppleScript backend + Markdown conversion.

AGENT OWNERSHIP: Agent B implements this file (+ backend.py + scripts/).
Other agents import these functions and MUST NOT change their signatures.

Flow:
    read:   backend (HTML) -> convert.html_to_markdown -> Note.body_markdown
    write:  Markdown -> convert.markdown_to_html -> backend (osascript)
"""

from __future__ import annotations

from .models import Folder, Note

# Folders the tool is allowed to touch by default (safety: don't roam the whole
# library). An explicit folder argument overrides this.
DEFAULT_FOLDER = "Claude Memory"
EXPORT_FOLDER = "Claude Exports"


def list_folders() -> list[Folder]:
    """Return all Notes folders across accounts."""
    raise NotImplementedError  # Agent B


def list_notes(folder: str | None = None) -> list[Note]:
    """List notes (title + id only; ``body_markdown`` is None). If ``folder`` is
    None, lists DEFAULT_FOLDER; pass a folder name to scope elsewhere."""
    raise NotImplementedError  # Agent B


def search_notes(query: str, folder: str | None = None) -> list[Note]:
    """Search note titles and bodies for ``query`` (case-insensitive)."""
    raise NotImplementedError  # Agent B


def read_note(note_id: str) -> Note:
    """Fetch a single note with its body converted to Markdown."""
    raise NotImplementedError  # Agent B


def create_note(title: str, body_markdown: str, folder: str = DEFAULT_FOLDER) -> Note:
    """Create a note. ``title`` becomes the first line (Notes derives the note
    name from line 1). Creates ``folder`` if it does not exist."""
    raise NotImplementedError  # Agent B


def append_note(note_id: str, body_markdown: str) -> Note:
    """Append Markdown to an existing note's body."""
    raise NotImplementedError  # Agent B


def delete_note(note_id: str) -> None:
    """Delete a note by id."""
    raise NotImplementedError  # Agent B
