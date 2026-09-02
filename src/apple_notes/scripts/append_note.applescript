// JXA (osascript -l JavaScript). Run via apple_notes.backend.run_json.
// Args: [noteId, htmlFragment]
//   noteId       - stable AppleScript id of the note to append to.
//   htmlFragment - HTML to append to the END of the existing body.
// Output: JSON object {id, name, folder, account, created, modified}.
function run(argv) {
  const noteId = argv[0];
  const htmlFragment = argv[1];
  const Notes = Application("Notes");

  const note = findNoteById(Notes, noteId);
  if (!note) {
    throw new Error("note not found: " + noteId);
  }

  const rec = noteToRecord(note);
  // Assigning note.body re-serializes the note and strips Forever Notes nav links.
  if (rec.folder === "Planner" && /^(0[1-9]|[12][0-9]|3[01])\s+(January|February|March|April|May|June|July|August|September|October|November|December)$/i.test(rec.name || "")) {
    throw new Error("refusing to assign note.body on a Planner daily: that strips Forever Notes nav links");
  }

  const current = note.body() || "";
  note.body = current + htmlFragment;

  return JSON.stringify(noteToRecord(note));
}
