// JXA (osascript -l JavaScript). Run via apple_notes.backend.run_json.
// Args: [query, folderName, titleOnly, bodyFolders]
//   query       - substring matched against titles (whose) and optionally bodies.
//   folderName  - optional; if non-empty, title+body search is restricted to it.
//   titleOnly   - "1" to skip body search entirely.
//   bodyFolders - \x1f-separated folder names for body search when folderName
//                 is empty. Body search NEVER walks the whole library.
// Output: JSON array of {id, name, folder, account, created, modified}.
//
// Title-first: exact whose({name}) then whose({name: {_contains}}). Body
// search is folder-scoped and prefers whose({plaintext: {_contains}}).
function run(argv) {
  const query = argv[0] || "";
  const folderName = argv.length > 1 ? argv[1] : "";
  const titleOnly = argv.length > 2 && argv[2] === "1";
  const bodyFolders = (argv.length > 3 ? argv[3] : "")
    .split("\x1f")
    .filter(function (s) { return s; });

  const Notes = Application("Notes");
  const seen = {};
  const out = [];

  function addNotes(matches) {
    const recs = notesToRecords(matches);
    for (let i = 0; i < recs.length; i++) {
      const rec = recs[i];
      if (seen[rec.id]) continue;
      seen[rec.id] = true;
      out.push(rec);
    }
  }

  function titleWhose(notesSpec) {
    addNotes(evalWhose(notesSpec.whose({name: query})));
    addNotes(evalWhose(notesSpec.whose({name: {_contains: query}})));
  }

  if (folderName) {
    const folder = findFolderByName(Notes, folderName);
    if (!folder) throw new Error("folder not found: " + folderName);
    titleWhose(folder.notes);
  } else {
    titleWhose(Notes.notes);
  }

  if (titleOnly) return JSON.stringify(out);

  const foldersToScan = folderName ? [folderName] : bodyFolders;
  if (!foldersToScan.length) {
    throw new Error(
      "body search requires a folder (pass --folder) or use --title-only"
    );
  }

  for (let f = 0; f < foldersToScan.length; f++) {
    const folder = findFolderByName(Notes, foldersToScan[f]);
    if (!folder) continue;

    let usedWhose = false;
    try {
      addNotes(evalWhose(folder.notes.whose({plaintext: {_contains: query}})));
      usedWhose = true;
    } catch (e) {
      usedWhose = false;
    }
    if (usedWhose) continue;

    // Last resort: plaintext() only notes in THIS folder. Never the library.
    let notes;
    try {
      notes = folder.notes();
    } catch (e) {
      continue;
    }
    const needle = query.toLowerCase();
    for (let n = 0; n < notes.length; n++) {
      const note = notes[n];
      let id;
      try {
        id = note.id();
      } catch (e) {
        continue;
      }
      if (seen[id]) continue;
      let bodyText = "";
      try {
        bodyText = note.plaintext() || "";
      } catch (e) {
        bodyText = "";
      }
      if (needle && bodyText.toLowerCase().indexOf(needle) === -1) continue;
      addNotes([note]);
    }
  }

  return JSON.stringify(out);
}
