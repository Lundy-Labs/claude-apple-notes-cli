// JXA (osascript -l JavaScript). Run via apple_notes.backend.run_json.
// Args: [noteId, htmlFragment]
//   noteId       - stable AppleScript id of the note to append to.
//   htmlFragment - HTML fragment concatenated onto the existing body.
// Output: JSON object {id, name, folder, account, created, modified}.
//
// THIS ASSIGNS note.body. Notes.sdef has no append/insert/attributedText
// command — the only scriptable content mutation is setting `body`, which
// re-serializes the note and strips Forever Notes Home/Today/Back/Next links
// (those links are not present in body() HTML; href count is 0). Do not use
// this on Planner "DD Month" dailies; the script refuses those titles.
function run(argv) {
  const noteId = argv[0];
  const htmlFragment = argv[1];
  const Notes = Application("Notes");

  const note = findNoteById(Notes, noteId);
  if (!note) {
    throw new Error("note not found: " + noteId);
  }

  const rec = noteToRecord(note);
  refuseForeverNotesDailyWrite(rec.name, rec.folder);

  const current = note.body() || "";
  note.body = current + htmlFragment;

  return JSON.stringify(noteToRecord(note));
}
