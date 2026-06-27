// JXA (osascript -l JavaScript). Run via apple_notes.backend.run_json.
// Args: [folderName]
// Output: JSON array of {id, name, folder, account, created, modified}.
//         Bodies are intentionally NOT included (list view is title+id only).
//
// Lists notes within the first folder whose name matches folderName
// (case-sensitive exact match), searched across all accounts.
function run(argv) {
  const folderName = argv[0];
  const Notes = Application("Notes");
  const out = [];

  const accounts = Notes.accounts();
  for (let a = 0; a < accounts.length; a++) {
    const account = accounts[a];
    const accountName = account.name();
    const folders = account.folders();
    for (let f = 0; f < folders.length; f++) {
      const folder = folders[f];
      if (folder.name() !== folderName) continue;
      const notes = folder.notes();
      for (let n = 0; n < notes.length; n++) {
        const note = notes[n];
        out.push({
          id: note.id(),
          name: note.name(),
          folder: folderName,
          account: accountName,
          created: isoOrNull(note.creationDate()),
          modified: isoOrNull(note.modificationDate()),
        });
      }
    }
  }
  return JSON.stringify(out);
}

function isoOrNull(d) {
  return d ? d.toISOString() : null;
}
