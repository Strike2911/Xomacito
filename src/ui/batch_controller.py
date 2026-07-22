from __future__ import annotations

import os
from pathlib import Path
from types import SimpleNamespace

from PySide6.QtCore import QObject, Property, QUrl, Signal, Slot
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import QFileDialog

from src.core.batch_processor import Job, QueueManager
from src.core.constants import (
    AUDIO_EXTENSIONS,
    COMPATIBILITY_RULES,
    DEFAULT_PRIORITY,
    EDITOR_FRIENDLY_CRITERIA,
    FAST_MODE_SUPPORTED_DOMAINS,
    FORMAT_MUXER_MAP,
    LANG_CODE_MAP,
    LANGUAGE_ORDER,
    VIDEO_EXTENSIONS,
)
from src.core.downloader import apply_yt_patch, extract_info_resilient
from src.core.processor import FFmpegProcessor

from .list_model import ObjectListModel
from .media_logic import build_media_choices, normalize_info, safe_filename
from .presets import PresetStore
from .settings_store import SettingsStore
from .workers import TaskPool


class _Value:
    def __init__(self, getter):
        self.get = getter


class _ImageRoute:
    def __init__(self, signal):
        self.signal = signal

    def _process_imported_files(self, paths):
        self.signal.emit(list(paths))


class _SingleAdapter:
    def __init__(self, presets: PresetStore):
        self.built_in_presets = presets.built_in
        self.custom_presets = presets.custom

    @staticmethod
    def sanitize_filename(value):
        return safe_filename(value)


class _RuntimeAdapter:
    """Contrato mínimo que QueueManager necesita, sin ningún widget de Tk."""

    def __init__(self, owner, ffmpeg, settings, presets):
        self.owner = owner
        self.ffmpeg_processor = ffmpeg
        self.cookies_mode_saved = settings.get("cookies_mode", "No usar")
        self.cookies_path = settings.get("cookies_path", "")
        self.selected_browser_saved = settings.get("selected_browser", "chrome")
        self.browser_profile_saved = settings.get("browser_profile", "")
        self.LANG_CODE_MAP = LANG_CODE_MAP
        self.LANGUAGE_ORDER = LANGUAGE_ORDER
        self.DEFAULT_PRIORITY = DEFAULT_PRIORITY
        self.EDITOR_FRIENDLY_CRITERIA = EDITOR_FRIENDLY_CRITERIA
        self.COMPATIBILITY_RULES = COMPATIBILITY_RULES
        self.FORMAT_MUXER_MAP = FORMAT_MUXER_MAP
        self.VIDEO_EXTENSIONS = VIDEO_EXTENSIONS
        self.AUDIO_EXTENSIONS = AUDIO_EXTENSIONS
        self.single_tab = _SingleAdapter(presets)
        self.image_tab = _ImageRoute(owner.imageFilesRequested)
        self.batch_tab = SimpleNamespace(
            auto_download_checkbox=_Value(lambda: int(owner._state["autoDownload"])),
            auto_send_to_it_checkbox=_Value(lambda: int(owner._state["autoSendImages"])),
            conflict_policy_menu=_Value(lambda: owner._state["conflictPolicy"]),
            output_path_entry=_Value(lambda: owner._state["outputPath"]),
            speed_limit_entry=_Value(lambda: owner._state["speedLimit"]),
            thumbnail_mode_var=_Value(lambda: owner._state["thumbnailMode"]),
            combined_audio_map={},
        )

    @staticmethod
    def after(_delay, callback, *args):
        callback(*args)


class BatchController(QObject):
    stateChanged = Signal()
    selectedChanged = Signal()
    selectedVideoChoicesChanged = Signal()
    selectedAudioChoicesChanged = Signal()
    queueEvent = Signal(str, str, str, float)
    imageFilesRequested = Signal("QStringList")
    notificationRequested = Signal(str, str, str)

    ROLES = [
        "jobId", "title", "status", "detail", "progress", "thumbnail", "jobType",
        "mode", "recode", "preset", "keepOriginal", "downloadThumbnail", "itemCount",
    ]

    def __init__(self, project_root, settings: SettingsStore, pool: TaskPool, presets: PresetStore, app_version: str, parent=None):
        super().__init__(parent)
        self.project_root = Path(project_root)
        self.settings = settings
        self.pool = pool
        self.presets = presets
        self.ffmpeg = FFmpegProcessor(app_version=app_version)
        self._state = {
            "url": "", "outputPath": settings.get("batch_download_path", str(Path.home() / "Downloads")),
            "globalMode": "Video+Audio", "globalQuality": "Mejor Calidad (Auto)",
            "autoDownload": False, "playlistAnalysis": settings.get("batch_playlist_analysis", True),
            "fastMode": settings.get("batch_fast_mode", False), "thumbnailMode": "normal",
            "autoSendImages": False, "conflictPolicy": "Renombrar", "createSubfolder": False,
            "subfolderName": "lote_xomacito", "speedLimit": "", "globalRecode": False,
            "globalPreset": "Archivo - H.265 Normal", "globalKeepOriginal": True,
            "allAudioTracks": False, "status": "Cola lista.", "progress": 0.0,
            "running": False, "analyzing": False, "selectedJobId": "",
        }
        self.jobs = ObjectListModel(self.ROLES, self)
        self._selected: dict = {}
        self._selected_video_choices: list[str] = []
        self._selected_audio_choices: list[str] = []
        self._pending_jobs: dict[str, Job] = {}
        self._playlist_entries: dict[str, list[dict]] = {}
        self.runtime = _RuntimeAdapter(self, self.ffmpeg, settings, presets)
        self.manager = QueueManager(self.runtime, self._queue_callback)
        self.queueEvent.connect(self._apply_queue_event)

    @Property("QVariantMap", notify=stateChanged)
    def state(self): return self._state

    @Property(QObject, constant=True)
    def model(self): return self.jobs

    @Property("QVariantMap", notify=selectedChanged)
    def selected(self): return self._selected

    @Property("QStringList", notify=selectedVideoChoicesChanged)
    def selectedVideoChoices(self): return self._selected_video_choices

    @Property("QStringList", notify=selectedAudioChoicesChanged)
    def selectedAudioChoices(self): return self._selected_audio_choices

    def _set_state(self, **values):
        changed = False
        for key, value in values.items():
            if self._state.get(key) != value:
                self._state[key] = value
                changed = True
        if changed: self.stateChanged.emit()

    @Slot(str, "QVariant")
    def setValue(self, key, value):
        if key not in self._state: return
        self._set_state(**{key: value})
        if key == "outputPath": self.settings.set("batch_download_path", str(value))
        elif key == "playlistAnalysis": self.settings.set("batch_playlist_analysis", bool(value))
        elif key == "fastMode": self.settings.set("batch_fast_mode", bool(value))

    @Slot()
    def chooseOutputFolder(self):
        folder = QFileDialog.getExistingDirectory(None, "Carpeta de la cola", self._state["outputPath"])
        if folder: self.setValue("outputPath", folder)

    @Slot()
    def analyze(self):
        url = str(self._state["url"]).strip()
        if not url or self._state["analyzing"]: return
        job = Job({"url": url, "title": "Analizando…"})
        self._pending_jobs[job.job_id] = job
        self.jobs.append(self._model_item(job, "ANALYZING", "Conectando…"))
        self._set_state(analyzing=True, status="Analizando enlace…")
        self.pool.submit(
            self._analyze_worker, url,
            on_result=lambda info, current=job: self._analysis_done(current, info),
            on_error=lambda message, detail, current=job: self._analysis_failed(current, message, detail),
        )

    def _cookie_options(self):
        mode = self.settings.get("cookies_mode", "No usar")
        if mode == "Archivo Manual..." and self.settings.get("cookies_path"):
            return {"cookiefile": self.settings.get("cookies_path")}, True
        if mode != "No usar":
            browser = self.settings.get("selected_browser", "chrome")
            profile = self.settings.get("browser_profile", "")
            return {"cookiesfrombrowser": ((browser, profile) if profile else (browser,))}, True
        return {}, False

    def _analyze_worker(self, url):
        playlist = bool(self._state["playlistAnalysis"])
        fast = playlist and bool(self._state["fastMode"]) and any(domain in url.lower() for domain in FAST_MODE_SUPPORTED_DOMAINS)
        options = {
            "no_warnings": True, "quiet": True, "noplaylist": not playlist,
            "ignoreerrors": True, "referer": url,
            "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        }
        if fast: options["extract_flat"] = "in_playlist"
        cookies, using = self._cookie_options()
        options.update(cookies)
        if using: options = apply_yt_patch(options)
        info = extract_info_resilient(url, options, download=False)
        if not info: raise RuntimeError("El sitio no devolvió información.")
        return normalize_info(info)

    def _analysis_done(self, job: Job, info: dict):
        self._pending_jobs.pop(job.job_id, None)
        is_playlist = info.get("_type") in {"playlist", "multi_video"} or bool(info.get("entries"))
        preset = self._state["globalPreset"] if self._state["globalRecode"] else "-"
        if is_playlist:
            entries = [entry for entry in info.get("entries", []) if entry]
            if not entries:
                self._analysis_failed(job, "La playlist está vacía.", "")
                return
            job.job_type = "PLAYLIST"
            job.analysis_data = info
            job.total_items = len(entries)
            job.config.update({
                "title": info.get("title") or "Playlist", "selected_indices": list(range(len(entries))),
                "playlist_mode": self._state["globalMode"], "playlist_quality": self._state["globalQuality"],
                "recode_enabled": bool(self._state["globalRecode"]), "recode_preset_name": preset,
                "recode_keep_original": bool(self._state["globalKeepOriginal"]),
            })
            self._playlist_entries[job.job_id] = entries
        else:
            choices = build_media_choices(info)
            video = choices["video"][0] if choices["video"] else {}
            audio = choices["audio"][0] if choices["audio"] else {}
            job.analysis_data = info
            job.config.update({
                "title": info.get("title") or f"video_{job.job_id[:8]}", "mode": self._state["globalMode"],
                "video_format_label": video.get("label", "-"), "audio_format_label": audio.get("label", "-"),
                "resolved_video_format_id": video.get("formatId"), "resolved_audio_format_id": audio.get("formatId"),
                "recode_enabled": bool(self._state["globalRecode"]), "recode_preset_name": preset,
                "recode_keep_original": bool(self._state["globalKeepOriginal"]), "recode_all_audio_tracks": bool(self._state["allAudioTracks"]),
            })
        self.manager.add_job(job)
        self._replace_job_model(job, "PENDING", "Listo para procesar", 0.0)
        self._set_state(analyzing=False, status="Análisis completado.", url="")
        self.selectJob(job.job_id)
        if self._state["autoDownload"] and not self.manager.user_paused:
            self.startQueue()

    def _analysis_failed(self, job, message, detail):
        self._pending_jobs.pop(job.job_id, None)
        self._replace_job_model(job, "FAILED", message, 0.0)
        self._set_state(analyzing=False, status="El análisis falló.")
        print(detail)
        self.notificationRequested.emit("error", "No se pudo analizar", message)

    @Slot()
    def importLocalFiles(self):
        paths, _ = QFileDialog.getOpenFileNames(None, "Importar archivos a la cola", "", "Multimedia (*.mp4 *.mkv *.webm *.mov *.avi *.m4a *.mp3 *.wav *.flac *.ogg *.opus);;Todos (*.*)")
        self.addLocalPaths(paths)

    @Slot("QStringList")
    def addLocalPaths(self, paths):
        for value in paths:
            path = QUrl(value).toLocalFile() if str(value).startswith("file:") else str(value)
            if not Path(path).is_file(): continue
            job = Job({
                "local_file_path": path, "title": Path(path).stem, "mode": self._state["globalMode"],
                "recode_enabled": True, "recode_preset_name": self._state["globalPreset"],
                "recode_keep_original": self._state["globalKeepOriginal"], "recode_all_audio_tracks": self._state["allAudioTracks"],
            }, "LOCAL_RECODE")
            info = self.ffmpeg.get_local_media_info(path)
            if not info:
                self.notificationRequested.emit("error", "Archivo inválido", path)
                continue
            job.analysis_data = info
            self.manager.add_job(job)

    @Slot()
    def importFolder(self):
        folder = QFileDialog.getExistingDirectory(None, "Importar carpeta")
        if not folder: return
        allowed = {"." + ext for ext in VIDEO_EXTENSIONS | AUDIO_EXTENSIONS}
        self.addLocalPaths([str(path) for path in Path(folder).rglob("*") if path.is_file() and path.suffix.lower() in allowed])

    @Slot()
    def startQueue(self):
        if self._state["createSubfolder"]:
            folder = Path(self._state["outputPath"]) / safe_filename(self._state["subfolderName"])
            folder.mkdir(parents=True, exist_ok=True)
            self.manager.subfolder_path = str(folder)
        elif hasattr(self.manager, "subfolder_path"):
            delattr(self.manager, "subfolder_path")
        self.manager.start_queue()
        self._set_state(running=True, status="Procesando cola…")

    @Slot()
    def pauseQueue(self):
        self.manager.pause_queue()
        self._set_state(running=False, status="Cola pausada.")

    @Slot()
    def toggleQueue(self):
        self.pauseQueue() if self._state["running"] else self.startQueue()

    def _queue_callback(self, job_id, status, detail, progress=0.0):
        self.queueEvent.emit(str(job_id), str(status), str(detail), float(progress or 0))

    @Slot(str, str, str, float)
    def _apply_queue_event(self, job_id, status, detail, progress):
        if job_id == "GLOBAL_PROGRESS":
            self._set_state(progress=progress, status=detail)
            return
        if job_id == "QUEUE_STATUS":
            self._set_state(running=status == "RUNNING")
            return
        job = self.manager.get_job_by_id(job_id)
        if job:
            job.status = status
            job.progress_message = detail
            self._replace_job_model(job, status, detail, progress)
            if self._state["selectedJobId"] == job_id: self.selectJob(job_id)

    def _model_item(self, job, status=None, detail="", progress=0.0):
        config = job.config
        return {
            "jobId": job.job_id, "title": config.get("title", "Sin título"),
            "status": status or job.status, "detail": detail or job.progress_message,
            "progress": progress, "thumbnail": (job.analysis_data or {}).get("thumbnail", ""),
            "jobType": job.job_type, "mode": config.get("mode", config.get("playlist_mode", "Video+Audio")),
            "recode": bool(config.get("recode_enabled")), "preset": config.get("recode_preset_name", "-"),
            "keepOriginal": bool(config.get("recode_keep_original", True)),
            "downloadThumbnail": bool(config.get("download_thumbnail", False)), "itemCount": job.total_items,
        }

    def _find_row(self, job_id):
        for index, item in enumerate(self.jobs.items()):
            if item["jobId"] == job_id: return index
        return -1

    def _replace_job_model(self, job, status, detail, progress=0.0):
        row = self._find_row(job.job_id)
        item = self._model_item(job, status, detail, progress)
        if row < 0: self.jobs.append(item)
        else: self.jobs.update_item(row, item)

    @Slot(str)
    def selectJob(self, job_id):
        job = self.manager.get_job_by_id(job_id) or self._pending_jobs.get(job_id)
        if not job: return
        self._set_state(selectedJobId=job_id)
        self._selected = self._model_item(job)
        choices = build_media_choices(job.analysis_data) if job.analysis_data and job.job_type == "DOWNLOAD" else {"video": [], "audio": []}
        self._selected_video_choices = [item["label"] for item in choices["video"]]
        self._selected_audio_choices = [item["label"] for item in choices["audio"]]
        self.selectedVideoChoicesChanged.emit(); self.selectedAudioChoicesChanged.emit(); self.selectedChanged.emit()

    @Slot(str, "QVariant")
    def setSelectedOption(self, key, value):
        job = self.manager.get_job_by_id(self._state["selectedJobId"])
        if not job: return
        mapping = {
            "title": "title", "mode": "mode", "preset": "recode_preset_name", "recode": "recode_enabled",
            "keepOriginal": "recode_keep_original", "downloadThumbnail": "download_thumbnail",
            "video": "video_format_label", "audio": "audio_format_label", "allAudioTracks": "recode_all_audio_tracks",
        }
        config_key = mapping.get(key)
        if not config_key: return
        job.config[config_key] = value
        self.selectJob(job.job_id)
        self._replace_job_model(job, job.status, job.progress_message)

    @Slot(str, "QVariantList", str, str)
    def configurePlaylist(self, job_id, indices, mode, quality):
        job = self.manager.get_job_by_id(job_id)
        if not job or job.job_type != "PLAYLIST": return
        valid = [int(index) for index in indices if 0 <= int(index) < len(self._playlist_entries.get(job_id, []))]
        job.config.update({"selected_indices": valid, "playlist_mode": mode, "playlist_quality": quality})
        job.total_items = len(valid)
        self._replace_job_model(job, job.status, f"{len(valid)} elementos seleccionados")

    @Slot(str, result="QVariantList")
    def playlistEntries(self, job_id):
        return [{"index": index, "title": entry.get("title") or entry.get("id") or f"Elemento {index + 1}", "thumbnail": entry.get("thumbnail", "")} for index, entry in enumerate(self._playlist_entries.get(job_id, []))]

    @Slot(str)
    def removeJob(self, job_id):
        self.manager.remove_job(job_id)
        self._pending_jobs.pop(job_id, None)
        self._playlist_entries.pop(job_id, None)
        row = self._find_row(job_id)
        if row >= 0: self.jobs.remove(row)
        if self._state["selectedJobId"] == job_id:
            self._selected = {}; self.selectedChanged.emit(); self._set_state(selectedJobId="")

    @Slot()
    def clearFinished(self):
        for item in list(self.jobs.items()):
            if item["status"] not in {"PENDING", "RUNNING", "ANALYZING"}: self.removeJob(item["jobId"])

    @Slot()
    def resetStatuses(self):
        for job in list(self.manager.jobs):
            if job.status in {"FAILED", "SKIPPED", "NO_AUDIO"}:
                job.status = "PENDING"; job.progress_message = "Listo para reintentar"
                self._replace_job_model(job, job.status, job.progress_message)
        self.manager.reset_progress()

    @Slot()
    def openOutput(self):
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(self._state["outputPath"])))

    def shutdown(self):
        self.manager.stop_worker_thread()
