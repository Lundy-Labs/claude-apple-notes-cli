// JXA (osascript -l JavaScript). Run via apple_notes.backend.run_json.
// Args: [noteId]   - stable AppleScript id (x-coredata://...).
// Output: JSON object {id, name, folder, account, body, created, modified}.
//         `body` is the raw Notes HTML (converted to Markdown in Python
//         unless the caller asked for HTML).
//
// Looks the note up with whose({id}) / byId. Never a nested folder scan.
function run(argv) {
  const noteId = argv[0];
  const Notes = Application("Notes");

  const note = findNoteById(Notes, noteId);
  if (!note) {
    throw new Error("note not found: " + noteId);
  }

  const rec = noteToRecord(note);
  rec.body = note.body();
  return JSON.stringify(rec);
}
