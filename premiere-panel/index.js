const uxp = require("uxp");
const ppro = require("premierepro");
const localFileSystem = uxp.storage.localFileSystem;
const TOKEN_KEY = "xomacito-library-folder-v1";
const AUTO_SYNC_KEY = "xomacito-auto-sync-v1";
const IMPORT_BIN_NAME = "Xomacito Import";

const VIDEO_EXTENSIONS = new Set(["mp4", "mov", "m4v", "mkv", "webm", "avi", "mxf", "mts", "m2ts"]);
const AUDIO_EXTENSIONS = new Set(["mp3", "m4a", "wav", "flac", "aac", "ogg", "opus", "wma"]);
const IMAGE_EXTENSIONS = new Set(["png", "jpg", "jpeg", "webp", "tif", "tiff", "gif"]);
const MEDIA_EXTENSIONS = new Set([...VIDEO_EXTENSIONS, ...AUDIO_EXTENSIONS, ...IMAGE_EXTENSIONS]);

let libraryFolder = null;
let allItems = [];
let selectedPaths = new Set();
let pageIndex = 0;
const PAGE_SIZE = 40;
let currentProjectId = "";
let activeFilter = "Todos";
let eventsAttached = false;
let autoSyncEnabled = localStorage.getItem(AUTO_SYNC_KEY) === "true";
let autoTimeline = localStorage.getItem("xomacito-auto-timeline") === "true";
let timelineImages = localStorage.getItem("xomacito-timeline-images") === "true";
let browserOpen = false;
let scanGeneration = 0;
let syncBusy = false;
let currentProjectName = "";
let unavailableFolderCount = 0;
let bridgeTimer = null;
let bridgeBusy = false;

const byId = (id) => document.getElementById(id);

function setStatus(message, kind = "") {
  const node = byId("status");
  const dot = byId("activity-dot");
  node.textContent = message;
  node.className = `status ${kind}`.trim();
  dot.className = `activity-dot ${kind}`.trim();
}

function renderConnection() {
  const ready = Boolean(currentProjectName);
  byId("connect-project").checked = autoSyncEnabled;
  byId("connect-project").disabled = !ready;
  byId("auto-timeline").checked = autoTimeline;
  byId("auto-timeline").disabled = !ready || !autoSyncEnabled;
  byId("timeline-images").checked = timelineImages;
  byId("timeline-images").disabled = !ready || !autoSyncEnabled || !autoTimeline;
  byId("connection-state").textContent = ready ? "CONECTADO" : "SIN PROYECTO";
  byId("connection-state").className = "badge" + (ready ? " connected" : "");
  byId("project-name").textContent = currentProjectName || "Abre un proyecto de Premiere";
  byId("connection-help").textContent = autoSyncEnabled
    ? autoTimeline ? "Inserta en V1/A1 y desplaza los clips siguientes. Requiere secuencia abierta." : "Descargas terminadas → Xomacito Import · Video / Audio / Imágenes"
    : "Envío manual disponible · Destino: Xomacito Import";
  byId("send-to-app").disabled = !ready;
  renderSelection();
}
function pathKey(path) {
  const normalized = String(path).replace(/\\/g, "/");
  return /^[a-z]:\//i.test(normalized) || normalized.startsWith("//") ? normalized.toLowerCase() : normalized;
}
function projectIdentity(project) {
  return project ? String(project.guid || project.path || project.name || "") : "";
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

async function walk(folder, output = [], depth = 0) {
  let entries = [];
  try {
    entries = await folder.getEntries();
  } catch (error) {
    if (depth === 0) throw error;
    unavailableFolderCount += 1;
    return output;
  }
  for (const entry of entries) {
    if (entry.isFolder) {
      if (!entry.name.startsWith(".xomacito")) await walk(entry, output, depth + 1);
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

async function libraryItems(folder) {
  const items = await walk(folder, []);
  const paths = new Set(items.map((item) => item.path));
  try {
    const manifest = JSON.parse(await (await folder.getEntry(".xomacito-library.json")).read());
    if (manifest.schema !== 1 || !Array.isArray(manifest.items)) return items;
    for (const row of manifest.items) {
      if (!row || typeof row.path !== "string" || paths.has(row.path)) continue;
      const ext = extension(row.path);
      if (!MEDIA_EXTENSIONS.has(ext)) continue;
      const kind = kindForExtension(ext);
      items.push({ name: String(row.name || row.path), path: row.path, extension: ext, kind,
        binName: binForItem(row.path, kind), linked: true });
      paths.add(row.path);
    }
  } catch (_error) { /* Standalone panel still works without a desktop manifest. */ }
  return items;
}

function showSetup(title = "Conecta tu biblioteca", copy = "Elige la misma carpeta que ves en Biblioteca dentro de Xomacito.") {
  scanGeneration++;
  libraryFolder = null;
  allItems = [];
  selectedPaths.clear();
  stopBridge();
  byId("library").classList.add("hidden");
  byId("empty").classList.remove("hidden");
  byId("setup-title").textContent = title;
  byId("setup-copy").textContent = copy;
}

function visibleItems() {
  const term = byId("search").value.trim().toLowerCase();
  return allItems.filter((item) => {
    const matchesKind = activeFilter === "Todos" || item.kind === activeFilter;
    const matchesTerm = !term || item.name.toLowerCase().includes(term) || item.extension.includes(term);
    return matchesKind && matchesTerm;
  });
}

function renderSelection() {
  const count = selectedPaths.size;
  byId("selection-summary").textContent = count ? count + " archivo(s) seleccionado(s)" : "Selecciona archivos de la lista";
  byId("import-project").disabled = !count || !currentProjectName || syncBusy || bridgeBusy;
  byId("add-timeline").disabled = count !== 1 || !currentProjectName || syncBusy || bridgeBusy;
  byId("add-timeline").title = count > 1 ? "Selecciona un solo archivo para insertarlo en V1/A1" : "Insertar en V1/A1; desplaza los clips siguientes";
}
function renderItems() {
  const visible = visibleItems();
  const pages = Math.max(1, Math.ceil(visible.length / PAGE_SIZE));
  pageIndex = Math.min(pageIndex, pages - 1);
  const container = byId("items");
  container.replaceChildren();
  byId("item-count").textContent = visible.length + " archivos";
  byId("page-label").textContent = (pageIndex + 1) + " / " + pages;
  byId("previous-page").disabled = pageIndex === 0;
  byId("next-page").disabled = pageIndex + 1 >= pages;
  byId("select-page").disabled = !visible.length;
  if (!visible.length) {
    const empty = document.createElement("div");
    empty.className = "empty-list";
    empty.textContent = allItems.length ? "No hay coincidencias." : "No hay medios compatibles en esta biblioteca.";
    container.appendChild(empty);
  }
  for (const item of visible.slice(pageIndex * PAGE_SIZE, (pageIndex + 1) * PAGE_SIZE)) {
    // Native UXP buttons flatten child nodes. File rows are real flex containers.
    const row = document.createElement("div");
    row.className = "item" + (selectedPaths.has(item.path) ? " selected" : "");
    row.tabIndex = 0;
    row.setAttribute("role", "option");
    row.setAttribute("aria-selected", String(selectedPaths.has(item.path)));
    row.setAttribute("aria-label", item.name);
    row.title = item.path;
    const icon = document.createElement("div"); icon.className = "item-icon";
    icon.textContent = item.kind === "Video" ? "VID" : item.kind === "Audio" ? "AUD" : "IMG";
    const copy = document.createElement("div"); copy.className = "item-copy";
    const title = document.createElement("div"); title.className = "item-title"; title.textContent = item.name;
    const meta = document.createElement("div"); meta.className = "item-meta";
    meta.textContent = item.extension.toUpperCase() + " · " + item.binName;
    const check = document.createElement("div"); check.className = "item-check";
    copy.appendChild(title); copy.appendChild(meta);
    row.appendChild(icon); row.appendChild(copy); row.appendChild(check);
    const toggle = () => {
      if (selectedPaths.has(item.path)) selectedPaths.delete(item.path); else selectedPaths.add(item.path);
      row.classList.toggle("selected", selectedPaths.has(item.path));
      row.setAttribute("aria-selected", String(selectedPaths.has(item.path)));
      renderSelection();
    };
    row.addEventListener("click", toggle);
    row.addEventListener("keydown", (event) => {
      if (event.key === "Enter" || event.key === " ") { event.preventDefault(); toggle(); }
    });
    container.appendChild(row);
  }
  renderSelection();
}

async function connectFolder(forcePicker = false) {
  if (bridgeBusy || syncBusy) return false;
  let folder = null;
  if (!forcePicker) {
    const token = localStorage.getItem(TOKEN_KEY);
    if (token) {
      try { folder = await localFileSystem.getEntryForPersistentToken(token); }
      catch (_error) { localStorage.removeItem(TOKEN_KEY); }
    }
  }
  if (!folder) {
    if (!forcePicker) {
      showSetup();
      return false;
    }
    folder = await localFileSystem.getFolder();
    if (!folder) return false;
    const token = await localFileSystem.createPersistentToken(folder);
    localStorage.setItem(TOKEN_KEY, token);
  }
  try {
    await folder.getEntries();
  } catch (_error) {
    localStorage.removeItem(TOKEN_KEY);
    showSetup(
      "Vuelve a vincular la biblioteca",
      "Premiere perdió el permiso o la carpeta de OneDrive cambió. Tus archivos siguen intactos."
    );
    setStatus("La biblioteca anterior ya no está disponible.", "error");
    return false;
  }
  libraryFolder = folder;
  scanGeneration++;
  allItems = [];
  selectedPaths.clear();
  pageIndex = 0;
  byId("empty").classList.add("hidden");
  byId("library").classList.remove("hidden");
  byId("folder-name").textContent = folder.nativePath;
  byId("folder-name").title = folder.nativePath;
  startBridge();
  if (browserOpen) await refreshLibrary();
  return true;
}

async function refreshLibrary() {
  if (!libraryFolder) return connectFolder(false);
  const generation = ++scanGeneration;
  const folder = libraryFolder;
  setStatus("Leyendo la biblioteca…", "working");
  try {
    unavailableFolderCount = 0;
    const items = await libraryItems(folder);
    if (generation !== scanGeneration || folder !== libraryFolder) return;
    allItems = items;
    allItems.sort((a, b) => a.name.localeCompare(b.name, "es", { sensitivity: "base" }));
    selectedPaths = new Set([...selectedPaths].filter(path => allItems.some(item => item.path === path)));
    renderItems();
    setStatus(
      unavailableFolderCount
        ? `${allItems.length} archivo(s). ${unavailableFolderCount} carpeta(s) de OneDrive aún no están disponibles.`
        : `${allItems.length} archivo(s) disponible(s).`,
      unavailableFolderCount ? "working" : "success"
    );
  } catch (error) {
    if (generation !== scanGeneration || folder !== libraryFolder) return;
    localStorage.removeItem(TOKEN_KEY);
    showSetup(
      "No pudimos abrir esa biblioteca",
      "Puede haberse movido, estar sólo en la nube o haber perdido el permiso. Elígela nuevamente."
    );
    setStatus("Biblioteca desconectada. Vuelve a vincularla.", "error");
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
    currentProjectId = projectIdentity(target);
  } catch (_error) {
    currentProjectName = "";
    currentProjectId = "";
  }
  renderConnection();
}

async function findProjectItem(folder, mediaPath) {
  const children = await folder.getItems();
  for (const item of children) {
    try {
      const clip = ppro.ClipProjectItem.cast(item);
      const path = await clip.getMediaFilePath();
      if (pathKey(path) === pathKey(mediaPath)) return item;
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

async function projectMediaIndex(folder, index = new Map()) {
  for (const item of await folder.getItems()) {
    try {
      const path = await ppro.ClipProjectItem.cast(item).getMediaFilePath();
      if (path) index.set(pathKey(path), item);
    } catch (_clipError) {
      let child = null;
      try { child = ppro.FolderItem.cast(item); } catch (_folderError) { /* not a bin */ }
      if (child) await projectMediaIndex(child, index);
    }
  }
  return index;
}

async function toggleBrowser() {
  browserOpen = !browserOpen;
  byId("browser").classList.toggle("hidden", !browserOpen);
  byId("toggle-browser").textContent = browserOpen ? "Ocultar archivos" : "Explorar archivos";
  if (browserOpen) await refreshLibrary();
}

function automaticTimelineFor(request, paths) {
  return request.automatic === true && autoTimeline && paths.length === 1
    && (timelineImages || kindForExtension(extension(paths[0])) !== "Imagen");
}

async function ensureImported(project, item, index = null) {
  const mediaPath = item.path;
  const root = await project.getRootItem();
  let projectItem = index ? index.get(pathKey(mediaPath)) : await findProjectItem(root, mediaPath);
  if (projectItem) return projectItem;
  const targetBin = await ensureCategoryBin(project, item.binName);
  const imported = await project.importFiles([mediaPath], true, targetBin, false);
  if (!imported) throw new Error("Premiere rechazó la importación del archivo.");
  projectItem = await findProjectItem(targetBin, mediaPath);
  if (!projectItem) throw new Error("El archivo se importó, pero no se pudo localizar en el proyecto.");
  if (index) index.set(pathKey(mediaPath), projectItem);
  return projectItem;
}

async function toggleProjectConnection() {
  try {
    await refreshProjectIdentity();
    if (!currentProjectName) throw new Error("Abre un proyecto de Premiere.");
    autoSyncEnabled = byId("connect-project").checked;
    localStorage.setItem(AUTO_SYNC_KEY, String(autoSyncEnabled));
    renderConnection();
    await processBridge();
    setStatus(autoSyncEnabled ? "Las próximas descargas terminadas se importarán automáticamente." : "Autoimportación desactivada.");
  } catch (error) { setStatus(String(error), "error"); renderConnection(); }
}
async function importSelected() {
  if (bridgeBusy || syncBusy) return;
  const items = allItems.filter(item => selectedPaths.has(item.path));
  if (!items.length) return;
  syncBusy = true; renderSelection();
  let imported = 0;
  try {
    const project = await activeProject();
    const identity = projectIdentity(project);
    const index = await projectMediaIndex(await project.getRootItem());
    for (const item of items) {
      await assertProject(identity);
      await ensureImported(project, item, index);
      imported++;
    }
    setStatus(imported + " archivo(s) disponible(s) en " + IMPORT_BIN_NAME + ".", "success");
  } catch (error) { setStatus(imported + "/" + items.length + " completados. " + String(error), "error"); }
  finally { syncBusy = false; renderSelection(); }
}
async function addSelectedToTimeline() {
  if (bridgeBusy || syncBusy || selectedPaths.size !== 1) return;
  const item = allItems.find(item => selectedPaths.has(item.path));
  if (!item) return;
  syncBusy = true; renderSelection();
  try {
    const project = await activeProject();
    const identity = projectIdentity(project);
    if (!await project.getActiveSequence()) throw new Error("Abre una secuencia antes de insertar.");
    const projectItem = await ensureImported(project, item);
    await assertProject(identity);
    await insertBridgeItem(project, projectItem);
    setStatus("Insertado en V1/A1 en el cabezal.", "success");
  } catch (error) { setStatus(String(error), "error"); }
  finally { syncBusy = false; renderSelection(); }
}
async function assertProject(identity) {
  const project = await activeProject();
  if (identity && projectIdentity(project) !== identity) throw new Error("Cambió el proyecto activo. Vuelve a enviar la selección.");
  return project;
}
async function sendSelectionToApp() {
  if (!libraryFolder || bridgeBusy || syncBusy) return;
  try {
    const project = await activeProject();
    const selection = await ppro.ProjectUtils.getSelection(project);
    const paths = [];
    for (const item of await selection.getItems()) {
      try {
        const path = await ppro.ClipProjectItem.cast(item).getMediaFilePath();
        if (path && MEDIA_EXTENSIONS.has(extension(path)) && !paths.includes(path)) paths.push(path);
      } catch (_error) { /* Bins, sequences and generated media have no source path. */ }
    }
    if (!paths.length) throw new Error("Selecciona medios en el panel Proyecto de Premiere.");
    if (paths.length > 500) throw new Error("Envía hasta 500 archivos por selección.");
    const id = (Date.now().toString(16) + Math.random().toString(16).slice(2)).padEnd(32, "0").slice(0,32);
    await writeBridgeJson(await bridgeFolder(libraryFolder), id + ".to-app.json",
      {schema: 1, id, paths, expires: Date.now()/1000 + 120});
    setStatus("Enviado a Xomacito; esperando confirmación…", "working");
  } catch (error) { setStatus(String(error), "error"); }
}

function setFilter(kind) {
  activeFilter = kind;
  pageIndex = 0;
  for (const button of byId("filters").querySelectorAll(".filter")) {
    button.selected = button.dataset.kind === kind;
  }
  renderItems();
}

async function writeBridgeJson(folder, name, value) {
  const entry = await folder.createFile(name, { overwrite: true });
  await entry.write(JSON.stringify(value));
}

async function bridgeFolder(root) {
  try { return await root.getEntry(".xomacito-link"); }
  catch (_error) {
    try { return await root.createFolder(".xomacito-link"); }
    catch (_race) { return await root.getEntry(".xomacito-link"); }
  }
}

async function insertBridgeItem(project, projectItem) {
  const sequence = await project.getActiveSequence();
  if (!sequence) throw new Error("Abre una secuencia antes de insertar en el cabezal.");
  const position = await sequence.getPlayerPosition();
  const editor = ppro.SequenceEditor.getEditor(sequence);
  let success = false;
  project.lockedAccess(() => {
    success = project.executeTransaction((compound) => {
      compound.addAction(editor.createInsertProjectItemAction(projectItem, position, 0, 0, true));
    }, "Insertar desde Xomacito");
  });
  if (!success) throw new Error("Premiere no pudo insertar el archivo.");
}

async function processBridge() {
  if (!libraryFolder || bridgeBusy || syncBusy) return;
  bridgeBusy = true;
  const root = libraryFolder;
  try {
    const folder = await bridgeFolder(root);
    let project = null;
    try { project = await activeProject(); } catch (_error) { /* keep connection alive without a project */ }
    const projectName = project ? String(project.name || "Proyecto activo") : "";
    currentProjectName = projectName;
    currentProjectId = projectIdentity(project);
    renderConnection();
    const identity = currentProjectId;
    await writeBridgeJson(folder, "heartbeat.json", { time: Date.now() / 1000, project: projectName, projectId: identity, autoImport: autoSyncEnabled, protocol: 2, version: "1.6.0" });
    const entries = await folder.getEntries();
    const names = new Set(entries.map((entry) => entry.name));
    for (const entry of entries) {
      if (entry.isFile && /^[a-f0-9]{32}\.app-result\.json$/.test(entry.name)) {
        try {
          const result = JSON.parse(await entry.read());
          setStatus(result.message, result.ok ? "success" : "error");
          await entry.delete();
        } catch (_error) { /* Retry incomplete acknowledgement on the next poll. */ }
        continue;
      }
      if (!entry.isFile || !/^[a-f0-9]{32}\.request\.json$/.test(entry.name)) continue;
      const id = entry.name.slice(0, 32);
      if (names.has(`${id}.result.json`)) continue;
      let result;
      try {
        const request = JSON.parse(await entry.read());
        const paths = request.schema === 2 ? request.paths : [request.path];
        if (request.id !== id || ![1,2].includes(request.schema) || !["import", "timeline"].includes(request.action)
            || !Array.isArray(paths) || !paths.length || paths.length > 500
            || paths.some(path => typeof path !== "string" || !MEDIA_EXTENSIONS.has(extension(path))
               || !(/^[a-z]:\//i.test(pathKey(path)) || pathKey(path).startsWith("/")))
            || (request.action === "timeline" && paths.length !== 1)) {
          throw new Error("La solicitud de Xomacito no es válida.");
        }
        if (!Number.isFinite(request.expires) || request.expires < Date.now() / 1000) throw new Error("El envío caducó; vuelve a enviarlo desde Xomacito.");
        if (names.has(id + ".claimed.json")) throw new Error("El envío anterior se interrumpió. Revisa tu proyecto antes de volver a enviarlo.");
        if (!project) throw new Error("Abre un proyecto en Premiere y vuelve a enviar el archivo.");
        if ((request.projectId && request.projectId !== currentProjectId) || (request.project && request.project !== projectName))
          throw new Error("Cambió el proyecto activo. Vuelve a enviar el archivo al proyecto correcto.");
        if (request.automatic && !autoSyncEnabled) throw new Error("Autoimportación desactivada.");
        const timeline = request.action === "timeline" || automaticTimelineFor(request, paths);
        if (timeline && !await project.getActiveSequence()) throw new Error("Abre una secuencia antes de insertar. El archivo sigue disponible en Xomacito.");
        await writeBridgeJson(folder, id + ".claimed.json", { id });
        let completed = 0;
        const unique = [...new Map(paths.map(path => [pathKey(path),path])).values()];
        const index = unique.length > 1 ? await projectMediaIndex(await project.getRootItem()) : null;
        for (const path of unique) {
          try {
            if (Date.now()/1000 > request.expires) throw new Error("El envío caducó.");
            await assertProject(identity);
            const kind = kindForExtension(extension(path));
            const projectItem = await ensureImported(project, { path, binName: binForItem(path, kind) }, index);
            if (timeline) {
              await assertProject(identity);
              await insertBridgeItem(project, projectItem);
            }
            completed++;
            if (!allItems.some(item => pathKey(item.path) === pathKey(path))) {
              allItems.push({path, name: path.replace(/\\/g, "/").split("/").pop(), extension: extension(path), kind, binName: binForItem(path, kind)});
            }
          } catch (error) {
            throw new Error(completed + "/" + unique.length + " completados. " + String(error.message || error));
          }
        }
        result = { id, ok: true, completed, message: timeline ? "Archivo insertado en V1/A1 en el cabezal." : completed + " archivo(s) importado(s) en Xomacito Import." };
        if (browserOpen) renderItems();
      } catch (error) {
        result = { id, ok: false, message: String(error.message || error) };
      }
      await writeBridgeJson(folder, `${id}.result.json`, result);
      setStatus(result.message, result.ok ? "success" : "error");
    }
  } catch (error) {
    setStatus(`Conexión con Xomacito: ${error}`, "error");
  } finally {
    bridgeBusy = false;
    renderSelection();
  }
}

function startBridge() {
  if (bridgeTimer !== null) clearInterval(bridgeTimer);
  bridgeTimer = setInterval(processBridge, 1500);
  processBridge();
}

function stopBridge() {
  if (bridgeTimer !== null) clearInterval(bridgeTimer);
  bridgeTimer = null;
}

function attachEvents() {
  if (eventsAttached) return;
  eventsAttached = true;
  byId("choose-folder").addEventListener("click", () => connectFolder(true));
  byId("change-folder").addEventListener("click", () => connectFolder(true));
  byId("refresh").addEventListener("click", async () => {
    if (!libraryFolder) return connectFolder(true);
    await processBridge();
    if (browserOpen) await refreshLibrary();
    else setStatus(currentProjectName ? "Conectado a " + currentProjectName : "Abre un proyecto en Premiere.");
  });
  byId("toggle-browser").addEventListener("click", toggleBrowser);
  byId("auto-timeline").addEventListener("change", () => {
    autoTimeline = byId("auto-timeline").checked;
    localStorage.setItem("xomacito-auto-timeline", String(autoTimeline));
    renderConnection();
  });
  byId("timeline-images").addEventListener("change", () => {
    timelineImages = byId("timeline-images").checked;
    localStorage.setItem("xomacito-timeline-images", String(timelineImages));
    renderConnection();
  });
  byId("search").addEventListener("input", () => { pageIndex = 0; renderItems(); });
  byId("previous-page").addEventListener("click", () => { pageIndex--; renderItems(); });
  byId("next-page").addEventListener("click", () => { pageIndex++; renderItems(); });
  byId("select-page").addEventListener("click", () => {
    for (const item of visibleItems().slice(pageIndex*PAGE_SIZE, (pageIndex+1)*PAGE_SIZE)) selectedPaths.add(item.path);
    renderItems();
  });
  byId("clear-selection").addEventListener("click", () => { selectedPaths.clear(); renderItems(); });
  byId("send-to-app").addEventListener("click", sendSelectionToApp);
  byId("import-project").addEventListener("click", importSelected);
  byId("add-timeline").addEventListener("click", addSelectedToTimeline);
  byId("connect-project").addEventListener("change", toggleProjectConnection);
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
          .catch((error) => setStatus(String(error), "error"));
      },
      hide() { stopBridge(); }
    }
  }
});
