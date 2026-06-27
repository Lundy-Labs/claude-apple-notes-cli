// JXA (osascript -l JavaScript). Run via apple_notes.backend.run_json.
// Args: [noteId]   - stable AppleScript id (x-coredata://...).
// Output: JSON object {id, name, folder, account, body, created, modified}.
//         `body` is the raw Notes HTML (converted to Markdown in Python).
//
// Looks the note up by id. Notes.app exposes notes by id via Notes.notes.byId,
// but that helper is unreliable for x-coredata ids, so we scan for an id match.
function run(argv) {
  const noteId = argv[0];
  const Notes = Application("Notes");

  const note = findNoteById(Notes, noteId);
  if (!note) {
    throw new Error("note not found: " + noteId);
  }

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

  const result = {
    id: note.id(),
    name: note.name(),
    folder: folderName,
    account: accountName,
    body: note.body(),
    created: isoOrNull(note.creationDate()),
    modified: isoOrNull(note.modificationDate()),
  };
  return JSON.stringify(result);
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
