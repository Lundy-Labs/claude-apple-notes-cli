// JXA (osascript -l JavaScript). Run via apple_notes.backend.run_json.
// Args: [query, folderName?]
//   query      - case-insensitive substring matched against title and body.
//   folderName - optional; if non-empty, restrict the search to that folder.
// Output: JSON array of {id, name, folder, account, created, modified}.
//         Bodies are not returned (search yields title+id results).
function run(argv) {
  const query = (argv[0] || "").toLowerCase();
  const folderName = argv.length > 1 ? argv[1] : "";
  const Notes = Application("Notes");
  const out = [];

  const accounts = Notes.accounts();
  for (let a = 0; a < accounts.length; a++) {
    const account = accounts[a];
    const accountName = account.name();
    const folders = account.folders();
    for (let f = 0; f < folders.length; f++) {
      const folder = folders[f];
      const fname = folder.name();
      if (folderName && fname !== folderName) continue;
      const notes = folder.notes();
      for (let n = 0; n < notes.length; n++) {
        const note = notes[n];
        const name = note.name() || "";
        // plaintext() gives the body without HTML markup for matching.
        let bodyText = "";
        try {
          bodyText = note.plaintext() || "";
        } catch (e) {
          bodyText = "";
        }
        const hay = (name + "\n" + bodyText).toLowerCase();
        if (query !== "" && hay.indexOf(query) === -1) continue;
        out.push({
          id: note.id(),
          name: name,
          folder: fname,
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
