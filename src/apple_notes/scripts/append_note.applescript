// JXA (osascript -l JavaScript). Run via apple_notes.backend.run_json.
// Args: [noteId, htmlFragment]
//   noteId       - stable AppleScript id of the note to append to.
//   htmlFragment - HTML to append to the END of the existing body. The title
//                  (first line) is left untouched.
// Output: JSON object {id, name, folder, account, created, modified}.
function run(argv) {
  const noteId = argv[0];
  const htmlFragment = argv[1];
  const Notes = Application("Notes");

  const note = findNoteById(Notes, noteId);
  if (!note) {
    throw new Error("note not found: " + noteId);
  }

  // Concatenating HTML keeps the existing title (first line) intact and adds
  // the new content after it.
  const current = note.body() || "";
  note.body = current + htmlFragment;

  let folderName = null;
  let accountName = null;
  try {
    const container = note.container();
    if (container) {
      folderName = container.name();
      try {
        accountName = container.container().name();
      } catch (e) {
        accountName = null;
      }
    }
  } catch (e) {
    folderName = null;
  }

  return JSON.stringify({
    id: note.id(),
    name: note.name(),
    folder: folderName,
    account: accountName,
    created: isoOrNull(note.creationDate()),
    modified: isoOrNull(note.modificationDate()),
  });
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

function isoOrNull(d) {
  return d ? d.toISOString() : null;
}
