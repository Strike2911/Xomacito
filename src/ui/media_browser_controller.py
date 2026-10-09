from __future__ import annotations

from pathlib import Path
from uuid import uuid4
import json
import threading
from urllib.parse import urlsplit

from PySide6.QtCore import QObject, Property, QMimeData, QUrl, Slot, Qt, Signal
from PySide6.QtGui import QDrag, QGuiApplication, QDesktopServices
from PySide6.QtWidgets import QApplication, QInputDialog, QLineEdit

from .list_model import ObjectListModel
from .media_library_controller import MediaLibraryController, _folder_accent, _format_duration, SUPPORTED_MEDIA, _unique_destination
from .media_logic import safe_filename
from src.core.media_catalogs import PROVIDERS, KEY_PROVIDERS, HEADERS, search_catalog, web_url


class MediaBrowserController(MediaLibraryController):
    """Folder tree, collections and browser selection independent of the inspector."""
    webDownloadReady = Signal(str, bool)

    def __init__(self, project_root, settings, pool, ffmpeg, parent=None):
        self._scope = "all"
        self._selected_paths = []
        self._anchor = ""
        self._tree_closed = {'web'}
        self._collections = list(settings.get("media_browser_collections", []) or [])
        self._downloads = set(settings.get("media_browser_downloads", []) or [])
        self._web_rows = []
        self._web_generation = 0
        self._catalog_keys = {}
        self._web_cancel = threading.Event()
        super().__init__(project_root, settings, pool, ffmpeg, parent)
        self.browser_items = ObjectListModel([*self.ROLES, "chosen"], self)
        self.sources = ObjectListModel(["key", "label", "depth", "branch", "expanded", "count", "color", "section"], self)
        self._state.update(scope="all", scopeTitle="Todos los medios", kindFilter="Todos",
                           viewMode=settings.get("media_browser_view", "grid"),
                           tileSize=int(settings.get("media_browser_tile_size", 138)),
                           sortBy="name", sortDescending=False, selectedCount=0,
                           webMode=False, webBusy=False, webDownloading=False, webPage=1, webStatus='', webFile='', webProvider='', webNeedsKey=False)
        self._rebuild_browser()

    @Property(QObject, constant=True)
    def browserModel(self): return self.browser_items

    @Property(QObject, constant=True)
    def sourceModel(self): return self.sources

    def _rebuild_library_rows(self):
        super()._rebuild_library_rows()
        if hasattr(self, "browser_items"):
            self._rebuild_browser()

    def _source_rows(self, items):
        rows = []
        def row(key, label, depth=0, count=0, branch=False, section=False, color=""):
            rows.append(dict(key=key, label=label, depth=depth, count=count, branch=branch,
                             expanded=key not in self._tree_closed, section=section, color=color))
        row("all", "Todos los medios", count=len(items))
        row('web', 'Medios web', branch=True, section=True)
        if 'web' not in self._tree_closed:
            for provider in PROVIDERS: row('web:' + provider, provider, 1)
        row("directories", "Directorios", branch=True, section=True)
        roots = {self.root.resolve()}
        for value in self._linked_paths:
            path = Path(value)
            roots.add(path.resolve() if path.is_dir() else path.parent.resolve())
        roots = sorted((root for root in roots if not any(root != other and root.is_relative_to(other) for other in roots)), key=lambda path: str(path).casefold())
        if "directories" not in self._tree_closed:
            for root in roots:
                folders = {root}
                for item in items:
                    parent = Path(item["path"]).parent
                    if parent.is_relative_to(root):
                        while parent != root:
                            folders.add(parent)
                            parent = parent.parent
                for folder in sorted(folders, key=lambda path: str(path).casefold()):
                    if any("folder:" + str(ancestor) in self._tree_closed for ancestor in folder.parents if ancestor == root or ancestor.is_relative_to(root)):
                        continue
                    depth = len(folder.relative_to(root).parts) + 1
                    key = "folder:" + str(folder)
                    children = any(other.parent == folder for other in folders if other != folder)
                    count = sum(Path(item["path"]).is_relative_to(folder) for item in items)
                    row(key, folder.name or str(folder), depth, count, children, color=_folder_accent(folder))
        row("collections", "Colecciones", branch=True, section=True)
        if "collections" not in self._tree_closed:
            row("downloads", "Descargados", 1, sum(item["path"] in self._downloads for item in items))
            row("clips", "Subclips", 1, sum(Path(item["path"]).is_relative_to(self.clips_dir) for item in items))
            row("favorites", "Favoritos", 1, len(self._favorite_paths))
            for collection in self._collections:
                row("collection:" + collection["id"], collection["name"], 1, len(collection["paths"]))
        return rows

    def _rebuild_browser(self):
        items = self.items.items()
        existing = {item['path'] for item in items}
        self._selected_paths = [path for path in self._selected_paths if path in existing]
        sources = self._source_rows(items)
        self.sources.reconcile(sources, "key")
        if self._scope.startswith('web:'):
            self.browser_items.reconcile(self._web_rows, 'path')
            self._set_state(scope=self._scope, scopeTitle=self._scope[4:], visibleCount=len(self._web_rows), selectedCount=0)
            return
        visible = []
        query = str(self._state.get("searchText") or "").casefold().strip()
        kind = self._state.get("kindFilter", "Todos")
        collection = next((entry for entry in self._collections if "collection:" + entry["id"] == self._scope), None)
        for item in items:
            path = item["path"]
            if self._scope.startswith("folder:") and not Path(path).is_relative_to(Path(self._scope[7:])):
                continue
            if self._scope == "favorites" and str(Path(path).resolve()) not in self._favorite_paths:
                continue
            if self._scope == "downloads" and path not in self._downloads:
                continue
            if self._scope == "clips" and not Path(path).is_relative_to(self.clips_dir):
                continue
            if collection is not None and path not in collection["paths"]:
                continue
            if kind != "Todos" and item["kind"] != kind:
                continue
            if query and query not in str(item.get("searchText", item["name"])).casefold():
                continue
            visible.append({**item, "isFavorite": str(Path(path).resolve()) in self._favorite_paths,
                            "chosen": path in self._selected_paths})
        sort_key = self._state.get("sortBy", "name")
        visible.sort(key=lambda item: str(item[sort_key]).casefold() if sort_key in {"name", "extension"} else float(item.get(sort_key) or 0), reverse=self._state.get("sortDescending", False))
        self.browser_items.reconcile(visible, "path")
        title = next((entry["label"] for entry in sources if entry["key"] == self._scope), "Todos los medios")
        self._set_state(scope=self._scope, scopeTitle=title, visibleCount=len(visible), selectedCount=len(self._selected_paths),
                        collections=[{'key': 'collection:' + entry['id'], 'name': entry['name']} for entry in self._collections])

    @Slot(str)
    def setScope(self, scope):
        if scope in {"directories", "collections", "web"}:
            self.toggleSource(scope)
            return
        self._scope = scope
        self._web_generation += 1
        self._web_rows = []
        provider = scope[4:] if scope.startswith('web:') else ''
        if provider: self._tree_closed.discard('web')
        self._set_state(webMode=bool(provider), webProvider=provider, webNeedsKey=provider in KEY_PROVIDERS and not self._catalog_keys.get(provider), webBusy=False,
                        webStatus='Busca contenido en ' + provider if provider else '', searchText='', webFile='')
        self._selected_paths = []
        self.select(-1)
        self._rebuild_browser()

    @Slot(str)
    def toggleSource(self, key):
        if key in self._tree_closed: self._tree_closed.remove(key)
        else: self._tree_closed.add(key)
        self._rebuild_browser()

    @Slot(str, "QVariant")
    def setBrowserValue(self, key, value):
        allowed = {"kindFilter": {"Todos", "Imagen", "Video", "Audio"}, "viewMode": {"grid", "list"},
                   "sortBy": {"name", "sizeBytes", "duration", "extension"}}
        if key in allowed and value not in allowed[key]: return
        if key == "tileSize": value = max(90, min(220, int(value)))
        if key not in {*allowed, "tileSize", "sortDescending"}: return
        self._set_state(**{key: value})
        if key == "viewMode": self.settings.set("media_browser_view", value)
        if key == "tileSize": self.settings.set("media_browser_tile_size", value)
        self._rebuild_browser()
        if key == 'kindFilter' and self._state.get('webMode') and self._state.get('searchText'): self.searchWeb(1)

    @Slot(str, bool, bool)
    def chooseItem(self, path, control=False, shift=False):
        paths = [item["path"] for item in self.browser_items.items()]
        if path not in paths: return
        if self._state.get('webMode'):
            self._web_rows = [{**row, 'chosen': row['path'] == path} for row in self._web_rows]
            selected = next(row for row in self._web_rows if row['path'] == path)
            self._set_state(selected=selected, webFile='', waveformSource='', filmstripSource='')
            self._rebuild_browser()
            return
        if shift and self._anchor in paths:
            first, last = sorted((paths.index(self._anchor), paths.index(path)))
            self._selected_paths = list(dict.fromkeys((self._selected_paths if control else []) + paths[first:last+1]))
        elif control:
            if path in self._selected_paths: self._selected_paths.remove(path)
            else: self._selected_paths.append(path)
            self._anchor = path
        else:
            self._selected_paths = [path]
            self._anchor = path
        self.selectPath(path)
        self._rebuild_browser()

    @Slot(result="QStringList")
    def chosenPaths(self): return list(self._selected_paths)

    @Slot()
    def selectAllVisible(self):
        if self._state.get('webMode'): return
        self._selected_paths = [item["path"] for item in self.browser_items.items()]
        self._rebuild_browser()

    @Slot()
    def startDrag(self):
        if self._state.get('webMode'): return
        urls = [QUrl.fromLocalFile(path) for path in self._selected_paths if Path(path).is_file()]
        if not urls: return
        mime = QMimeData(); mime.setUrls(urls)
        drag = QDrag(QGuiApplication.focusWindow() or self)
        drag.setMimeData(mime)
        drag.exec(Qt.CopyAction)

    @Slot(str)
    def recordDownload(self, path):
        path = str(Path(path).resolve())
        target = Path(path)
        if target.is_dir():
            self._downloads.update(str(item.resolve()) for item in target.rglob('*') if item.is_file() and item.suffix.lower() in SUPPORTED_MEDIA)
        else:
            self._downloads.add(path)
        self.settings.set("media_browser_downloads", sorted(self._downloads))
        self.linkPath(path)

    @Slot()
    def createCollection(self):
        name, accepted = QInputDialog.getText(None, "Nueva colección", "Nombre de la colección:")
        if accepted: self.addCollection(name)

    @Slot(str)
    def addCollection(self, name):
        name = name.strip()[:80]
        if not name: return
        self._collections.append({"id": uuid4().hex, "name": name, "paths": list(self._selected_paths)})
        self.settings.set("media_browser_collections", self._collections)
        self._rebuild_browser()

    @Slot(str)
    def addToCollection(self, key):
        collection = next((entry for entry in self._collections if "collection:" + entry["id"] == key), None)
        if collection:
            collection["paths"] = list(dict.fromkeys(collection["paths"] + self._selected_paths))
            self.settings.set("media_browser_collections", self._collections)
            self._rebuild_browser()

    @Slot()
    def removeFromCollection(self):
        collection = next((entry for entry in self._collections if "collection:" + entry["id"] == self._scope), None)
        if collection:
            collection["paths"] = [path for path in collection["paths"] if path not in self._selected_paths]
            self.settings.set("media_browser_collections", self._collections)
            self._selected_paths = []
            self._rebuild_browser()

    @Slot()
    def removeSource(self):
        if self._scope.startswith("collection:"):
            self._collections = [entry for entry in self._collections if "collection:" + entry["id"] != self._scope]
            self.settings.set("media_browser_collections", self._collections)
        elif self._scope.startswith("folder:"):
            folder = Path(self._scope[7:]).resolve()
            if folder == self.root.resolve(): return
            self._linked_paths = [value for value in self._linked_paths if not Path(value).resolve().is_relative_to(folder)]
            self.settings.set("media_library_linked_paths", self._linked_paths)
            self.refresh()
        self.setScope("all")

    @Slot()
    def copySelectedPath(self):
        QApplication.clipboard().setText("\n".join(self._selected_paths))

    def _scan_ready(self, rows):
        # Background local indexing must not replace a remote preview.
        remote = dict(self._state.get('selected') or {}) if self._scope.startswith('web:') else None
        super()._scan_ready(rows)
        if remote is not None: self._set_state(selected=remote, waveformSource='', filmstripSource='')

    @Slot()
    def configureWebKey(self):
        provider = self._state.get('webProvider')
        if provider not in KEY_PROVIDERS: return
        value, accepted = QInputDialog.getText(None, 'Conectar ' + provider,
            'Clave API personal (se conserva solo durante esta sesión):', QLineEdit.Password)
        if accepted:
            self._catalog_keys[provider] = value.strip()
            self._set_state(webNeedsKey=not bool(value.strip()))

    @Slot(int)
    def searchWeb(self, page=1):
        provider = self._state.get('webProvider')
        query = self._state.get('searchText', '').strip()
        if provider not in PROVIDERS or not query or self._state.get('webBusy'): return
        self._web_generation += 1
        generation = self._web_generation
        self._set_state(webBusy=True, webStatus='Buscando en ' + provider + '…', webPage=max(1, page))
        self.pool.submit(search_catalog, provider, query, self._state['kindFilter'], page, self._catalog_keys.get(provider, ''),
            self.settings.directory / 'catalog-cache',
            on_result=lambda rows: self._web_ready(generation, rows),
            on_error=lambda message, detail: self._web_error(generation, message))

    def _web_ready(self, generation, rows):
        if generation != self._web_generation: return
        self._web_rows = []
        for row in rows:
            base = {role: '' for role in self.ROLES}
            base.update(row, path='web:' + row['provider'] + ':' + row['id'], name=row['title'],
                        durationLabel=_format_duration(row['duration']), sizeLabel='Web', chosen=False,
                        isFavorite=False, formatLabel=row['kind'] + ' · ' + row['provider'], sizeBytes=0,
                        metadataSummary=row['note'], searchText=row['title'])
            self._web_rows.append(base)
        self._set_state(webBusy=False, webStatus=f'{len(rows)} resultados · {self._state["webProvider"]}', selected={}, webFile='')
        self._rebuild_browser()

    def _web_error(self, generation, message):
        if generation != self._web_generation: return
        self._set_state(webBusy=False, webStatus=message)
        self.notificationRequested.emit('warning', 'Medios web', message)

    @Slot()
    def openWebSource(self):
        url = web_url((self._state.get('selected') or {}).get('pageUrl'))
        if url: QDesktopServices.openUrl(QUrl(url))

    @Slot()
    def copyWebCredits(self):
        row = self._state.get('selected') or {}
        QApplication.clipboard().setText(self._credits(row))

    @staticmethod
    def _credits(row):
        return '\n'.join(str(row.get(key) or '') for key in ('name', 'creator', 'license', 'pageUrl'))

    @Slot(bool)
    def downloadWeb(self, send_premiere=False):
        row = dict(self._state.get('selected') or {})
        if not row.get('downloadUrl') or self._state.get('webDownloading'): return
        self._web_cancel.clear()
        self._set_state(webDownloading=True, webStatus='Descargando desde ' + row['provider'] + '…')
        self.pool.submit(self._web_download_worker, row, self.root / 'Medios web' / row['provider'],
            on_result=lambda path: self._web_download_done(path, row['path'], send_premiere),
            on_error=lambda message, detail: self._web_download_error(message))

    def _web_download_worker(self, row, folder):
        import requests
        url = web_url(row['downloadUrl'])
        if not url: raise ValueError('El catálogo no ofrece una descarga directa.')
        folder.mkdir(parents=True, exist_ok=True)
        temporary = folder / ('.download-' + uuid4().hex + '.part')
        try:
            with requests.get(url, headers=HEADERS, stream=True, timeout=(10, 25)) as response:
                response.raise_for_status()
                content = response.headers.get('Content-Type', '').split(';')[0].lower()
                if content in {'text/html', 'application/json'}: raise ValueError('El origen devolvió una página en lugar del archivo. Abre su enlace original.')
                suffix = Path(urlsplit(url).path).suffix.lower()
                mime_ext = {'image/jpeg': '.jpg', 'image/png': '.png', 'image/webp': '.webp', 'image/gif': '.gif', 'video/mp4': '.mp4', 'video/webm': '.webm', 'audio/mpeg': '.mp3', 'audio/wav': '.wav', 'audio/x-wav': '.wav', 'audio/ogg': '.ogg', 'video/ogg': '.ogv', 'audio/flac': '.flac'}
                suffix = mime_ext.get(content, suffix)
                if suffix not in SUPPORTED_MEDIA: raise ValueError('Este formato no admite importación directa. Descárgalo desde el origen.')
                with temporary.open('wb') as output:
                    for chunk in response.iter_content(256*1024):
                        if self._web_cancel.is_set(): raise ValueError('Descarga cancelada.')
                        if chunk: output.write(chunk)
            if not temporary.stat().st_size: raise ValueError('El catálogo devolvió un archivo vacío.')
            destination = _unique_destination(folder, safe_filename(Path(row['name']).stem), suffix)
            temporary.replace(destination)
            destination.with_suffix(destination.suffix + '.credits.txt').write_text(self._credits(row), encoding='utf-8')
            return str(destination)
        except requests.RequestException:
            raise ValueError('Falló la descarga del catálogo. Inténtalo de nuevo o abre el origen.') from None
        finally:
            temporary.unlink(missing_ok=True)

    def _web_download_done(self, path, identity, send_premiere):
        self._set_state(webDownloading=False, webStatus='Guardado en la colección Descargados.')
        if (self._state.get('selected') or {}).get('path') == identity: self._set_state(webFile=path)
        self.recordDownload(path)
        self.webDownloadReady.emit(path, send_premiere)

    def _web_download_error(self, message):
        self._set_state(webDownloading=False, webStatus=message)
        self.notificationRequested.emit('warning', 'Descarga de medios web', message)

    @Slot()
    def cancelWebDownload(self): self._web_cancel.set()

    def shutdown(self):
        self._web_generation += 1
        self._web_cancel.set()
        super().shutdown()
