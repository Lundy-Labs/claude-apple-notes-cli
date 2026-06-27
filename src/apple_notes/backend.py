"""AppleScript/JXA bridge. The only module that shells out to ``osascript``.

AGENT OWNERSHIP: Agent B (together with notes.py + scripts/).
macOS-only at runtime; logic can be written anywhere but executes on a Mac.

Notes are addressed by their stable AppleScript ``id`` (x-coredata://...), never
by title (titles are not unique). Bodies cross this boundary as HTML.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

SCRIPTS_DIR = Path(__file__).parent / "scripts"


class BackendError(RuntimeError):
    """osascript failed or Notes returned an error."""


def run_applescript(script: str, args: list[str] | None = None) -> str:
    """Run an AppleScript source string via ``osascript`` and return stdout.

    Raises BackendError on non-zero exit. Implement string escaping carefully —
    note bodies contain arbitrary HTML/quotes.
    """
    raise NotImplementedError  # Agent B


def load_script(name: str) -> str:
    """Load a .applescript template from scripts/ by name (without extension)."""
    raise NotImplementedError  # Agent B
