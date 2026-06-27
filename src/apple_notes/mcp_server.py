"""MCP server front-end. Exposes the core API as tools to Claude.

AGENT OWNERSHIP: Agent C (cli.py + mcp_server.py).

Transports:
    * stdio  -> local Claude Code on the Mac.
    * HTTP   -> remote use (e.g. from the iPhone/iPad Claude app over Tailscale),
                guarded by a bearer token read from APPLE_NOTES_MCP_TOKEN.

Tools (map to apple_notes.notes / memory / export):
    notes_list_folders, notes_list, notes_search, notes_read,
    notes_create, notes_append, memory_get, memory_set, export_note

`main()` is the console entry point (see [project.scripts]); it should select
the transport from argv/env (e.g. `--http --host --port`, default stdio).
"""

from __future__ import annotations


def main() -> None:
    """Entry point: start the MCP server (stdio by default, HTTP if requested)."""
    raise NotImplementedError  # Agent C


if __name__ == "__main__":
    main()
