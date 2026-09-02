"""Typer CLI front-end. Thin wrapper over apple_notes.notes.

AGENT OWNERSHIP: Agent C (cli.py + mcp_server.py).
Commands map 1:1 to the core API. Read commands print Markdown to stdout
(or HTML with --html); write commands accept Markdown via --body or stdin.

Target command surface:
    notes folders
    notes list [--folder NAME] [--limit N]
    notes find --title T [--folder NAME]
    notes search QUERY [--folder NAME] [--title-only]
    notes read NOTE_ID [--html]
    notes write --title T [--folder NAME]   (body from --body or stdin)
    notes append NOTE_ID                     (body from --body or stdin)
    notes delete NOTE_ID
"""

from __future__ import annotations

import sys

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
    except ValueError as exc:
        _fail(str(exc))


def _body_from_option_or_stdin(body: str | None) -> str:
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
    folder: str | None = typer.Option(
        None, "--folder", "-f", help="Folder to list (default: Claude Memory)."
    ),
    limit: int | None = typer.Option(
        None,
        "--limit",
        "-n",
        help="Max notes to return (keeps huge folders like Notes from hanging).",
    ),
) -> None:
    """List notes (title + id) in a folder. Uses bulk id/name reads, not bodies."""
    result = _run(
        lambda: core.list_notes(folder=folder, limit=limit), "listing notes"
    )
    for note in result:
        typer.echo(note.summary())


@app.command("find")
def find_notes(
    title: str = typer.Option(
        ...,
        "--title",
        "-t",
        help="Exact note title (JXA whose({name}); e.g. '02 September').",
    ),
    folder: str | None = typer.Option(
        None, "--folder", "-f", help="Restrict the lookup to this folder."
    ),
) -> None:
    """Fast exact-title lookup. Does not scan note bodies."""
    result = _run(
        lambda: core.find_notes_by_title(title, folder=folder), "finding note"
    )
    if not result:
        _fail(f"no note titled {title!r}")
    for note in result:
        typer.echo(note.summary())


@app.command("search")
def search(
    query: str = typer.Argument(..., help="Text to search for."),
    folder: str | None = typer.Option(
        None, "--folder", "-f", help="Restrict the search to this folder."
    ),
    title_only: bool = typer.Option(
        False,
        "--title-only",
        help="Match titles via whose({name}) only; never call plaintext().",
    ),
) -> None:
    """Search notes, title-first.

    Titles are matched with whose({name}) (fast, library-wide unless --folder).
    Body search is folder-scoped: --folder, or the small default set
    (Claude Memory + Claude Exports). It never plaintext()s the whole library.
    """
    result = _run(
        lambda: core.search_notes(query, folder=folder, title_only=title_only),
        "searching notes",
    )
    for note in result:
        typer.echo(note.summary())


@app.command("read")
def read(
    note_id: str = typer.Argument(..., help="Stable AppleScript note id."),
    html: bool = typer.Option(
        False,
        "--html",
        help="Print raw Notes HTML instead of Markdown (keeps Forever Notes structure).",
    ),
) -> None:
    """Read a note and print its body as Markdown (or HTML with --html)."""
    note = _run(lambda: core.read_note(note_id, html=html), "reading note")
    if html:
        typer.echo(note.body_html or "")
    else:
        typer.echo(note.body_markdown or "")


@app.command("write")
def write(
    title: str = typer.Option(..., "--title", "-t", help="Note title (first line)."),
    folder: str | None = typer.Option(
        None, "--folder", "-f", help="Folder to create the note in (default: Claude Memory)."
    ),
    body: str | None = typer.Option(
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
    body: str | None = typer.Option(
        None, "--body", "-b", help="Markdown to append (omit to read from stdin)."
    ),
) -> None:
    """Append Markdown to an existing note (--body or stdin).

    Implemented as assigning note.body (the only content-mutation Notes
    exposes). That strips Forever Notes Home/Today/Back/Next note links.
    Planner "DD Month" dailies are refused. Test writes only on a throwaway
    note you create, never on a Planner daily page.
    """
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
    body: str | None = typer.Option(
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
