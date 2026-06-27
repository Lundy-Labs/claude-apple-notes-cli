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

import typer

app = typer.Typer(help="Read/write Apple Notes in Markdown.", no_args_is_help=True)


@app.callback()
def _root() -> None:
    """Apple Notes CLI."""


# TODO(Agent C): implement commands wired to apple_notes.notes.*


if __name__ == "__main__":
    app()
