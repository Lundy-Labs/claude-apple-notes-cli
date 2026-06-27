"""Typer CLI front-end. Thin wrapper over apple_notes.notes.

AGENT OWNERSHIP: Agent C (cli.py + mcp_server.py).
Commands map 1:1 to the core API. Read commands print Markdown to stdout;
write commands accept Markdown via --body or stdin.

Target command surface:
    notes folders
    notes list [--folder NAME]
    notes search QUERY [--folder NAME]
    notes read NOTE_ID
    notes write --title T [--folder NAME]   (body from --body or stdin)
    notes append NOTE_ID                     (body from --body or stdin)
    notes delete NOTE_ID
"""

from __future__ import annotations

import sys
from typing import Optional

import typer

from . import memory as mem
from . import notes as core
from .backend import BackendError

app = typer.Typer(help="Read/write Apple Notes in Markdown.", no_args_is_help=True)


@app.callback()
def _root() -> None:
    """Apple Notes CLI — read and write Apple Notes in Markdown."""


def _fail(message: str) -> None:
    """Print a friendly error to stderr and exit non-zero."""
    typer.secho(f"error: {message}", fg=typer.colors.RED, err=True)
    raise typer.Exit(code=1)


def _run(action, what: str):
    """Call a core function, translating expected errors into friendly output."""
    try:
        return action()
    except NotImplementedError:
        _fail(
            f"{what} is not available yet: the Apple Notes backend is unimplemented "
            "(this command runs only on macOS)."
        )
    except BackendError as exc:
        _fail(f"{what} failed: {exc}")


def _body_from_option_or_stdin(body: Optional[str]) -> str:
    """Resolve a Markdown body from --body, else read all of stdin.

    Supports `echo '# x' | notes write --title X`.
    """
    if body is not None:
        return body
    if sys.stdin is None or sys.stdin.isatty():
        _fail("no body provided: pass --body TEXT or pipe Markdown via stdin.")
    return sys.stdin.read()


@app.command("folders")
def folders() -> None:
    """List all Notes folders."""
    result = _run(core.list_folders, "listing folders")
    for folder in result:
        typer.echo(f"[{folder.account}] {folder.name}  ({folder.id})")


@app.command("list")
def list_notes(
    folder: Optional[str] = typer.Option(
        None, "--folder", "-f", help="Folder to list (default: Claude Memory)."
    ),
) -> None:
    """List notes (title + id) in a folder."""
    result = _run(lambda: core.list_notes(folder=folder), "listing notes")
    for note in result:
        typer.echo(note.summary())


@app.command("search")
def search(
    query: str = typer.Argument(..., help="Text to search for (case-insensitive)."),
    folder: Optional[str] = typer.Option(
        None, "--folder", "-f", help="Restrict the search to this folder."
    ),
) -> None:
    """Search note titles and bodies."""
    result = _run(
        lambda: core.search_notes(query, folder=folder), "searching notes"
    )
    for note in result:
        typer.echo(note.summary())


@app.command("read")
def read(
    note_id: str = typer.Argument(..., help="Stable AppleScript note id."),
) -> None:
    """Read a note and print its body as Markdown."""
    note = _run(lambda: core.read_note(note_id), "reading note")
    typer.echo(note.body_markdown or "")


@app.command("write")
def write(
    title: str = typer.Option(..., "--title", "-t", help="Note title (first line)."),
    folder: Optional[str] = typer.Option(
        None, "--folder", "-f", help="Folder to create the note in (default: Claude Memory)."
    ),
    body: Optional[str] = typer.Option(
        None, "--body", "-b", help="Markdown body (omit to read from stdin)."
    ),
) -> None:
    """Create a note from Markdown (--body or stdin)."""
    body_markdown = _body_from_option_or_stdin(body)
    kwargs = {"folder": folder} if folder is not None else {}
    note = _run(
        lambda: core.create_note(title, body_markdown, **kwargs), "creating note"
    )
    typer.echo(f"created: {note.summary()}")


@app.command("append")
def append(
    note_id: str = typer.Argument(..., help="Stable AppleScript note id."),
    body: Optional[str] = typer.Option(
        None, "--body", "-b", help="Markdown to append (omit to read from stdin)."
    ),
) -> None:
    """Append Markdown to an existing note (--body or stdin)."""
    body_markdown = _body_from_option_or_stdin(body)
    note = _run(
        lambda: core.append_note(note_id, body_markdown), "appending to note"
    )
    typer.echo(f"appended: {note.summary()}")


@app.command("delete")
def delete(
    note_id: str = typer.Argument(..., help="Stable AppleScript note id."),
    yes: bool = typer.Option(
        False, "--yes", "-y", help="Skip the confirmation prompt."
    ),
) -> None:
    """Delete a note by id."""
    if not yes:
        typer.confirm(f"Delete note {note_id}?", abort=True)
    _run(lambda: core.delete_note(note_id), "deleting note")
    typer.echo(f"deleted: {note_id}")


# --- memory subcommands ----------------------------------------------------

memory_app = typer.Typer(
    help="Read/write Claude memory notes (in the 'Claude Memory' folder).",
    no_args_is_help=True,
)
app.add_typer(memory_app, name="memory")


@memory_app.command("core")
def memory_core() -> None:
    """Print the lightweight memory core (curated 'Core' note + pointers).

    Designed for a Claude Code SessionStart hook: small, flat-cost, and
    hook-safe — it never exits non-zero on a backend hiccup, so a transient
    Notes error can't block a session from starting.
    """
    try:
        block = mem.memory_core()
    except NotImplementedError:
        _fail("memory core is not available yet (runs only on macOS).")
    except BackendError as exc:
        typer.secho(
            f"warning: memory core unavailable: {exc}",
            fg=typer.colors.YELLOW,
            err=True,
        )
        raise typer.Exit(code=0)
    if block:
        typer.echo(block, nl=False)


@memory_app.command("get")
def memory_get(
    key: str = typer.Argument(..., help="Memory note name, e.g. Profile."),
) -> None:
    """Print a memory note's Markdown body (empty if it doesn't exist yet)."""
    body = _run(lambda: mem.memory_get(key), "reading memory")
    typer.echo(body)


@memory_app.command("set")
def memory_set(
    key: str = typer.Argument(..., help="Memory note name, e.g. Profile."),
    body: Optional[str] = typer.Option(
        None, "--body", "-b", help="Markdown content (omit to read from stdin)."
    ),
    append: bool = typer.Option(
        False, "--append", "-a", help="Append instead of replacing the note."
    ),
) -> None:
    """Create/replace (or --append) a memory note from --body or stdin."""
    body_markdown = _body_from_option_or_stdin(body)
    _run(
        lambda: mem.memory_set(key, body_markdown, append=append),
        "writing memory",
    )
    typer.echo(f"memory '{key}' {'appended' if append else 'set'}.")


if __name__ == "__main__":
    app()
