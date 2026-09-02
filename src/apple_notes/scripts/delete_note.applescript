// JXA (osascript -l JavaScript). Run via apple_notes.backend.run_json.
// Args: [noteId]   - stable AppleScript id of the note to delete.
// Output: JSON string "ok" on success; throws if the note is not found.
function run(argv) {
  const noteId = argv[0];
  const Notes = Application("Notes");

  const note = findNoteById(Notes, noteId);
  if (!note) {
    throw new Error("note not found: " + noteId);
  }
  Notes.delete(note);
  return JSON.stringify("ok");
}
