"""MCP server front-end. Exposes the core API as tools to Claude.

AGENT OWNERSHIP: Agent C (cli.py + mcp_server.py).

Transports:
    * stdio  -> local Claude Code on the Mac.
    * HTTP   -> remote use (e.g. from the iPhone/iPad Claude app over Tailscale),
                guarded by a bearer token read from APPLE_NOTES_MCP_TOKEN.

Tools (map to apple_notes.notes / memory / export):
    notes_list_folders, notes_list, notes_search, notes_read,
    notes_create, notes_append, memory_get, memory_set, export_note

Usage (see [project.scripts] -> apple-notes-mcp):
    apple-notes-mcp                      # stdio transport (default; local Claude Code)
    apple-notes-mcp --http               # HTTP/SSE transport on 127.0.0.1:8765
    apple-notes-mcp --http --host 0.0.0.0 --port 9000

HTTP transport auth:
    The HTTP/SSE transport is guarded by a bearer token. Set the shared secret in
    the environment as APPLE_NOTES_MCP_TOKEN; clients must send
    ``Authorization: Bearer <token>``. Requests without the matching token are
    rejected with 401. The token is required to *start* the HTTP transport — the
    server refuses to listen unprotected.

Environment:
    APPLE_NOTES_MCP_TOKEN   bearer token for the HTTP transport (required for --http)
    APPLE_NOTES_MCP_HTTP    if truthy ("1"/"true"/"yes"), default to HTTP transport
    APPLE_NOTES_MCP_HOST    default host for HTTP transport (default 127.0.0.1)
    APPLE_NOTES_MCP_PORT    default port for HTTP transport (default 8765)
"""

from __future__ import annotations

import argparse
import os
import sys

from mcp.server.fastmcp import FastMCP

from . import export as export_mod
from . import memory as memory_mod
from . import notes as core

DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8765
TOKEN_ENV = "APPLE_NOTES_MCP_TOKEN"

mcp = FastMCP(
    "apple-notes",
    instructions=(
        "Read and write Apple Notes in Markdown. By default tools are scoped to "
        "the 'Claude Memory' folder; pass an explicit folder to reach elsewhere. "
        "Notes are addressed by their stable id, never by title."
    ),
)


# --- Tools -----------------------------------------------------------------
# Each tool returns plain data (dicts / Markdown strings); FastMCP derives the
# JSON input schema from the type annotations below.


@mcp.tool(name="notes_list_folders")
def notes_list_folders() -> list[dict]:
    """List all Apple Notes folders across accounts."""
    return [
        {"id": f.id, "name": f.name, "account": f.account}
        for f in core.list_folders()
    ]


@mcp.tool(name="notes_list")
def notes_list(folder: str | None = None) -> list[dict]:
    """List notes (title + id only) in a folder.

    folder: folder name to list; omit to use the default 'Claude Memory' folder.
    """
    return [
        {"id": n.id, "title": n.title, "folder": n.folder}
        for n in core.list_notes(folder=folder)
    ]


@mcp.tool(name="notes_search")
def notes_search(query: str, folder: str | None = None) -> list[dict]:
    """Search note titles and bodies (case-insensitive).

    query: text to search for.
    folder: optional folder to restrict the search to.
    """
    return [
        {"id": n.id, "title": n.title, "folder": n.folder}
        for n in core.search_notes(query, folder=folder)
    ]


@mcp.tool(name="notes_read")
def notes_read(note_id: str) -> str:
    """Read a note and return its body as Markdown.

    note_id: stable AppleScript note id.
    """
    note = core.read_note(note_id)
    return note.body_markdown or ""


@mcp.tool(name="notes_create")
def notes_create(
    title: str, body_markdown: str, folder: str | None = None
) -> dict:
    """Create a note from a Markdown body.

    title: note title (becomes the first line).
    body_markdown: note body in Markdown.
    folder: folder to create the note in; omit for the default 'Claude Memory'.
    """
    kwargs = {"folder": folder} if folder is not None else {}
    note = core.create_note(title, body_markdown, **kwargs)
    return {"id": note.id, "title": note.title, "folder": note.folder}


@mcp.tool(name="notes_append")
def notes_append(note_id: str, body_markdown: str) -> dict:
    """Append a Markdown body to an existing note.

    note_id: stable AppleScript note id.
    body_markdown: Markdown to append.
    """
    note = core.append_note(note_id, body_markdown)
    return {"id": note.id, "title": note.title, "folder": note.folder}


@mcp.tool(name="memory_get")
def memory_get(key: str) -> str:
    """Read a memory note's Markdown body (returns '' if it does not exist yet).

    key: one of Profile, Preferences, Projects, Log.
    """
    return memory_mod.memory_get(key)


@mcp.tool(name="memory_set")
def memory_set(key: str, body_markdown: str, append: bool = False) -> str:
    """Create or replace a memory note (or append to it).

    key: one of Profile, Preferences, Projects, Log.
    body_markdown: Markdown content.
    append: if true, add to the note instead of replacing it (useful for Log).
    """
    memory_mod.memory_set(key, body_markdown, append=append)
    return f"memory '{key}' {'appended' if append else 'set'}."


@mcp.tool(name="memory_core")
def memory_core() -> str:
    """Return the lightweight memory 'core': a curated summary plus a pointer
    list of the other memory notes. Cheap orientation — pull individual notes
    with memory_get only when a topic is actually relevant."""
    return memory_mod.memory_core()


@mcp.tool(name="export_note")
def export_note(
    title: str, body_markdown: str, kind: str = "chat"
) -> dict:
    """File Claude-generated Markdown as a note in the 'Claude Exports' folder.

    title: note title.
    body_markdown: content to file (e.g. a chat transcript or research).
    kind: 'chat' or 'research' (selects a small header template).
    """
    note = export_mod.export_note(title, body_markdown, kind=kind)
    return {"id": note.id, "title": note.title, "folder": note.folder}


# --- HTTP bearer-token auth ------------------------------------------------


def _build_token_middleware(token: str):
    """Return a Starlette middleware class that enforces a bearer token.

    Health/liveness style requests still need the token; anything without a
    matching ``Authorization: Bearer <token>`` header gets a 401.
    """
    from starlette.middleware.base import BaseHTTPMiddleware
    from starlette.responses import JSONResponse

    expected = f"Bearer {token}"

    class BearerTokenMiddleware(BaseHTTPMiddleware):
        async def dispatch(self, request, call_next):
            header = request.headers.get("authorization", "")
            # Constant-time-ish comparison; tokens are short shared secrets.
            if not header or not _secure_eq(header, expected):
                return JSONResponse(
                    {"error": "unauthorized: missing or invalid bearer token"},
                    status_code=401,
                )
            return await call_next(request)

    return BearerTokenMiddleware


def _secure_eq(a: str, b: str) -> bool:
    import hmac

    return hmac.compare_digest(a.encode("utf-8"), b.encode("utf-8"))


def _run_http(host: str, port: int, token: str) -> None:
    """Run the SSE/HTTP transport behind bearer-token middleware."""
    import uvicorn
    from starlette.middleware import Middleware

    mcp.settings.host = host
    mcp.settings.port = port

    # Build the SSE Starlette app and wrap every route with token auth.
    app = mcp.sse_app()
    app.user_middleware.insert(0, Middleware(_build_token_middleware(token)))
    app.middleware_stack = app.build_middleware_stack()

    uvicorn.run(app, host=host, port=port, log_level=mcp.settings.log_level.lower())


# --- Entry point -----------------------------------------------------------


def _truthy(value: str | None) -> bool:
    return (value or "").strip().lower() in {"1", "true", "yes", "on"}


def _parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="apple-notes-mcp",
        description=(
            "Apple Notes MCP server. Default transport is stdio (local Claude "
            "Code). Use --http for the HTTP/SSE transport (remote / iPhone via "
            "Tailscale), guarded by the APPLE_NOTES_MCP_TOKEN bearer token."
        ),
    )
    parser.add_argument(
        "--http",
        action="store_true",
        default=_truthy(os.environ.get("APPLE_NOTES_MCP_HTTP")),
        help="Run the HTTP/SSE transport instead of stdio (requires "
        f"{TOKEN_ENV}).",
    )
    parser.add_argument(
        "--host",
        default=os.environ.get("APPLE_NOTES_MCP_HOST", DEFAULT_HOST),
        help=f"Host for the HTTP transport (default {DEFAULT_HOST}).",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=int(os.environ.get("APPLE_NOTES_MCP_PORT", DEFAULT_PORT)),
        help=f"Port for the HTTP transport (default {DEFAULT_PORT}).",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    """Entry point: start the MCP server (stdio by default, HTTP if requested).

    stdio (default) is used by local Claude Code. ``--http`` starts the HTTP/SSE
    transport on ``--host``/``--port`` (defaults 127.0.0.1:8765), protected by a
    bearer token from the APPLE_NOTES_MCP_TOKEN environment variable.
    """
    args = _parse_args(sys.argv[1:] if argv is None else argv)

    if args.http:
        token = os.environ.get(TOKEN_ENV, "").strip()
        if not token:
            print(
                f"refusing to start HTTP transport without a token: set {TOKEN_ENV} "
                "to a shared secret (clients send it as 'Authorization: Bearer ...').",
                file=sys.stderr,
            )
            raise SystemExit(2)
        _run_http(args.host, args.port, token)
    else:
        mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
