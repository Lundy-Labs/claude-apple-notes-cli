# claude-apple-notes-cli

Read and write **Apple Notes** from the terminal and from **Claude** (via MCP),
communicating in **Markdown**. Use it as a **memory** store so Claude learns
about you across sessions, and to **export** chats or research into notes.

> ⚠️ **macOS only.** Apple Notes has no public/cloud API. This tool drives the
> local **Notes.app via AppleScript** (`osascript`), so it must run on a Mac
> (your own Mac, or a Mac mini left running). It cannot run on iOS or on
> serverless hosts — there is no API to call. See [PLAN.md](./PLAN.md) for the
> full design and module ownership.

## What it is

- A shared core (`apple_notes.notes`) over an AppleScript backend, with two
  front-ends:
  - a **Typer CLI** (`notes`) for the terminal, and
  - an **MCP server** (`apple-notes-mcp`) that exposes the same operations as
    tools to Claude.
- **Markdown is the wire format.** Apple Notes stores HTML internally;
  conversion happens at the boundary (`convert.py`). Bodies are always exchanged
  as Markdown at the API/CLI/MCP layer.
- Pinned by default to two folders so it won't roam your whole library:
  **`Claude Memory`** and **`Claude Exports`**. An explicit `--folder` overrides.

## Requirements

- **macOS** with the **Notes** app and an iCloud (or local) account.
- **Python 3.11+**.

## Install

```bash
python3 -m venv .venv
.venv/bin/pip install -e ".[dev]"
```

This installs the package editable, with dev tools (pytest, ruff, mypy). It
provides two console scripts:

- `notes` — the CLI (`apple_notes.cli:app`)
- `apple-notes-mcp` — the MCP server (`apple_notes.mcp_server:main`)

Activate the venv (`source .venv/bin/activate`) or call the binaries directly
from `.venv/bin/`.

## macOS Automation permission

The first time the tool talks to Notes, macOS shows a prompt:

> "Terminal" (or your MCP host) wants access to control "Notes".

Click **OK / Allow**. This is the standard AppleScript automation consent.

If you missed the prompt or denied it, grant it manually:

1. Open **System Settings → Privacy & Security → Automation**.
2. Find the app that runs this tool (e.g. **Terminal**, **iTerm**, or the
   process hosting the MCP server).
3. Enable the **Notes** checkbox under it.

If a binary doesn't appear in the list, run a command once (e.g. `notes
folders`) to trigger the prompt, then re-check the list. You may also need
**Accessibility** consent for the same app in some macOS versions.

## CLI usage

```bash
notes --help

# Browse
notes folders                      # list all Notes folders
notes list                         # list notes in "Claude Memory" (default)
notes list --folder "Notes"        # scope to another folder
notes search "tailscale"           # search titles + bodies
notes read NOTE_ID                 # print a note's Markdown body

# Write (body via --body or piped on stdin)
notes write --title "Idea" --body "## Idea\n\nText here"
echo "## Idea" | notes write --title "Idea"
notes append NOTE_ID --body "More text"
notes delete NOTE_ID
```

Notes are addressed by their stable AppleScript **id** (shown in `list`/`search`
output), never by title — titles are not unique.

## MCP registration

The MCP server exposes the core operations plus memory/export as tools:
`notes_list_folders`, `notes_list`, `notes_search`, `notes_read`,
`notes_create`, `notes_append`, `memory_get`, `memory_set`, `export_note`.

### Local (stdio) — Claude Code on the Mac

Register the stdio server with Claude Code:

```bash
claude mcp add apple-notes -- apple-notes-mcp
```

or add it to your MCP config manually:

```json
{
  "mcpServers": {
    "apple-notes": {
      "command": "apple-notes-mcp"
    }
  }
}
```

(Use the absolute path `.../.venv/bin/apple-notes-mcp` if the binary isn't on
the host's `PATH`.)

### Remote / iPhone (HTTP + bearer token over Tailscale)

Apple Notes only exists on the Mac, but you can reach it from the iPhone/iPad
Claude app. iCloud keeps the notes themselves in sync; the **server still runs
on the Mac** and the phone talks to it over the network.

1. **Set a bearer token** the server requires on every HTTP request:

   ```bash
   export APPLE_NOTES_MCP_TOKEN="$(openssl rand -hex 32)"
   ```

2. **Run the server in HTTP mode** on the Mac:

   ```bash
   apple-notes-mcp --http --host 0.0.0.0 --port 8765
   ```

3. **Reach it over [Tailscale](https://tailscale.com/).** Install Tailscale on
   both the Mac and the phone, joined to the same tailnet. Use the Mac's
   Tailscale address (e.g. `http://mac-mini.tailnet-name.ts.net:8765`) as the
   MCP server URL in the Claude app, with the **Authorization: Bearer
   `<APPLE_NOTES_MCP_TOKEN>`** header. Do not expose the port to the public
   internet — keep access on the tailnet.

4. **Keep the Mac awake** so it can answer requests while you're away:

   ```bash
   caffeinate -s apple-notes-mcp --http --host 0.0.0.0 --port 8765
   ```

   `caffeinate` prevents the Mac from sleeping for the lifetime of the wrapped
   process.

## Memory model

A dedicated **`Claude Memory`** folder holds a few stable-named notes Claude
reads to learn about you instead of scanning your whole library:

| Note          | Purpose                                            |
|---------------|----------------------------------------------------|
| `Profile`     | who you are, role, context                         |
| `Preferences` | how you like Claude to work                        |
| `Projects`    | what you're building                               |
| `Log`         | append-only running notes Claude adds over time    |

- `memory_get(key)` returns that note's Markdown body, or `''` if it doesn't
  exist yet.
- `memory_set(key, body_markdown, append=False)` creates or **replaces** the
  note; with `append=True` it **appends** instead (and creates the note if it's
  missing — ideal for `Log`).

> Future (local only): a Claude Code **SessionStart hook** can auto-load memory
> at the start of each session.

## Export model

`export_note(title, body_markdown, kind="chat", folder="Claude Exports")` files
Claude-generated content into Notes. It prepends a small header (kind + today's
date), then creates the note in `Claude Exports`, and returns the created
`Note`.

> **The tool cannot read Claude's own transcript.** "Export this chat" works by
> Claude assembling the conversation (or research) as Markdown and passing it in
> as `body_markdown`; this module only formats a header and files it.

## Development & testing

```bash
.venv/bin/pytest        # convert.py is pure Python and unit-tested on any OS
.venv/bin/ruff check .
.venv/bin/mypy src
```

`convert.py` (Markdown ↔ Notes HTML) is tested in CI on Linux. Everything that
touches `osascript`/Notes is validated on macOS.

See [PLAN.md](./PLAN.md) for architecture, the core API contract, and module
ownership.
