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

from .notes import DEFAULT_FOLDER  # noqa: F401  (memory lives in DEFAULT_FOLDER)

MEMORY_KEYS = ("Profile", "Preferences", "Projects", "Log")


def memory_get(key: str) -> str:
    """Return the Markdown body of memory note ``key`` (one of MEMORY_KEYS).
    Returns '' if the note does not exist yet."""
    raise NotImplementedError  # Agent D


def memory_set(key: str, body_markdown: str, append: bool = False) -> None:
    """Create or replace memory note ``key``. If ``append``, add to it instead
    (useful for 'Log'). Creates the memory folder/note on first use."""
    raise NotImplementedError  # Agent D
