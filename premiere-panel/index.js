const uxp = require("uxp");
const ppro = require("premierepro");
const localFileSystem = uxp.storage.localFileSystem;
const TOKEN_KEY = "xomacito-library-folder-v1";
const AUTO_SYNC_KEY = "xomacito-auto-sync-v1";
const IMPORT_BIN_NAME = "Xomacito Import";
const SYNC_INTERVAL_MS = 2500;

const VIDEO_EXTENSIONS = new Set(["mp4", "mov", "m4v", "mkv", "webm", "avi", "mxf", "mts", "m2ts"]);
const AUDIO_EXTENSIONS = new Set(["mp3", "m4a", "wav", "flac", "aac", "ogg", "opus", "wma"]);
const IMAGE_EXTENSIONS = new Set(["png", "jpg", "jpeg", "webp", "tif", "tiff", "gif"]);
const MEDIA_EXTENSIONS = new Set([...VIDEO_EXTENSIONS, ...AUDIO_EXTENSIONS, ...IMAGE_EXTENSIONS]);

let libraryFolder = null;
let allItems = [];
let selectedPath = "";
let activeFilter = "Todos";
let eventsAttached = false;
let autoSyncEnabled = localStorage.getItem(AUTO_SYNC_KEY) === "true";
let autoSyncTimer = null;
let syncBusy = false;
let knownProjectPaths = new Set();
let stableObservations = new Map();
let lastProjectGuid = "";
let currentProjectName = "";

const byId = (id) => document.getElementById(id);

function setStatus(message, kind = "") {
  const node = byId("status");
  const dot = byId("activity-dot");
  node.textContent = message;
  node.className = `status ${kind}`.trim();
  dot.className = `activity-dot ${kind}`.trim();
}

function renderConnection() {
  const button = byId("connect-project");
  const badge = byId("connection-state");
  const projectStep = byId("project-step");
  const syncStep = byId("sync-step");
  const projectReady = Boolean(currentProjectName);

  button.textContent = autoSyncEnabled ? "Pausar autoimportación" : "Activar autoimportación";
  button.classList.toggle("connected", autoSyncEnabled);
  badge.textContent = autoSyncEnabled ? "ACTIVO" : "PAUSADO";
  badge.className = `connection-state${autoSyncEnabled ? " connected" : ""}`;
  byId("project-name").textContent = currentProjectName || "Abre un proyecto de Premiere";
  byId("project-step-label").textContent = projectReady ? "Detectado" : "Pendiente";
  byId("sync-step-label").textContent = autoSyncEnabled ? "Activo" : "Pausado";
  projectStep.className = `progress-step${projectReady ? " done" : ""}`;
  syncStep.className = `progress-step${autoSyncEnabled ? " active" : ""}`;
  byId("connection-help").textContent = autoSyncEnabled
    ? "Vigilando la biblioteca. Sólo se importan archivos terminados y sin duplicados."
    : "Actívalo para crear Xomacito Import y organizar automáticamente cada descarga.";
}

function extension(name) {
  const parts = String(name || "").toLowerCase().split(".");
  return parts.length > 1 ? parts.pop() : "";
}

function kindForExtension(ext) {
  if (VIDEO_EXTENSIONS.has(ext)) return "Video";
  if (AUDIO_EXTENSIONS.has(ext)) return "Audio";
  return "Imagen";
}

function binForItem(path, kind) {
  if (String(path).toLowerCase().includes("recortes")) return "Recortes";
  if (kind === "Imagen") return "Imágenes";
  return kind;
}

async function walk(folder, output = []) {
  const entries = await folder.getEntries();
  for (const entry of entries) {
    if (entry.isFolder) {
      if (entry.name !== ".xomacito-thumbnails") await walk(entry, output);
    } else if (entry.isFile && MEDIA_EXTENSIONS.has(extension(entry.name))) {
      const ext = extension(entry.name);
      const kind = kindForExtension(ext);
      output.push({
        name: entry.name,
        path: entry.nativePath,
        entry,
        extension: ext,
        kind,
        binName: binForItem(entry.nativePath, kind),
      });
    }
  }
  return output;
}

function visibleItems() {
  const term = byId("search").value.trim().toLowerCase();
  return allItems.filter((item) => {
    const matchesKind = activeFilter === "Todos" || item.kind === activeFilter;
    const matchesTerm = !term || item.name.toLowerCase().includes(term) || item.extension.includes(term);
    return matchesKind && matchesTerm;
  });
}

function renderItems() {
  const visible = visibleItems();
  const container = byId("items");
  container.replaceChildren();
  byId("item-count").textContent = String(visible.length);
  if (!visible.length) {
    const empty = document.createElement("div");
    empty.className = "empty-list";
    empty.textContent = allItems.length
      ? "No hay archivos que coincidan con este filtro."
      : "Esta biblioteca todavía no tiene medios compatibles.";
    container.appendChild(empty);
    return;
  }

  for (const item of visible) {
    const button = document.createElement("button");
    button.className = `item${selectedPath === item.path ? " selected" : ""}`;
    button.type = "button";
    button.title = item.path;

    const icon = document.createElement("span");
    icon.className = "item-icon";
    icon.textContent = item.kind === "Video" ? "VID" : item.kind === "Audio" ? "AUD" : "IMG";

    const copy = document.createElement("span");
    copy.className = "item-copy";
    const title = document.createElement("span");
    title.className = "item-title";
    title.textContent = item.name;
    const meta = document.createElement("span");
    meta.className = "item-meta";
    meta.textContent = `${item.extension.toUpperCase()} · ${IMPORT_BIN_NAME} › ${item.binName}`;
    copy.append(title, meta);
    button.append(icon, copy);
    button.addEventListener("click", () => selectItem(item));
    container.appendChild(button);
  }
}

function selectItem(item) {
  selectedPath = item.path;
  byId("selection-summary").textContent = item.name;
  byId("selection-panel").classList.remove("hidden");
  byId("import-project").disabled = false;
  byId("add-timeline").disabled = false;
  renderItems();
}

function selectedItem() {
  return allItems.find((item) => item.path === selectedPath) || null;
}

async function connectFolder(forcePicker = false) {
  let folder = null;
  if (!forcePicker) {
    const token = localStorage.getItem(TOKEN_KEY);
    if (token) {
      try { folder = await localFileSystem.getEntryForPersistentToken(token); }
      catch (_error) { localStorage.removeItem(TOKEN_KEY); }
    }
  }
  if (!folder) {
    folder = await localFileSystem.getFolder();
    if (!folder) return;
    const token = await localFileSystem.createPersistentToken(folder);
    localStorage.setItem(TOKEN_KEY, token);
  }
  libraryFolder = folder;
  knownProjectPaths = new Set();
  stableObservations = new Map();
  byId("empty").classList.add("hidden");
  byId("library").classList.remove("hidden");
  byId("folder-name").textContent = folder.nativePath;
  byId("folder-name").title = folder.nativePath;
  await refreshLibrary();
}

async function refreshLibrary() {
  if (!libraryFolder) return connectFolder(false);
  setStatus("Leyendo la biblioteca…", "working");
  try {
    allItems = await walk(libraryFolder, []);
    allItems.sort((a, b) => a.name.localeCompare(b.name, "es", { sensitivity: "base" }));
    if (selectedPath && !allItems.some((item) => item.path === selectedPath)) {
      selectedPath = "";
      byId("selection-panel").classList.add("hidden");
    }
    renderItems();
    setStatus(`${allItems.length} archivo(s) disponible(s).`, "success");
  } catch (error) {
    setStatus(`No se pudo leer la biblioteca: ${error}`, "error");
  }
}

async function activeProject() {
  const project = await ppro.Project.getActiveProject();
  if (!project) throw new Error("Abre o crea un proyecto de Premiere primero.");
  return project;
}

async function refreshProjectIdentity(project = null) {
  try {
    const target = project || await activeProject();
    currentProjectName = String(target.name || "Proyecto activo");
  } catch (_error) {
    currentProjectName = "";
  }
  renderConnection();
}

async function findProjectItem(folder, mediaPath) {
  const children = await folder.getItems();
  for (const item of children) {
    try {
      const clip = ppro.ClipProjectItem.cast(item);
      const path = await clip.getMediaFilePath();
      if (String(path).toLowerCase() === String(mediaPath).toLowerCase()) return item;
    } catch (_clipError) {
      try {
        const childFolder = ppro.FolderItem.cast(item);
        const match = await findProjectItem(childFolder, mediaPath);
        if (match) return match;
      } catch (_folderError) { /* no es un bin */ }
    }
  }
  return null;
}

async function findDirectFolder(parent, name) {
  const children = await parent.getItems();
  for (const item of children) {
    try {
      const folder = ppro.FolderItem.cast(item);
      if (String(folder.name).toLowerCase() === String(name).toLowerCase()) return folder;
    } catch (_error) { /* no es un bin */ }
  }
  return null;
}

async function createBin(project, parent, name) {
  let success = false;
  project.lockedAccess(() => {
    success = project.executeTransaction((compoundAction) => {
      compoundAction.addAction(parent.createBinAction(name, false));
    }, `Crear bin ${name}`);
  });
  if (!success) throw new Error(`Premiere no pudo crear el bin ${name}.`);
}

async function ensureImportBin(project) {
  let root = await project.getRootItem();
  let targetBin = await findDirectFolder(root, IMPORT_BIN_NAME);
  if (targetBin) return targetBin;
  await createBin(project, root, IMPORT_BIN_NAME);
  root = await project.getRootItem();
  targetBin = await findDirectFolder(root, IMPORT_BIN_NAME);
  if (!targetBin) throw new Error(`El bin ${IMPORT_BIN_NAME} se creó, pero no pudo localizarse.`);
  return targetBin;
}

async function ensureCategoryBin(project, categoryName) {
  const importBin = await ensureImportBin(project);
  let targetBin = await findDirectFolder(importBin, categoryName);
  if (targetBin) return targetBin;
  await createBin(project, importBin, categoryName);
  targetBin = await findDirectFolder(importBin, categoryName);
  if (!targetBin) throw new Error(`No se pudo preparar ${IMPORT_BIN_NAME} › ${categoryName}.`);
  return targetBin;
}

async function ensureImported(project, item) {
  const mediaPath = item.path;
  const root = await project.getRootItem();
  let projectItem = await findProjectItem(root, mediaPath);
  if (projectItem) return projectItem;
  const targetBin = await ensureCategoryBin(project, item.binName);
  const imported = await project.importFiles([mediaPath], true, targetBin, false);
  if (!imported) throw new Error("Premiere rechazó la importación del archivo.");
  projectItem = await findProjectItem(await project.getRootItem(), mediaPath);
  if (!projectItem) throw new Error("El archivo se importó, pero no se pudo localizar en el proyecto.");
  return projectItem;
}

async function stableItems(items) {
  const stable = [];
  const current = new Set();
  for (const item of items) {
    const key = item.path.toLowerCase();
    current.add(key);
    let signature = key;
    try {
      const metadata = await item.entry.getMetadata();
      signature = `${metadata.size || 0}:${metadata.dateModified || metadata.modified || ""}`;
    } catch (_error) { /* dos observaciones de la misma ruta siguen siendo seguras */ }
    const previous = stableObservations.get(key);
    const count = previous && previous.signature === signature ? previous.count + 1 : 1;
    stableObservations.set(key, { signature, count });
    if (count >= 2) stable.push(item);
  }
  for (const key of stableObservations.keys()) {
    if (!current.has(key)) stableObservations.delete(key);
  }
  return stable;
}

async function syncProject(showSummary = false) {
  if (!autoSyncEnabled || !libraryFolder || syncBusy) return;
  syncBusy = true;
  try {
    const project = await activeProject();
    await refreshProjectIdentity(project);
    const projectGuid = String(project.guid || project.name || "active-project");
    if (projectGuid !== lastProjectGuid) {
      lastProjectGuid = projectGuid;
      knownProjectPaths = new Set();
    }
    await ensureImportBin(project);
    const latestItems = await walk(libraryFolder, []);
    const readyItems = await stableItems(latestItems);
    let importedCount = 0;
    for (const item of readyItems) {
      const key = item.path.toLowerCase();
      if (knownProjectPaths.has(key)) continue;
      const root = await project.getRootItem();
      if (await findProjectItem(root, item.path)) {
        knownProjectPaths.add(key);
        continue;
      }
      await ensureImported(project, item);
      knownProjectPaths.add(key);
      importedCount += 1;
    }

    const currentPaths = new Set(latestItems.map((item) => item.path.toLowerCase()));
    knownProjectPaths = new Set([...knownProjectPaths].filter((path) => currentPaths.has(path)));
    const waitingCount = Math.max(0, latestItems.length - readyItems.length);
    if (importedCount) {
      setStatus(`${importedCount} archivo(s) nuevo(s) organizado(s) en ${IMPORT_BIN_NAME}.`, "success");
    } else if (waitingCount) {
      setStatus(`Esperando que ${waitingCount} archivo(s) terminen de escribirse…`, "working");
    } else if (showSummary) {
      setStatus(`${currentProjectName} está conectado y al día.`, "success");
    }
    if (latestItems.length !== allItems.length) await refreshLibrary();
  } catch (error) {
    currentProjectName = "";
    renderConnection();
    setStatus(`Premiere: ${error}`, "error");
  } finally {
    syncBusy = false;
  }
}

async function toggleProjectConnection() {
  if (!libraryFolder) await connectFolder(false);
  if (!libraryFolder) return;
  if (!autoSyncEnabled) {
    try {
      const project = await activeProject();
      await ensureImportBin(project);
      await refreshProjectIdentity(project);
      autoSyncEnabled = true;
      localStorage.setItem(AUTO_SYNC_KEY, "true");
      renderConnection();
      startAutoSync();
      await syncProject(true);
    } catch (error) {
      setStatus(String(error), "error");
    }
    return;
  }
  autoSyncEnabled = false;
  localStorage.setItem(AUTO_SYNC_KEY, "false");
  renderConnection();
  stopAutoSync();
  setStatus("Autoimportación pausada. La biblioteca sigue disponible.");
}

function startAutoSync() {
  stopAutoSync();
  if (!autoSyncEnabled) return;
  autoSyncTimer = setInterval(() => syncProject(false), SYNC_INTERVAL_MS);
}

function stopAutoSync() {
  if (autoSyncTimer !== null) clearInterval(autoSyncTimer);
  autoSyncTimer = null;
}

async function importSelected() {
  const item = selectedItem();
  if (!item) return;
  setStatus(`Importando ${item.name}…`, "working");
  try {
    const project = await activeProject();
    await refreshProjectIdentity(project);
    await ensureImported(project, item);
    knownProjectPaths.add(item.path.toLowerCase());
    setStatus(`Listo en ${IMPORT_BIN_NAME} › ${item.binName}.`, "success");
  } catch (error) {
    setStatus(String(error), "error");
  }
}

async function addSelectedToTimeline() {
  const item = selectedItem();
  if (!item) return;
  setStatus(`Añadiendo ${item.name} en el cabezal…`, "working");
  try {
    const project = await activeProject();
    await refreshProjectIdentity(project);
    const projectItem = await ensureImported(project, item);
    knownProjectPaths.add(item.path.toLowerCase());
    const sequence = await project.getActiveSequence();
    if (!sequence) throw new Error("Abre una secuencia para añadir el archivo a la línea de tiempo.");
    const position = await sequence.getPlayerPosition();
    const editor = ppro.SequenceEditor.getEditor(sequence);
    let success = false;
    project.lockedAccess(() => {
      success = project.executeTransaction((compoundAction) => {
        compoundAction.addAction(editor.createInsertProjectItemAction(projectItem, position, 0, 0, true));
      }, "Añadir desde Xomacito");
    });
    if (!success) throw new Error("Premiere no pudo completar la inserción.");
    setStatus("Añadido en el cabezal de reproducción.", "success");
  } catch (error) {
    setStatus(String(error), "error");
  }
}

function setFilter(kind) {
  activeFilter = kind;
  for (const button of byId("filters").querySelectorAll(".filter")) {
    button.classList.toggle("active", button.dataset.kind === kind);
  }
  renderItems();
}

function attachEvents() {
  if (eventsAttached) return;
  eventsAttached = true;
  byId("choose-folder").addEventListener("click", () => connectFolder(true));
  byId("change-folder").addEventListener("click", () => connectFolder(true));
  byId("refresh").addEventListener("click", refreshLibrary);
  byId("search").addEventListener("input", renderItems);
  byId("import-project").addEventListener("click", importSelected);
  byId("add-timeline").addEventListener("click", addSelectedToTimeline);
  byId("connect-project").addEventListener("click", toggleProjectConnection);
  for (const button of byId("filters").querySelectorAll(".filter")) {
    button.addEventListener("click", () => setFilter(button.dataset.kind));
  }
  renderConnection();
}

uxp.entrypoints.setup({
  panels: {
    xomacitoLinkPanel: {
      show() {
        attachEvents();
        connectFolder(false)
          .then(() => refreshProjectIdentity())
          .then(() => { startAutoSync(); return syncProject(false); })
          .catch((error) => setStatus(String(error), "error"));
      },
      hide() { stopAutoSync(); }
    }
  }
});
