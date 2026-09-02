# claude-apple-notes-cli — design

Read/write Apple Notes from the terminal and from Claude, communicating in
**Markdown**. Doubles as a **memory** store so Claude can learn about the user.

## Decisions

- **Language:** Python 3.11+.
- **Shape:** shared core (`notes.py`) with two front-ends — a Typer **CLI** and an
  **MCP server**.
- **Backend:** AppleScript via `osascript` only (officially supported; no fragile
  SQLite/protobuf writes).
- **Markdown is the wire format.** Apple Notes stores HTML internally; conversion
  happens at the boundary in `convert.py`.

## The Apple Notes reality

No public/cloud API exists. The only programmatic access is **AppleScript or the
local SQLite DB, on macOS**. Consequences:

- The server must run on a **Mac** (your own Mac / a Mac mini). It cannot run on
  iOS (no AppleScript), nor serverless (Lambda/Workers have no API to call).
- **iPhone/iPad use:** run the MCP server on the Mac with **HTTP transport +
  bearer token**, reach it over **Tailscale**; iCloud keeps notes in sync.

## Architecture

```
   terminal ─► Typer CLI ─┐
                          ├─► notes.py (core) ─► convert.py (md↔html)
   Claude ─► MCP server ──┘                  └─► backend.py ─► osascript ─► Notes.app
             • stdio (local)
             • HTTP + token (remote / iPhone via Tailscale)
```

## Modules & ownership

| Module | Responsibility | Agent |
|---|---|---|
| `models.py` | `Note`, `Folder` dataclasses (foundation, done) | — |
| `notes.py` | core API contract + orchestration | B |
| `backend.py` + `scripts/` | osascript bridge + AppleScript templates | B |
| `convert.py` + `tests/test_convert.py` | Markdown ↔ Notes HTML (pure, tested) | A |
| `cli.py` | Typer commands | C |
| `mcp_server.py` | MCP tools; stdio + HTTP transports | C |
| `memory.py` | `Claude Memory` folder conventions | D |
| `export.py` | file chats/research into notes | D |
| `README.md` | setup, permissions, Tailscale, caffeinate | D |

## Core API (the contract)

```
list_folders() -> [Folder]
list_notes(folder=None, *, limit=None) -> [Note]   # title+id; bulk specifier read
find_notes_by_title(title, folder=None) -> [Note]  # whose({name}); no body scan
search_notes(query, folder=None, *, title_only=False) -> [Note]
read_note(note_id, *, html=False) -> Note          # Markdown, or raw HTML
create_note(title, body_markdown, folder=DEFAULT_FOLDER) -> Note
append_note(note_id, body_markdown) -> Note        # assigns note.body; refuses Planner dailies
delete_note(note_id) -> None
```

Lookups use JXA `whose()` / `byId`. Body search never `plaintext()`s the whole
library (requires `--folder`, or defaults to Claude Memory + Claude Exports).

**Forever Notes:** there is no non-rewriting append in Notes' scripting
dictionary. `append_note` assigns `body` and will not touch Planner `DD Month`
pages.

## Safety defaults

- Tool is pinned to `Claude Memory` / `Claude Exports` folders unless an explicit
  `--folder` is given — it won't roam the whole personal library by accident.
- Notes addressed by stable AppleScript `id`, or by exact title via
  `find_notes_by_title` (`whose({name})`).
- Never assign `note.body` on Forever Notes Planner dailies.

## Memory model

A `Claude Memory` folder with notes: `Core` (curated summary), `Profile`,
`Preferences`, `Projects`, `Log` (append-only). Two tiers keep per-session cost
flat:

- **Tier 1 (push):** `memory_core()` returns the small `Core` note + a pointer
  list of other notes' titles. A Claude Code **SessionStart hook**
  (`notes memory core`, matcher `startup|resume`) injects this into context
  automatically; it's hook-safe (exits 0 on backend errors).
- **Tier 2 (pull):** bulk notes fetched on demand via `memory_get` /
  `notes_search`, only when relevant.

Same split serves remote/iPhone, where there's no hook — Claude pulls via the
`memory_core` / `memory_get` MCP tools.

## Build phases

1. Core read path (backend + convert + notes read/list/search + CLI).
2. Write path (create/append, md→html, title-from-first-line).
3. MCP wrapper (stdio + HTTP + auth).
4. Memory + export.
5. Polish (config, README: permissions / Tailscale / caffeinate).

## Testing note

`convert.py` is pure Python and unit-tested in CI/Linux. Everything touching
`osascript`/Notes is validated on macOS. First run triggers a macOS Automation
permission prompt for Notes.
