// Shared JXA helpers prepended by apple_notes.backend.load_script.
// Keep this file free of run() — each operation script defines run(argv).
//
// Performance rules:
//   * Title lookup: Notes.notes.whose({name: title}) — never walk folders.
//   * Id lookup: whose({id}) then byId — never a nested id scan.
//   * List: bulk specifier .id()/.name(), never per-note Apple Events.
//   * Never call plaintext() on every note in the library.

function isoOrNull(d) {
  return d ? d.toISOString() : null;
}

function asArray(value) {
  if (value === undefined || value === null) return [];
  if (Object.prototype.toString.call(value) === "[object Array]") return value;
  if (typeof value === "object" && typeof value.length === "number") {
    const arr = [];
    for (let i = 0; i < value.length; i++) arr.push(value[i]);
    return arr;
  }
  return [value];
}

function noteToRecord(note) {
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
  return {
    id: note.id(),
    name: note.name() || "",
    folder: folderName,
    account: accountName,
    created: isoOrNull(note.creationDate()),
    modified: isoOrNull(note.modificationDate()),
  };
}

function notesToRecords(matches) {
  const arr = asArray(matches);
  const out = [];
  for (let i = 0; i < arr.length; i++) {
    if (arr[i]) out.push(noteToRecord(arr[i]));
  }
  return out;
}

// Bulk-read id+name from a JXA specifier (one Apple Event per property).
// Used for list: do NOT call this on a specifier that would fetch bodies.
function recordsFromSpecifier(notesSpec, folderName, accountName, limit) {
  let ids;
  let names;
  try {
    ids = asArray(notesSpec.id());
    names = asArray(notesSpec.name());
  } catch (e) {
    return [];
  }
  const n = limit > 0 ? Math.min(limit, ids.length) : ids.length;
  const out = [];
  for (let i = 0; i < n; i++) {
    out.push({
      id: ids[i],
      name: names[i] || "",
      folder: folderName || null,
      account: accountName || null,
      created: null,
      modified: null,
    });
  }
  return out;
}

// Fast id lookup. whose({id}) first, then byId. Never a nested folder walk.
function findNoteById(Notes, noteId) {
  try {
    const found = asArray(Notes.notes.whose({id: noteId})());
    if (found.length > 0 && found[0]) return found[0];
  } catch (e) {
    // fall through to byId
  }
  try {
    const note = Notes.notes.byId(noteId);
    if (note) {
      note.id();
      return note;
    }
  } catch (e) {
    // some JXA builds expose byID
  }
  try {
    const note = Notes.notes.byID(noteId);
    if (note) {
      note.id();
      return note;
    }
  } catch (e) {
    // not found
  }
  return null;
}

function collectFolders(container, folderName, out) {
  let folders;
  try {
    folders = container.folders();
  } catch (e) {
    return;
  }
  for (let i = 0; i < folders.length; i++) {
    const folder = folders[i];
    try {
      if (folder.name() === folderName) out.push(folder);
    } catch (e) {
      // skip inaccessible folder
    }
    collectFolders(folder, folderName, out);
  }
}

function findFoldersByName(Notes, folderName) {
  try {
    const found = asArray(Notes.folders.whose({name: folderName})());
    if (found.length > 0) return found;
  } catch (e) {
    // fall through to a folders-only tree walk (never notes/plaintext)
  }
  const out = [];
  try {
    const accounts = Notes.accounts();
    for (let a = 0; a < accounts.length; a++) {
      collectFolders(accounts[a], folderName, out);
    }
  } catch (e) {
    // ignore
  }
  return out;
}

function findFolderByName(Notes, folderName) {
  const folders = findFoldersByName(Notes, folderName);
  return folders.length ? folders[0] : null;
}

function evalWhose(spec) {
  try {
    return asArray(spec());
  } catch (e) {
    return [];
  }
}

// Forever Notes Planner dailies ("01 September"). Assigning note.body strips
// Home/Today/Back/Next note links that body() does not even export.
var FOREVER_NOTES_PLANNER = "Planner";
var FOREVER_NOTES_DAILY = /^(0[1-9]|[12][0-9]|3[01])\s+(January|February|March|April|May|June|July|August|September|October|November|December)$/i;

function isForeverNotesDaily(name, folder) {
  if ((folder || "") !== FOREVER_NOTES_PLANNER) return false;
  return FOREVER_NOTES_DAILY.test((name || "").replace(/^\s+|\s+$/g, ""));
}

function refuseForeverNotesDailyWrite(name, folder) {
  if (!isForeverNotesDaily(name, folder)) return;
  throw new Error(
    "refusing to assign note.body on Forever Notes daily " +
      JSON.stringify(name) +
      " in Planner: that strips Home/Today/Back/Next note links. " +
      "Notes' scripting dictionary has no append/insert — only set body. " +
      "Test writes on a throwaway note you create, never on a DD Month Planner page."
  );
}
