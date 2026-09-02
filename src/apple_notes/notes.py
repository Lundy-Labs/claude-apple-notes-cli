"""Core API. This is the contract the CLI and MCP server both call, and the
single place that orchestrates the AppleScript backend + Markdown conversion.

AGENT OWNERSHIP: Agent B implements this file (+ backend.py + scripts/).
Other agents import these functions and MUST NOT change their signatures
except to add optional keyword-only arguments.

Flow:
    read:   backend (HTML) -> convert.html_to_markdown -> Note.body_markdown
            (or skip conversion when html=True and return Note.body_html)
    write:  Markdown -> convert.markdown_to_html -> backend (osascript)

There is no Forever Notes-safe append: Notes.sdef only mutates content by
assigning ``note.body``, which re-serializes attributed text and strips
note-to-note links that ``body()`` does not export. ``append_note`` still
assigns ``body`` (for simple notes) and refuses Planner "DD Month" dailies.

"""

from __future__ import annotations

import re
from datetime import datetime

from . import convert
from .backend import run_json
from .models import Folder, Note

# Folders the tool is allowed to touch by default (safety: don't roam the whole
# library). An explicit folder argument overrides this.
DEFAULT_FOLDER = "Claude Memory"
EXPORT_FOLDER = "Claude Exports"

# Body search (plaintext) is never allowed across the whole library. When the
# caller omits --folder, scan only this small set. Title search uses whose()
# and may be library-wide.
BODY_SEARCH_DEFAULT_FOLDERS = (DEFAULT_FOLDER, EXPORT_FOLDER)

# Forever Notes daily pages live here, titled "DD Month". Any note.body
# assignment (append-by-rewrite, markdown round-trip, set_note_body) strips
# Home/Today/Back/Next note links that body() does not export.
PLANNER_FOLDER = "Planner"
_MONTHS = (
    "January",
    "February",
    "March",
    "April",
    "May",
    "June",
    "July",
    "August",
    "September",
    "October",
    "November",
    "December",
)
_DAILY_TITLE = re.compile(
    r"^(0[1-9]|[12]\d|3[01])\s+(" + "|".join(_MONTHS) + r")$",
    re.IGNORECASE,
)

_BODY_FOLDER_SEP = "\x1f"


def is_forever_notes_daily(title: str | None, folder: str | None) -> bool:
    """True for Planner notes titled like ``02 September``."""
    if (folder or "").strip() != PLANNER_FOLDER:
        return False
    return bool(_DAILY_TITLE.match((title or "").strip()))


# --------------------------------------------------------------------------- #
# parsing helpers
# --------------------------------------------------------------------------- #
def _parse_dt(value: str | None) -> datetime | None:
    """Parse an ISO-8601 string (as emitted by JXA ``Date.toISOString()``) into a
    naive/aware ``datetime``. Returns None for missing/unparseable values."""
    if not value:
        return None
    text = str(value)
    # JXA emits e.g. "2026-06-27T17:04:05.123Z"; Python's fromisoformat handles
    # the offset form but historically not a trailing "Z", so normalize it.
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        return datetime.fromisoformat(text)
    except ValueError:
        return None


def _note_from_record(
    rec: dict,
    *,
    body_markdown: str | None = None,
    body_html: str | None = None,
) -> Note:
    """Build a :class:`Note` from a backend JSON record. ``name`` is the note
    title in Notes; ``body_markdown`` / ``body_html`` are supplied only for
    full reads."""
    return Note(
        id=rec["id"],
        title=rec.get("name") or "",
        folder=rec.get("folder"),
        body_markdown=body_markdown,
        body_html=body_html,
        created=_parse_dt(rec.get("created")),
        modified=_parse_dt(rec.get("modified")),
    )


def _split_title_body(body_markdown: str) -> tuple[str | None, str]:
    """Split a Markdown blob into (title, remainder).

    Used when the caller hands us a full note body and we want the first line as
    the note title. Strips a leading Markdown heading marker (``# ``) from the
    title line so the note name is clean.
    """
    body_markdown = body_markdown or ""
    parts = body_markdown.split("\n", 1)
    first = parts[0].strip()
    rest = parts[1] if len(parts) > 1 else ""
    title = first.lstrip("#").strip() if first else None
    return (title or None), rest


# --------------------------------------------------------------------------- #
# read path
# --------------------------------------------------------------------------- #
def list_folders() -> list[Folder]:
    """Return all Notes folders across accounts."""
    records = run_json("list_folders")
    return [
        Folder(
            id=rec["id"],
            name=rec.get("name") or "",
            account=rec.get("account") or "iCloud",
        )
        for rec in records
    ]


def list_notes(folder: str | None = None, *, limit: int | None = None) -> list[Note]:
    """List notes (title + id only; ``body_markdown`` is None). If ``folder`` is
    None, lists DEFAULT_FOLDER; pass a folder name to scope elsewhere.

    ``limit`` caps how many notes are returned (0/None = no cap). Listing uses
    bulk JXA specifier reads, not per-note property access.
    """
    target = folder if folder is not None else DEFAULT_FOLDER
    limit_s = str(limit) if limit else "0"
    records = run_json("list_notes", [target, limit_s])
    return [_note_from_record(rec) for rec in records]


def find_notes_by_title(title: str, folder: str | None = None) -> list[Note]:
    """Exact title lookup via JXA ``whose({name: title})``.

    This is the fast path for Forever Notes daily pages ("02 September"). It
    does not scan bodies and does not walk folders note-by-note.
    """
    records = run_json("find_by_title", [title, folder or ""])
    return [_note_from_record(rec) for rec in records]


def search_notes(
    query: str,
    folder: str | None = None,
    *,
    title_only: bool = False,
) -> list[Note]:
    """Search notes for ``query``.

    Always title-first via ``whose({name})``. Body search (``plaintext``) is
    folder-scoped: ``folder`` if given, otherwise :data:`BODY_SEARCH_DEFAULT_FOLDERS`.
    Pass ``title_only=True`` to skip bodies entirely (fast on a large library).
    """
    body_folders = ""
    if not title_only:
        if folder:
            body_folders = folder
        else:
            body_folders = _BODY_FOLDER_SEP.join(BODY_SEARCH_DEFAULT_FOLDERS)
    args = [
        query,
        folder if folder is not None else "",
        "1" if title_only else "0",
        body_folders,
    ]
    records = run_json("search_notes", args)
    return [_note_from_record(rec) for rec in records]


def read_note(note_id: str, *, html: bool = False) -> Note:
    """Fetch a single note by id via ``whose({id})`` / ``byId``.

    Default: convert the HTML body to Markdown. With ``html=True``, skip the
    converter (Forever Notes / rich pages) and populate ``body_html`` instead.
    """
    rec = run_json("read_note", [note_id])
    raw_html = rec.get("body") or ""
    if html:
        return _note_from_record(rec, body_html=raw_html)
    return _note_from_record(rec, body_markdown=convert.html_to_markdown(raw_html))


# --------------------------------------------------------------------------- #
# write path
# --------------------------------------------------------------------------- #
def create_note(title: str, body_markdown: str, folder: str = DEFAULT_FOLDER) -> Note:
    """Create a note. ``title`` becomes the first line (Notes derives the note
    name from line 1). Creates ``folder`` if it does not exist."""
    # markdown_to_html renders `title` as the first line so Notes uses it as the
    # note name; the body follows it.
    html = convert.markdown_to_html(body_markdown or "", title=title)
    rec = run_json("create_note", [folder, html])
    # Return a fully-populated Note, including the Markdown we just wrote.
    body = body_markdown or ""
    return _note_from_record(rec, body_markdown=body)


def append_note(note_id: str, body_markdown: str) -> Note:
    """Append Markdown to an existing note by assigning ``note.body``.

    Notes.app has no scripting command that inserts at the end of existing
    attributed text. This concatenates HTML onto ``body`` and writes it back,
    which **strips Forever Notes Home/Today/Back/Next note links**. Planner
    daily pages are refused. Use only on simple notes, or on a throwaway note
    you created for testing.
    """
    fragment_html = convert.markdown_to_html(body_markdown or "")
    run_json("append_note", [note_id, fragment_html])
    # Re-read so the returned Note reflects the full, current body as Markdown.
    return read_note(note_id)


def delete_note(note_id: str) -> None:
    """Delete a note by id."""
    run_json("delete_note", [note_id])
