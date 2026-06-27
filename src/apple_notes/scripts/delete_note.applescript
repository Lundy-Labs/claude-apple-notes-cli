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

function findNoteById(Notes, noteId) {
  const accounts = Notes.accounts();
  for (let a = 0; a < accounts.length; a++) {
    const folders = accounts[a].folders();
    for (let f = 0; f < folders.length; f++) {
      const notes = folders[f].notes();
      for (let n = 0; n < notes.length; n++) {
        if (notes[n].id() === noteId) return notes[n];
      }
    }
  }
  return null;
}
