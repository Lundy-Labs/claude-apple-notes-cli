# claude-apple-notes-cli

Read and write **Apple Notes** from the terminal and from **Claude** (via MCP),
communicating in **Markdown**. Use it as a memory store so Claude knows more
about you, and to export chats or research into notes.

> ⚠️ macOS only. Apple Notes has no API; this drives Notes.app via AppleScript,
> so it must run on a Mac. See [PLAN.md](./PLAN.md) for the full design.

## Status

Early scaffold. Foundation + module contracts are in place; implementation is in
progress (see [PLAN.md](./PLAN.md) for module ownership).

## Quick start (placeholder — Agent D to complete)

```bash
pip install -e ".[dev]"
notes --help
```

<!-- TODO(Agent D): full setup, macOS Automation permission steps,
     MCP registration (stdio + HTTP), Tailscale remote access, caffeinate. -->
