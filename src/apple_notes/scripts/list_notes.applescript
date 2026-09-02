// JXA (osascript -l JavaScript). Run via apple_notes.backend.run_json.
// Args: [folderName, limit?]
//   folderName - exact folder name (whose({name})), searched across accounts.
//   limit      - optional max notes (0 / omitted = no cap).
// Output: JSON array of {id, name, folder, account, created, modified}.
//         Bodies are intentionally NOT included. Dates are omitted so a large
//         default Notes folder does not hang on per-note Apple Events.
//
// Uses bulk specifier .id()/.name() (two Apple Events per folder), not a
// per-note loop that calls name()/id()/dates on every note.
function run(argv) {
  const folderName = argv[0];
  const limit = argv.length > 1 ? parseInt(argv[1], 10) || 0 : 0;
  const Notes = Application("Notes");

  const folders = findFoldersByName(Notes, folderName);
  if (!folders.length) throw new Error("folder not found: " + folderName);

  const out = [];
  for (let i = 0; i < folders.length; i++) {
    if (limit > 0 && out.length >= limit) break;
    const folder = folders[i];
    let accountName = null;
    try {
      accountName = folder.container().name();
    } catch (e) {
      accountName = null;
    }
    const remaining = limit > 0 ? limit - out.length : 0;
    const chunk = recordsFromSpecifier(
      folder.notes,
      folder.name(),
      accountName,
      remaining
    );
    for (let j = 0; j < chunk.length; j++) out.push(chunk[j]);
  }
  return JSON.stringify(out);
}
