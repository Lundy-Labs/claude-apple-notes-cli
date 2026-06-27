"""claude-apple-notes-cli: read/write Apple Notes from the terminal and from Claude.

Public surface lives in :mod:`apple_notes.notes` (the core API that the CLI and
the MCP server both call). Everything communicates in Markdown; HTML is an
internal detail of Apple Notes handled in :mod:`apple_notes.convert`.
"""

__version__ = "0.1.0"
