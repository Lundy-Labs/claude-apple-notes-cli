// JXA (osascript -l JavaScript). Run via apple_notes.backend.run_json.
// Args: none.
// Output: JSON array of {id, name, account}.
//
// Lists every folder across every account in Notes.app.
function run(argv) {
  const Notes = Application("Notes");
  const out = [];
  const accounts = Notes.accounts();
  for (let a = 0; a < accounts.length; a++) {
    const account = accounts[a];
    const accountName = account.name();
    const folders = account.folders();
    for (let f = 0; f < folders.length; f++) {
      const folder = folders[f];
      out.push({
        id: folder.id(),
        name: folder.name(),
        account: accountName,
      });
    }
  }
  return JSON.stringify(out);
}
