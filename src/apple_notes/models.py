"""Shared data models. Stable contract for all modules — do not change field
names without updating every consumer (notes, cli, mcp_server, memory, export)."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


@dataclass(frozen=True)
class Folder:
    """An Apple Notes folder."""

    id: str           # stable AppleScript id, e.g. "x-coredata://.../ICFolder/p123"
    name: str         # display name, e.g. "Claude Memory"
    account: str = "iCloud"  # account the folder lives in


@dataclass
class Note:
    """An Apple Notes note.

    ``body_markdown`` is ``None`` for lightweight list/search results (title +
    id only) and populated by :func:`apple_notes.notes.read_note`. Bodies are
    always exchanged as Markdown at this layer; HTML never escapes the backend.
    """

    id: str                        # stable AppleScript id (canonical handle)
    title: str                     # first line of the note
    folder: str | None = None      # folder display name
    body_markdown: str | None = None
    created: datetime | None = None
    modified: datetime | None = None

    def summary(self) -> str:
        """One-line representation for list output."""
        loc = f"[{self.folder}] " if self.folder else ""
        return f"{loc}{self.title}  ({self.id})"
