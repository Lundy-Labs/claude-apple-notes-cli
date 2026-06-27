"""AppleScript/JXA bridge. The only module that shells out to ``osascript``.

AGENT OWNERSHIP: Agent B (together with notes.py + scripts/).
macOS-only at runtime; logic can be written anywhere but executes on a Mac.

Notes are addressed by their stable AppleScript ``id`` (x-coredata://...), never
by title (titles are not unique). Bodies cross this boundary as HTML.

Design notes
------------
We drive Apple Notes with **JXA** (JavaScript for Automation), invoked as
``osascript -l JavaScript``. JXA is used over classic AppleScript for two
reasons that matter a lot here:

* It can build and emit **JSON** natively, so structured results (folders,
  notes, dates) cross the process boundary as JSON instead of fragile
  newline/record text that we'd have to hand-parse.
* It reads its arguments from ``run(argv)`` as a plain list of strings, so note
  bodies full of arbitrary HTML and quotes are passed as ``osascript`` argv —
  never interpolated into the script source. No string-escaping hell.

The script *source* is loaded from ``scripts/<name>.applescript`` (the files
contain JXA despite the extension; AppleScript is the umbrella term used in the
plan). The script is fed to ``osascript`` on **stdin** (``osascript - ...``), so
the source itself is never shell-quoted either.

Every script is expected to print a single JSON document to stdout. Scripts that
have nothing to return (e.g. delete) print ``"ok"``. Callers use
:func:`run_json` to get the parsed value back.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any

SCRIPTS_DIR = Path(__file__).parent / "scripts"

# osascript language flag. Our templates are JXA.
_OSA_LANG = "JavaScript"


class BackendError(RuntimeError):
    """osascript failed or Notes returned an error."""


def load_script(name: str) -> str:
    """Load a script template from ``scripts/<name>.applescript``.

    ``name`` is given without the extension, e.g. ``load_script("list_folders")``.
    """
    path = SCRIPTS_DIR / f"{name}.applescript"
    try:
        return path.read_text(encoding="utf-8")
    except FileNotFoundError as exc:  # pragma: no cover - trivial
        raise BackendError(f"script template not found: {path}") from exc


def run_applescript(script: str, args: list[str] | None = None) -> str:
    """Run a JXA/AppleScript *source string* via ``osascript`` and return stdout.

    The source is passed on **stdin** (``osascript -l JavaScript -``) so it is
    never shell-escaped. ``args`` are forwarded verbatim as positional process
    arguments and surface inside the script as ``run(argv)`` — this is how note
    bodies (arbitrary HTML/quotes) are passed safely without interpolation.

    Returns ``stdout`` stripped of a single trailing newline. Raises
    :class:`BackendError` on a non-zero exit, including osascript's stderr.
    """
    argv = ["osascript", "-l", _OSA_LANG, "-"]
    if args:
        # Reject Nones early; osascript argv must be strings.
        argv.extend(str(a) for a in args)

    try:
        proc = subprocess.run(
            argv,
            input=script,
            capture_output=True,
            text=True,
            check=False,
        )
    except FileNotFoundError as exc:
        # osascript itself is missing -> not on macOS / not on PATH.
        raise BackendError(
            "osascript not found; Apple Notes access requires macOS"
        ) from exc

    if proc.returncode != 0:
        stderr = (proc.stderr or "").strip()
        detail = stderr or f"osascript exited with status {proc.returncode}"
        raise BackendError(detail)

    out = proc.stdout
    # osascript appends a trailing newline to printed output; drop exactly one.
    if out.endswith("\n"):
        out = out[:-1]
    return out


def run_json(name: str, args: list[str] | None = None) -> Any:
    """Load template ``name``, run it with ``args`` and parse its JSON stdout.

    Convenience wrapper used throughout :mod:`apple_notes.notes`. Scripts always
    emit a single JSON value (object, array, or string). Raises
    :class:`BackendError` if the output is not valid JSON.
    """
    raw = run_applescript(load_script(name), args)
    if raw == "":
        # Treat empty output as a backend error so callers don't silently get None.
        raise BackendError(f"script {name!r} produced no output")
    try:
        return json.loads(raw)
    except json.JSONDecodeError as exc:
        raise BackendError(
            f"script {name!r} returned non-JSON output: {raw[:200]!r}"
        ) from exc
