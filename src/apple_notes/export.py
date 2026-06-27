"""Export helpers: file Claude-generated content (chat transcripts, research)
into Apple Notes.

AGENT OWNERSHIP: Agent D (memory.py + export.py + README).

NOTE: the tool cannot read Claude's own transcript. 'Export a chat' works by
Claude assembling the conversation as Markdown and passing it in here; this
module just formats a header (title, date) and files it in EXPORT_FOLDER.
"""

from __future__ import annotations

from datetime import date

from . import notes
from .models import Note
from .notes import EXPORT_FOLDER


def export_note(
    title: str,
    body_markdown: str,
    kind: str = "chat",
    folder: str = EXPORT_FOLDER,
) -> Note:
    """File ``body_markdown`` as a new note in ``folder``.

    ``kind`` ("chat" | "research") selects a small header template (title + date
    + kind). Returns the created Note.

    The tool cannot read Claude's own transcript: Claude assembles the
    conversation/research as Markdown and passes it in as ``body_markdown``;
    this function only prepends a small header and files it.
    """
    header = (
        f"_{kind.capitalize()} exported by Claude · {date.today().isoformat()}_\n\n"
        f"---\n\n"
    )
    body = header + body_markdown
    # ``title`` becomes the note's name (Notes derives it from the first line).
    return notes.create_note(title, body, folder=folder)
