// JXA (osascript -l JavaScript). Run via apple_notes.backend.run_json.
// Args: [folderName, bodyHtml, accountName?]
//   folderName  - target folder; created in the chosen account if missing.
//   bodyHtml    - full note HTML. Its FIRST line/element becomes the note title
//                 (Notes derives the note name from line 1), so the caller must
//                 already have prepended the title. We do NOT pass a name here.
//   accountName - optional; default account used when omitted/empty.
// Output: JSON object {id, name, folder, account, created, modified}.
function run(argv) {
  const folderName = argv[0];
  const bodyHtml = argv[1];
  const accountName = argv.length > 2 ? argv[2] : "";
  const Notes = Application("Notes");

  const account = pickAccount(Notes, accountName);
  const folder = findOrCreateFolder(Notes, account, folderName);

  // Create the note inside the folder. Notes takes the title from the first
  // line of the body, so we only supply `body`.
  const note = Notes.Note({ body: bodyHtml });
  folder.notes.push(note);

  return JSON.stringify({
    id: note.id(),
    name: note.name(),
    folder: folder.name(),
    account: account.name(),
    created: isoOrNull(note.creationDate()),
    modified: isoOrNull(note.modificationDate()),
  });
}

function pickAccount(Notes, accountName) {
  const accounts = Notes.accounts();
  if (accountName) {
    for (let a = 0; a < accounts.length; a++) {
      if (accounts[a].name() === accountName) return accounts[a];
    }
    throw new Error("account not found: " + accountName);
  }
  // Default to the default account if exposed, else the first account.
  try {
    const def = Notes.defaultAccount();
    if (def) return def;
  } catch (e) {
    // fall through
  }
  if (accounts.length === 0) throw new Error("no Notes accounts available");
  return accounts[0];
}

function findOrCreateFolder(Notes, account, folderName) {
  const folders = account.folders();
  for (let f = 0; f < folders.length; f++) {
    if (folders[f].name() === folderName) return folders[f];
  }
  // Autocreate the folder in this account.
  const folder = Notes.Folder({ name: folderName });
  account.folders.push(folder);
  return folder;
}

function isoOrNull(d) {
  return d ? d.toISOString() : null;
}
