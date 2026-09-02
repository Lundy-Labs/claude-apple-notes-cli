// JXA (osascript -l JavaScript). Run via apple_notes.backend.run_json.
// Args: [title, folderName?]
//   title      - exact note name; looked up with whose({name: title}).
//   folderName - optional; if non-empty, restrict to that folder.
// Output: JSON array of {id, name, folder, account, created, modified}.
//
// Fast exact-title path via whose({name}). Do not walk folders or plaintext().
function run(argv) {
  const title = argv[0] || "";
  const folderName = argv.length > 1 ? argv[1] : "";
  if (!title) throw new Error("title is required");

  const Notes = Application("Notes");
  let spec;
  if (folderName) {
    const folder = findFolderByName(Notes, folderName);
    if (!folder) throw new Error("folder not found: " + folderName);
    spec = folder.notes.whose({name: title});
  } else {
    spec = Notes.notes.whose({name: title});
  }
  return JSON.stringify(notesToRecords(evalWhose(spec)));
}
