from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from uuid import uuid4
import re
import math
import time
from collections import OrderedDict
from itertools import islice

from PySide6.QtCore import QObject, Property, QTimer, QUrl, Signal, Slot
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import QApplication, QFileDialog

from .download_controller import DEFAULT_OPTIONS, reveal_in_file_manager
from .list_model import ObjectListModel
from .media_logic import seconds_from_time
from src.core.downloader import extract_info_resilient
from src.core.ytdlp_runtime import configure_ytdlp_options
from .quick_options import ACTIVE_STATUSES, CHOICES, DEFAULTS, input_kind, job_options, output_path, preferences, thumbnail_mode
from .quick_runner import _JobSettings, _QuickRunner, choose_video
from .search_preview_controller import SearchPreviewController


class QuickController(QObject):
    CHOICES = CHOICES
    stateChanged = Signal()
    notificationRequested = Signal(str, str, str)
    successfulDownload = Signal(int)
    gachaSourceCompleted = Signal(str)
    outputReady = Signal(str)
    premiereRequested = Signal(str, bool)
    cancelledRequested = Signal()
    discoveryReady = Signal()
    discoveryRequested = Signal()
    ROLES = ["jobId", "url", "title", "detail", "status", "progress", "output", "outputs", "mode", "quality", "thumbnail"]

    def __init__(self, project_root, settings, pool, dialogs, presets, version, parent=None):
        super().__init__(parent)
        self.settings = settings
        self.pool = pool
        self._state = {
            **preferences(settings.get("quick_mode_preferences", {}),
                          settings.get("premiere_library_path", str(Path.home() / "Videos" / "Xomacito"))),
            "url": "", "running": False, "pending": 0, "ranges": [],
            "discovering": False, "discoveryTitle": "", "totalProgress": 0.0,
            "discoveryQuery": "", "discoverySource": "YouTube", "discoverySelected": 0,
            "discoveryHasMore": False, "discoveryPage": 0, "discoveryError": "",
        }
        self._refresh_input()
        self.jobs = ObjectListModel(self.ROLES, self)
        self.history = ObjectListModel(self.ROLES, self)
        self.discovery = ObjectListModel(['url', 'title', 'duration', 'chosen', 'thumbnail', 'channel', 'views', 'isLive'], self)
        self.preview = SearchPreviewController(settings, pool, self)
        history = settings.get("quick_mode_history", [])
        self.history.replace([row for row in history if isinstance(row, dict) and row.get("output")][-100:][::-1])
        self._pending = []
        self._active = None
        self._closed = False
        self._discovery_generation = 0
        self._discovery_cache = OrderedDict()
        self._discovery_inflight = {}
        self._discovery_pending = None
        self.runner = _QuickRunner(project_root, _JobSettings(settings, self), pool, dialogs, presets, version, self)
        self.runner.stateChanged.connect(self._progress)
        self.runner.finished.connect(self._finished)
        self.runner.notificationRequested.connect(self._notice)
        self.runner.successfulDownload.connect(self.successfulDownload)
        self.runner.gachaSourceCompleted.connect(self.gachaSourceCompleted)
        self.runner.cancelledRequested.connect(self.cancelledRequested)
        settings.changed.connect(self._settings_changed)

    @Property("QVariantMap", notify=stateChanged)
    def state(self): return self._state

    @Property("QVariantMap", constant=True)
    def choices(self): return CHOICES

    @Property(QObject, constant=True)
    def model(self): return self.jobs

    @Property(QObject, constant=True)
    def historyModel(self): return self.history

    @Property(QObject, constant=True)
    def discoveryModel(self): return self.discovery

    @Property(QObject, constant=True)
    def previewController(self): return self.preview

    @Slot(str, "QVariant")
    def setValue(self, key, value):
        if key == "thumbnailMode" and value in CHOICES[key]:
            self._state.update(thumbnail=value == CHOICES[key][1], thumbnailOnly=value == CHOICES[key][2])
        elif key in {*DEFAULTS, "url"} and type(value) is type(self._state[key]):
            if key in CHOICES and value not in CHOICES[key]:
                return
            if self._state[key] == value:
                return
            self._state[key] = value
            if value and key in {"thumbnail", "thumbnailOnly"}:
                self._state["thumbnail" if key == "thumbnailOnly" else "thumbnailOnly"] = False
        else:
            return
        self._refresh_input()
        self.stateChanged.emit()
        if key != "url":
            self.settings.set("quick_mode_preferences", {name: self._state[name] for name in DEFAULTS})

    def _refresh_input(self):
        kind = input_kind(self._state["url"])
        destination = output_path(self._state, self.settings.get('download_tags', []))
        self._state.update(inputKind=kind, thumbnailMode=thumbnail_mode(self._state),
                           effectiveOutputPath=destination, taggedOutput=destination != self._state["outputPath"],
                           actionLabel="Buscar" if kind == "search" else
                           "Ver lista" if self._state["playlist"] else "Descargar")

    def _settings_changed(self, key, value):
        if key == "download_tags":
            self._refresh_input()
            self.stateChanged.emit()

    @Slot()
    def openSearch(self):
        if self._state['discoverySource'] == 'playlist':
            self.cancelDiscovery()
            self.discovery.clear()
            self._state.update(discoveryQuery="", discoveryPage=0, discoveryHasMore=False, discoverySelected=0)
        self._state.update(discoverySource="YouTube")
        self.stateChanged.emit()
        self.discoveryRequested.emit()

    @Slot()
    def paste(self):
        self.setValue("url", QApplication.clipboard().text().strip())

    @Slot()
    def chooseOutputFolder(self):
        folder = QFileDialog.getExistingDirectory(None, "Destino del modo rápido", self._state["outputPath"])
        if folder:
            self.setValue("outputPath", folder)

    @Slot()
    def enqueue(self):
        if self._closed:
            return
        kind = input_kind(self._state['url'])
        if kind == 'search':
            self.discover(self._state['url'], 'YouTube')
        elif kind == 'links' and self._state['playlist']:
            if len(self._state['url'].split()) != 1:
                self.notificationRequested.emit('warning', 'Lista de reproducción', 'Pega un solo enlace para elegir sus videos.')
                return
            self.discover(self._state['url'], 'playlist')
        else:
            self._enqueue_urls(self._state['url'].split())

    def _enqueue_urls(self, values):
        urls = list(dict.fromkeys(values))
        if self._closed:
            return
        if not urls or len(urls) > 50 or any(input_kind(url) != "links" for url in urls):
            self.notificationRequested.emit("warning", "Revisa los enlaces", "Pega entre 1 y 50 enlaces HTTP o HTTPS, separados por espacios o líneas.")
            return
        for url in urls:
            job = job_options(self._state, self.settings.get('download_tags', []))
            job.update(jobId=uuid4().hex, url=url)
            self._pending.append(job)
            self.jobs.append({"jobId": job["jobId"], "url": url, "title": url,
                              "detail": "Esperando turno", "status": "En cola", "progress": 0.0,
                              "output": "", "thumbnail": "", "mode": job["mode"],
                              "quality": "Miniatura" if job["thumbnailOnly"] else job["audioFormat"] if job["mode"] == "Audio" else job["quality"]})
        self._state["url"] = ""
        self._refresh_input()
        self.stateChanged.emit()
        self._update_state()
        self._next()

    def _update_state(self):
        total = sum(1.0 if status not in ACTIVE_STATUSES else max(0, progress)
                    for status, progress in zip(self.jobs.values("status"), self.jobs.values("progress"))) / max(1, self.jobs.count())
        changes = dict(running=self._active is not None, pending=len(self._pending), totalProgress=total)
        if any(self._state[key] != value for key, value in changes.items()):
            self._state.update(changes)
            self.stateChanged.emit()

    def _index(self, job_id):
        return self.jobs.find("jobId", job_id)

    def _next(self):
        if self._closed or self._active or not self._pending:
            return
        self._active = self._pending.pop(0)
        job = self._active
        self.runner.quick_options = deepcopy(job)
        self.runner.quick_outputs = []
        self.runner._options = deepcopy(DEFAULT_OPTIONS)
        self.runner._set_state(url=job["url"], outputPath=job["outputPath"], effectiveOutputPath=job["outputPath"],
                               lastOutput="", analyzed=False, busy=False)
        self._update_state()
        self.runner.analyze()

    def _progress(self):
        if not self._active:
            return
        state = self.runner.state
        self.jobs.update_item(self._index(self._active["jobId"]), {
            "title": state["title"] or self._active["url"], "detail": state["status"],
            "progress": state["progress"], "status": "Descargando" if state["analyzed"] else "Analizando",
            "thumbnail": state.get('thumbnailSource', ''),
        })
        self._update_state()

    def _notice(self, level, title, message):
        self.notificationRequested.emit(level, title, message)
        # start() can reject an invalid output folder before scheduling a worker.
        if level == "error" and self._active and not self.runner.state["busy"]:
            QTimer.singleShot(0, self._failed_start)

    def _failed_start(self):
        if self._active and not self.runner.state["busy"]:
            self._finished("Error", "")

    def _finished(self, status, output):
        if not self._active:
            return
        job = self._active
        outputs = list(getattr(self.runner, 'quick_outputs', [])) or ([output] if output and Path(output).is_file() else [])
        self.jobs.update_item(self._index(job["jobId"]), {"status": status, "output": output, "outputs": outputs})
        self._active = None
        if output:
            for path in outputs:
                self.outputReady.emit(path)
                if job["sendPremiere"]: self.premiereRequested.emit(path, False)
        if output:
            self.history.replace([self.jobs.item(self._index(job['jobId'])), *self.history.items()][:100])
            self.settings.set("quick_mode_history", self.history.items()[::-1])
        self._update_state()
        QTimer.singleShot(0, self._next)

    @Slot(str)
    def cancel(self, job_id):
        if self._active and self._active["jobId"] == job_id:
            self.runner.cancel()
        else:
            self._pending = [job for job in self._pending if job["jobId"] != job_id]
            self.jobs.update_item(self._index(job_id), {"status": "Cancelado", "detail": "Cancelado antes de iniciar"})
            self._update_state()

    @Slot(str)
    def openResult(self, path):
        if Path(path).exists():
            reveal_in_file_manager(path)

    @Slot(str)
    def sendToPremiere(self, path):
        row = next((row for row in self.jobs.items() + self.history.items() if row.get('output') == path), {})
        for output in row.get('outputs') or [path]: self.premiereRequested.emit(output, False)

    @Slot()
    def clearHistory(self):
        self.history.clear()
        self.settings.set("quick_mode_history", [])

    @Slot()
    def clearActivity(self):
        self.jobs.replace([row for row in self.jobs.items() if row['status'] in ACTIVE_STATUSES])
        self._update_state()

    @Slot()
    def cancelAll(self):
        for job in self._pending:
            self.jobs.update_item(self._index(job['jobId']), {"status": "Cancelado", "detail": "Cancelado antes de iniciar"})
        self._pending.clear()
        self._update_state()
        if self._active: self.cancel(self._active['jobId'])

    @Slot(str)
    def removeJob(self, job_id):
        index = self._index(job_id)
        row = self.jobs.item(index)
        if row and row['status'] not in ACTIVE_STATUSES:
            self.jobs.remove(index); self._update_state()

    @Slot()
    def openOutputFolder(self):
        folder = Path(self._state['effectiveOutputPath']).expanduser()
        if folder.is_dir(): QDesktopServices.openUrl(QUrl.fromLocalFile(str(folder)))

    @Slot(str, str)
    def addRange(self, start, end):
        try:
            first, last = seconds_from_time(start), seconds_from_time(end)
            if not all(re.fullmatch(r'\d+(?::\d{1,2}){0,2}(?:\.\d+)?', value.strip()) for value in (start, end)) or not math.isfinite(last) or first < 0 or last <= first or len(self._state['ranges']) >= 24: raise ValueError()
        except (ValueError, TypeError):
            self.notificationRequested.emit('warning', 'Revisa el recorte', 'Indica una entrada y una salida posterior en HH:MM:SS. Máximo 24 recortes.')
            return
        self._state['ranges'] = [*self._state['ranges'], {'startTime': start.strip(), 'endTime': end.strip()}]
        self.stateChanged.emit()

    @Slot(int)
    def removeRange(self, index):
        self._state['ranges'] = [row for i, row in enumerate(self._state['ranges']) if i != index]
        self.stateChanged.emit()

    @Slot(str, str)
    def discover(self, query, source):
        if self._closed or not query.strip() or source not in {'playlist', 'YouTube', 'SoundCloud'}: return
        query = query.strip()
        if source == 'playlist' and not query.startswith(('https://', 'http://')): return
        self.preview.close()
        self._discovery_generation += 1
        self._discovery_pending = None
        self.discovery.replace([])
        self._state.update(discovering=True, discoveryQuery=query, discoverySource=source,
                           discoveryPage=0, discoveryHasMore=False, discoverySelected=0, discoveryError="",
                           discoveryTitle='Lista de reproducción' if source == 'playlist' else 'Resultados de ' + source)
        self.stateChanged.emit()
        self.discoveryRequested.emit()
        self._request_discovery(1)

    @Slot()
    def loadMoreDiscovery(self):
        if self._state['discovering'] or not self._state['discoveryHasMore']: return
        self._state.update(discovering=True, discoveryError="")
        self.stateChanged.emit()
        self._request_discovery(self._state['discoveryPage'] + 1)

    @Slot()
    def cancelDiscovery(self):
        self._discovery_generation += 1
        self._discovery_pending = None
        self._state['discovering'] = False
        self.stateChanged.emit()

    def _request_discovery(self, page):
        query, source = self._state['discoveryQuery'], self._state['discoverySource']
        size = 50 if source == 'playlist' else 20
        lookup = query if source == 'playlist' else ('ytsearch' if source == 'YouTube' else 'scsearch') + str(page * size) + ':' + query
        from src.core.browser_cookies import cookie_options
        cookies = cookie_options(self.settings, lookup)
        # Session-local cache: a cookie/account change cannot reuse another search.
        key = (source, query, page, repr(sorted(cookies.items())))
        job = (self._discovery_generation, key, lookup, page, size, cookies)
        cached = self._discovery_cache.get(key)
        if cached and time.monotonic() - cached[0] < 120:
            self._discovery_cache.move_to_end(key)
            self._accept_discovery(job, deepcopy(cached[1]))
            return
        if len(self._discovery_inflight) >= 2:
            self._discovery_pending = job  # Replace superseded work, never queue every keystroke.
        else:
            self._start_discovery(job)

    def _start_discovery(self, job):
        generation, key, lookup, page, size, cookies = job
        token = (generation, page)
        self._discovery_inflight[token] = job
        self.pool.submit(self._discovery_worker, lookup, page, size, cookies,
                         on_result=lambda rows: self._finish_discovery(job, rows),
                         on_error=lambda message, detail: self._finish_discovery(job, None, message))

    def _finish_discovery(self, job, rows, error=""):
        self._discovery_inflight.pop((job[0], job[3]), None)
        if not self._closed:
            if rows is not None:
                self._discovery_cache[job[1]] = (time.monotonic(), deepcopy(rows))
                self._discovery_cache.move_to_end(job[1])
                while len(self._discovery_cache) > 24: self._discovery_cache.popitem(last=False)
            if job[0] == self._discovery_generation:
                if rows is None: self._discovery_error(error, "")
                else: self._accept_discovery(job, rows)
            pending, self._discovery_pending = self._discovery_pending, None
            if pending and pending[0] == self._discovery_generation: self._start_discovery(pending)

    def _accept_discovery(self, job, rows):
        if self._closed or job[0] != self._discovery_generation: return
        _, _, _, page, size, _ = job
        previous = self.discovery.items() if page > 1 else []
        seen = {row['url'] for row in previous}
        for row in rows:
            if row['url'] not in seen:
                previous.append(row)
                seen.add(row['url'])
        self._state.update(discoveryPage=page, discoveryHasMore=len(rows) == size and page * size < 200,
                           discoveryError="")
        self._discovery_done(previous)

    def _discovery_worker(self, lookup, page=1, size=20, cookies=None):
        options = configure_ytdlp_options({
            'extract_flat': 'in_playlist', 'skip_download': True, 'lazy_playlist': True,
            'noplaylist': False, 'playliststart': (page - 1) * size + 1, 'playlistend': page * size,
            'quiet': True, 'socket_timeout': 10, 'retries': 1, 'extractor_retries': 1,
        })
        if cookies is None:
            from src.core.browser_cookies import cookie_options
            cookies = cookie_options(self.settings, lookup)
        options.update(cookies)
        result = extract_info_resilient(lookup, options, download=False) or {}
        rows = []
        for entry in islice(result.get('entries') or [result], size):
            if not entry: continue
            url = entry.get('webpage_url') or entry.get('url') or ''
            video_id = str(entry.get('id', ''))
            youtube = entry.get('ie_key', '').lower() == 'youtube'
            if not url.startswith(('http://', 'https://')) and youtube and re.fullmatch(r'[A-Za-z0-9_-]{11}', video_id):
                url = 'https://www.youtube.com/watch?v=' + video_id
            thumbnails = [item for item in entry.get('thumbnails') or [] if item.get('url')]
            if youtube and re.fullmatch(r'[A-Za-z0-9_-]{11}', video_id):
                thumbnail = 'https://i.ytimg.com/vi/' + video_id + '/mqdefault.jpg'
            else:
                thumbnails.sort(key=lambda item: abs((item.get('width') or 320) - 320))
                thumbnail = thumbnails[0]['url'] if thumbnails else entry.get('thumbnail') or ''
            if thumbnail.startswith('//'): thumbnail = 'https:' + thumbnail
            if url.startswith(('http://', 'https://')):
                rows.append(dict(url=url, title=entry.get('title') or url, duration=entry.get('duration') or 0,
                                 chosen=lookup.startswith(('http://', 'https://')), thumbnail=thumbnail,
                                 channel=entry.get('channel') or entry.get('uploader') or '',
                                 views=entry.get('view_count') or 0, isLive=bool(entry.get('is_live'))))
        return rows

    def _discovery_done(self, rows):
        if self._closed: return
        self._state['discovering'] = False
        self.discovery.replace(rows)
        self._update_discovery_count()
        self.discoveryReady.emit()

    def _discovery_error(self, message, detail):
        if self._closed: return
        self._state.update(discovering=False, discoveryError=message)
        self.stateChanged.emit()
        self.notificationRequested.emit('error', 'No se pudo buscar', message)

    @Slot(int, bool)
    def chooseDiscovery(self, index, chosen):
        self.discovery.update_item(index, {'chosen': chosen})
        self._update_discovery_count()

    def _update_discovery_count(self):
        self._state['discoverySelected'] = sum(bool(row.get('chosen')) for row in self.discovery.items())
        self.stateChanged.emit()

    @Slot(bool)
    def chooseAllDiscovery(self, chosen):
        for index in range(self.discovery.count()): self.discovery.update_item(index, {'chosen': chosen})
        self._update_discovery_count()

    @Slot(int)
    def previewDiscovery(self, index):
        row = self.discovery.item(index)
        if row: self.preview.show(row)

    @Slot()
    def openPreviewSource(self):
        url = self.preview.state['pageUrl']
        if url: QDesktopServices.openUrl(QUrl(url))

    @Slot()
    def enqueueDiscovery(self):
        self._enqueue_urls([row['url'] for row in self.discovery.items() if row['chosen']])

    def shutdown(self):
        self._closed = True
        self.cancelDiscovery()
        self.preview.shutdown()
        self.runner.shutdown()
