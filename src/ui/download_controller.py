from __future__ import annotations

import io
import hashlib
import os
import re
import shutil
import subprocess
import sys
import tempfile
import threading
import time
from contextlib import redirect_stdout
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import requests
from PySide6.QtCore import QObject, Property, QStandardPaths, QUrl, Signal, Slot
from PySide6.QtGui import QColor, QDesktopServices
from PySide6.QtWidgets import QColorDialog, QFileDialog, QInputDialog, QMessageBox

from src.core.constants import AUDIO_EXTENSIONS, VIDEO_EXTENSIONS
from src.core.downloader import (
    apply_yt_patch,
    download_media,
    extract_info_resilient,
    extract_instagram_image_post_info,
    extract_instagram_reel_info,
    extract_x_media_post_info,
    instagram_image_post_info_from_metadata,
    is_instagram_post_url,
    is_instagram_reel_url,
    is_x_status_url,
)
from src.core.exceptions import UserCancelledError
from src.core.file_naming import next_available_media_stem, next_available_path
from src.core.processor import FFmpegProcessor, clean_and_convert_vtt_to_srt, pixel_format_has_alpha
from src.core.thumbnail_export import (
    PREMIERE_THUMBNAIL_FILTER,
    premiere_thumbnail_path,
    save_premiere_thumbnail,
)
from src.core.video_upscaler import VideoUpscaler
from src.core.ytdlp_runtime import (
    configure_ytdlp_options,
    friendly_ytdlp_error,
    is_youtube_url,
    safe_console_print,
)
from main import UPSCALING_DIR

from .dialog_broker import DialogBroker
from .media_logic import (
    build_media_choices,
    is_editor_mp4_selection,
    normalize_info,
    preferred_merge_container,
    safe_filename,
    seconds_from_time,
)
from .presets import ALPHA_PRESET, BUILT_IN_PRESETS, PresetStore, resolve_recode_parameters
from .settings_store import SettingsStore
from .waveform import render_waveform, waveform_target
from .filmstrip import filmstrip_target, render_filmstrip
from .media_preview_proxy import MediaPreviewProxy
from .workers import TaskPool


DEFAULT_OPTIONS: dict[str, Any] = {
    "downloadSubtitles": False,
    "cleanSubtitle": True,
    "keepFullSubtitle": False,
    "autoSaveThumbnail": False,
    "fragmentEnabled": False,
    "fragmentRanges": [],
    "startTime": "00:00:00",
    "endTime": "",
    "preciseClip": True,
    "forceFullDownload": False,
    "keepOriginalOnClip": False,
    "applyPreset": False,
    "keepOriginal": True,
    "embedThumbnail": False,
    "recodeVideoEnabled": False,
    "recodeAudioEnabled": False,
    "recodeProc": "CPU",
    "recodeCodecName": "H.265 (x265)",
    "recodeProfileName": "Calidad Equilibrada (CRF 20)",
    "recodeAudioCodecName": "AAC",
    "recodeAudioProfileName": "Buena Calidad (~192kbps)",
    "customBitrate": "8",
    "customGifFps": "15",
    "customGifWidth": "480",
    "fpsForceEnabled": False,
    "fpsValue": "60",
    "resolutionChangeEnabled": False,
    "resolutionPreset": "Personalizado",
    "resWidth": "1920",
    "resHeight": "1080",
    "maintainAspect": True,
    "noUpscaling": False,
    "useAllAudioTracks": False,
    "extractFramesEnabled": False,
    "extractType": "Todos los fotogramas",
    "extractFormat": "png",
    "extractFps": "",
    "extractJpgQuality": "2",
    "extractFolderName": "fotogramas",
    "keepOriginalExtract": True,
    "upscaleVideoEnabled": False,
    "upscaleEngine": "realesrgan-ncnn-vulkan",
    "upscaleModel": "Real-ESRGAN x4plus",
    "upscaleScale": "4x",
    "upscaleContainer": "Mismo que el original",
    "upscaleOutputName": "",
    "upscaleTile": "0",
    "upscaleDenoise": "-1",
    "upscaleTta": False,
    "upscaleConcurrency": "Automático",
    "upscaleTransparency": False,
}


def reveal_in_file_manager(target: str | Path) -> bool:
    """Abre la ubicación del resultado y, cuando es posible, lo selecciona."""
    path = Path(str(target)).expanduser()
    try:
        resolved = path.resolve(strict=False)
    except OSError:
        resolved = path

    if sys.platform == "win32":
        try:
            if resolved.is_file():
                subprocess.Popen(["explorer.exe", "/select,", str(resolved)])
            else:
                subprocess.Popen(["explorer.exe", str(resolved)])
            return True
        except OSError:
            pass

    folder = resolved if resolved.is_dir() else resolved.parent
    return bool(QDesktopServices.openUrl(QUrl.fromLocalFile(str(folder))))


def editor_mp4_fallback_options(options: dict) -> dict:
    """Fuerza un resultado H.264/AAC MP4 si el sitio sólo entregó WEBM/MKV."""
    compatible = {**options, **BUILT_IN_PRESETS["Web/Móvil - H.264 Normal"]}
    compatible.update({
        "mode": "Video+Audio",
        "keep_original_file": False,
    })
    return compatible


class DownloadController(QObject):
    stateChanged = Signal()
    optionsChanged = Signal()
    tagsChanged = Signal()
    videoChoicesChanged = Signal()
    audioChoicesChanged = Signal()
    subtitleLanguagesChanged = Signal()
    subtitleFormatsChanged = Signal()
    progressReported = Signal(float, str)
    navigateRequested = Signal(str)
    queueRequested = Signal(str)
    notificationRequested = Signal(str, str, str)
    successfulDownload = Signal(int)
    gachaSourceCompleted = Signal(str)

    def __init__(
        self,
        project_root: str | Path,
        settings: SettingsStore,
        pool: TaskPool,
        dialogs: DialogBroker,
        presets: PresetStore,
        app_version: str,
        parent=None,
    ):
        super().__init__(parent)
        self.project_root = Path(project_root)
        self.settings = settings
        self.pool = pool
        self.dialogs = dialogs
        self.presets = presets
        self.ffmpeg = FFmpegProcessor(app_version=app_version)
        cache_root = QStandardPaths.writableLocation(QStandardPaths.CacheLocation)
        self.waveform_dir = Path(cache_root or tempfile.gettempdir()) / "waveforms"
        self.waveform_dir.mkdir(parents=True, exist_ok=True)
        self.filmstrip_dir = Path(cache_root or tempfile.gettempdir()) / "filmstrips"
        self.filmstrip_dir.mkdir(parents=True, exist_ok=True)
        self.preview_dir = Path(cache_root or tempfile.gettempdir()) / "trim-previews"
        self.preview_dir.mkdir(parents=True, exist_ok=True)
        self._trim_preview_request = ""
        self.preview_proxy = MediaPreviewProxy()
        self.cancellation = threading.Event()
        output = settings.get("default_download_path") or str(Path.home() / "Downloads")
        self._state: dict[str, Any] = {
            "url": "", "outputPath": output, "title": "", "mode": "Video+Audio",
            "localFile": "", "thumbnailSource": "", "status": "Pega un enlace o importa un archivo.",
            "progress": 0.0, "busy": False, "analyzed": False, "lastOutput": "",
            "operationMode": "Rápido", "preset": settings.get("quick_preset_saved", "Archivo - H.265 Normal"),
            "selectedVideo": "", "selectedAudio": "", "selectedSubtitleLanguage": "",
            "selectedSubtitleFormat": "", "hasVideo": False, "hasAudio": False,
            "imagePost": False, "imageCount": 0, "imageFormat": "Original",
            "sourceHasAlpha": False, "duration": 0.0,
            "originalWidth": 0, "originalHeight": 0, "estimatedSize": "",
            "selectedTag": "Sin etiqueta", "selectedTagColor": "#6F7F8F",
            "effectiveOutputPath": output,
            "waveformSource": "", "waveformBusy": False, "waveformError": "",
            "trimPreviewSource": "", "trimPreviewHasAudio": False,
            "trimPreviewOffset": 0.0, "trimPreviewBusy": False,
            "trimPreviewFallback": False, "trimPreviewError": "",
            "trimFilmstripSource": "", "trimFilmstripBusy": False, "trimFilmstripError": "",
        }
        self._tags = self._load_download_tags()
        saved_tag = str(settings.get("selected_download_tag", "Sin etiqueta"))
        selected_tag = next((tag for tag in self._tags if tag["name"] == saved_tag), None)
        if selected_tag:
            self._state.update({
                "selectedTag": selected_tag["name"],
                "selectedTagColor": selected_tag["color"],
                "effectiveOutputPath": selected_tag["folder"],
            })
        saved_recode = settings.get("recode_settings", {})
        self._options = {**DEFAULT_OPTIONS}
        if isinstance(saved_recode, dict):
            legacy_map = {
                "keep_original": "keepOriginal",
                "video_codec": "recodeCodecName",
                "video_profile": "recodeProfileName",
                "video_audio_codec": "recodeAudioCodecName",
                "video_audio_profile": "recodeAudioProfileName",
                "embed_thumbnail": "embedThumbnail",
            }
            for key, value in saved_recode.items():
                mapped = legacy_map.get(key, key)
                if mapped in self._options:
                    self._options[mapped] = value
        self._video_choices: list[str] = []
        self._audio_choices: list[str] = []
        self._subtitle_languages: list[str] = []
        self._subtitle_formats: list[str] = []
        self._video_map: dict[str, dict] = {}
        self._audio_map: dict[str, dict] = {}
        self._subtitle_map: dict[str, list[dict]] = {}
        self._subtitle_language_code: dict[str, str] = {}
        self._analysis_info: dict | None = None
        self._image_post: dict | None = None
        self._active_worker = None
        self._current_counts_as_download = False
        self._last_download_was_partial = False
        self.progressReported.connect(self._apply_progress)
        self.settings.changed.connect(self._on_settings_changed)

    @Property("QVariantMap", notify=stateChanged)
    def state(self):
        return self._state

    @Property("QVariantMap", notify=optionsChanged)
    def options(self):
        return self._options

    @Property("QStringList", notify=tagsChanged)
    def downloadTags(self):
        return ["Sin etiqueta", *[tag["name"] for tag in self._tags]]

    @Property("QStringList", notify=videoChoicesChanged)
    def videoChoices(self):
        return self._video_choices

    @Property("QStringList", notify=audioChoicesChanged)
    def audioChoices(self):
        return self._audio_choices

    @Property("QStringList", notify=subtitleLanguagesChanged)
    def subtitleLanguages(self):
        return self._subtitle_languages

    @Property("QStringList", notify=subtitleFormatsChanged)
    def subtitleFormats(self):
        return self._subtitle_formats

    def _set_state(self, **updates):
        changed = False
        for key, value in updates.items():
            if self._state.get(key) != value:
                self._state[key] = value
                changed = True
        if changed:
            self.stateChanged.emit()

    @Slot(str, "QVariant")
    def setValue(self, key: str, value):
        if key not in self._state:
            return
        self._set_state(**{key: value})
        if key == "outputPath":
            self.settings.set("default_download_path", str(value))
            self._refresh_tag_state()
        elif key == "preset":
            self.settings.set("quick_preset_saved", str(value))
        elif key == "mode":
            self._ensure_preset_for_mode(str(value))
        elif key == "selectedTag":
            self.selectDownloadTag(str(value))
        elif key == "selectedSubtitleLanguage":
            self._refresh_subtitle_formats(str(value))
        elif key == "selectedAudio":
            self.prepareWaveform()
        elif key == "selectedVideo":
            self._refresh_trim_preview_source()
            self.prepareTrimFilmstrip()

    @Slot(str, "QVariant")
    def setOption(self, key: str, value):
        if key == "preciseClip":
            value = True
        if key not in self._options or self._options.get(key) == value:
            return
        self._options[key] = value
        self.optionsChanged.emit()
        persisted = {
            "keep_original": self._options["keepOriginal"],
            "video_codec": self._options["recodeCodecName"],
            "video_profile": self._options["recodeProfileName"],
            "video_audio_codec": self._options["recodeAudioCodecName"],
            "video_audio_profile": self._options["recodeAudioProfileName"],
            "embed_thumbnail": self._options["embedThumbnail"],
        }
        self.settings.set("recode_settings", persisted)

    @Slot(str, str)
    def addFragment(self, start_time: str, end_time: str):
        """Añade a la cola un corte válido sin duplicarlo."""
        error = self._fragment_range_error(start_time, end_time)
        if error:
            self.notificationRequested.emit("warning", "Revisa el fragmento", error)
            return
        fragment = {
            "startTime": str(start_time).strip(),
            "endTime": str(end_time).strip(),
        }
        ranges = [dict(item) for item in self._options.get("fragmentRanges", []) if isinstance(item, dict)]
        if any(
            item.get("startTime") == fragment["startTime"]
            and item.get("endTime") == fragment["endTime"]
            for item in ranges
        ):
            self.notificationRequested.emit("info", "Fragmento ya añadido", "Ese intervalo ya está en la lista.")
            return
        if len(ranges) >= 24:
            self.notificationRequested.emit("warning", "Límite alcanzado", "Puedes procesar hasta 24 fragmentos a la vez.")
            return
        ranges.append(fragment)
        ranges.sort(key=lambda item: self._parse_clock(item.get("startTime", "")) or 0)
        self._options["fragmentRanges"] = ranges
        self._options["fragmentEnabled"] = True
        self.optionsChanged.emit()

    @Slot(int)
    def removeFragment(self, index: int):
        ranges = [dict(item) for item in self._options.get("fragmentRanges", []) if isinstance(item, dict)]
        if index < 0 or index >= len(ranges):
            return
        ranges.pop(index)
        self._options["fragmentRanges"] = ranges
        self.optionsChanged.emit()

    @Slot(int)
    def useFragment(self, index: int):
        ranges = self._options.get("fragmentRanges", [])
        if index < 0 or index >= len(ranges) or not isinstance(ranges[index], dict):
            return
        fragment = ranges[index]
        self._options["startTime"] = str(fragment.get("startTime") or "00:00:00")
        self._options["endTime"] = str(fragment.get("endTime") or "")
        self.optionsChanged.emit()

    @Slot()
    def clearFragments(self):
        if not self._options.get("fragmentRanges"):
            return
        self._options["fragmentRanges"] = []
        self.optionsChanged.emit()

    def _ensure_preset_for_mode(self, mode: str):
        if mode == "Imágenes":
            return
        """Mantiene sincronizados el preset visible y el preset que se ejecutará."""
        presets = self.presets.videoPresets if mode == "Video+Audio" else self.presets.audioPresets
        if presets and self._state["preset"] not in presets:
            self._set_state(preset=presets[0])

    def _load_download_tags(self) -> list[dict[str, str]]:
        saved = self.settings.get("download_tags", [])
        tags: list[dict[str, str]] = []
        seen: set[str] = set()
        if not isinstance(saved, list):
            return tags
        for raw in saved:
            if not isinstance(raw, dict):
                continue
            name = str(raw.get("name") or "").strip()
            folder = str(raw.get("folder") or "").strip()
            color = str(raw.get("color") or "#22D3EE")
            if not name or not folder or name.casefold() in seen:
                continue
            if not QColor(color).isValid():
                color = "#22D3EE"
            seen.add(name.casefold())
            tags.append({"name": name, "folder": folder, "color": color})
        return tags

    def _selected_tag(self) -> dict[str, str] | None:
        selected = str(self._state.get("selectedTag") or "")
        return next((tag for tag in self._tags if tag["name"] == selected), None)

    def _refresh_tag_state(self):
        tag = self._selected_tag()
        self._set_state(
            selectedTag=tag["name"] if tag else "Sin etiqueta",
            selectedTagColor=tag["color"] if tag else "#6F7F8F",
            effectiveOutputPath=tag["folder"] if tag else self._state["outputPath"],
        )

    @Slot(str)
    def selectDownloadTag(self, name: str):
        """Selecciona etiqueta, color y carpeta en una sola actualización visible."""
        requested = str(name or "Sin etiqueta")
        tag = next((item for item in self._tags if item["name"] == requested), None)
        self._set_state(
            selectedTag=tag["name"] if tag else "Sin etiqueta",
            selectedTagColor=tag["color"] if tag else "#6F7F8F",
            effectiveOutputPath=tag["folder"] if tag else self._state["outputPath"],
        )
        self.settings.set("selected_download_tag", self._state["selectedTag"])

    def _save_tags(self):
        self.settings.set("download_tags", self._tags)
        self.settings.set("selected_download_tag", self._state["selectedTag"])
        self.tagsChanged.emit()
        self._refresh_tag_state()

    @Slot(str, "QVariant")
    def _on_settings_changed(self, key, _value):
        """Mantiene las mismas etiquetas activas en Descargar y Cola."""
        if key == "download_tags":
            self._tags = self._load_download_tags()
            self.tagsChanged.emit()
            self._refresh_tag_state()
        elif key == "selected_download_tag":
            self._set_state(selectedTag=str(self.settings.get(key, "Sin etiqueta")))
            self._refresh_tag_state()

    @Slot()
    def createDownloadTag(self):
        name, accepted = QInputDialog.getText(
            None, "Nueva etiqueta", "Nombre (por ejemplo: SFX, Música o Material):",
        )
        name = str(name).strip()
        if not accepted or not name:
            return
        if any(tag["name"].casefold() == name.casefold() for tag in self._tags):
            self.notificationRequested.emit("warning", "La etiqueta ya existe", name)
            return
        folder = QFileDialog.getExistingDirectory(
            None, f"Carpeta para {name}", self._state["outputPath"],
        )
        if not folder:
            return
        color = QColorDialog.getColor(QColor("#22D3EE"), None, f"Color de {name}")
        if not color.isValid():
            return
        self._tags.append({"name": name, "folder": folder, "color": color.name().upper()})
        self._set_state(selectedTag=name)
        self._save_tags()
        self.notificationRequested.emit(
            "success", "Etiqueta guardada", f"{name} enviará tus archivos a {folder}",
        )

    @Slot()
    def deleteSelectedTag(self):
        tag = self._selected_tag()
        if not tag:
            return
        choice = QMessageBox.question(
            None,
            "Eliminar etiqueta",
            f"Se eliminará «{tag['name']}». Los archivos existentes no se modificarán.",
            QMessageBox.Yes | QMessageBox.Cancel,
            QMessageBox.Cancel,
        )
        if choice != QMessageBox.Yes:
            return
        self._tags = [item for item in self._tags if item["name"] != tag["name"]]
        self._set_state(selectedTag="Sin etiqueta")
        self._save_tags()

    @Slot()
    def chooseOutputFolder(self):
        tag = self._selected_tag()
        current = tag["folder"] if tag else self._state["outputPath"]
        title = f"Carpeta para {tag['name']}" if tag else "Carpeta de salida"
        folder = QFileDialog.getExistingDirectory(None, title, current)
        if folder:
            if tag:
                tag["folder"] = folder
                self._save_tags()
            else:
                self.setValue("outputPath", folder)
                self._refresh_tag_state()

    def _refresh_trim_preview_source(self):
        """Expone una fuente reproducible sin descargar el archivo completo."""
        self._trim_preview_request = ""
        local_file = str(self._state.get("localFile") or "")
        if local_file and Path(local_file).is_file():
            self._set_state(
                trimPreviewSource=QUrl.fromLocalFile(local_file).toString(),
                trimPreviewHasAudio=bool(self._state.get("hasAudio")),
                trimPreviewOffset=0.0, trimPreviewBusy=False,
                trimPreviewFallback=False, trimPreviewError="",
            )
            return

        selected = dict(self._video_map.get(self._state.get("selectedVideo"), {}) or {})
        candidates = [selected, *self._video_map.values()]
        def progressive_combined(entry):
            raw_entry = dict(entry.get("raw") or {})
            source_url = str(raw_entry.get("url") or "").lower()
            protocol = str(raw_entry.get("protocol") or "").lower()
            return (
                entry.get("combined")
                and source_url
                and "m3u8" not in source_url
                and "dash" not in protocol
                and "m3u8" not in protocol
                and protocol not in {"http_dash_segments", "mhtml"}
            )
        playable = next(
            (entry for entry in candidates if progressive_combined(entry)),
            None,
        ) or next(
            (
                entry for entry in candidates
                if entry.get("combined") and str((entry.get("raw") or {}).get("url") or "")
            ),
            selected,
        )
        raw = dict(playable.get("raw") or {})
        source = str(raw.get("url") or "")
        preview_source = self.preview_proxy.url_for(source, dict(raw.get("http_headers") or {})) if source else ""
        self._set_state(
            trimPreviewSource=preview_source,
            trimPreviewHasAudio=bool(playable.get("combined")),
            trimPreviewOffset=0.0, trimPreviewBusy=False,
            trimPreviewFallback=False, trimPreviewError="",
        )

    @Slot()
    def refreshTrimPreview(self):
        self._refresh_trim_preview_source()

    @Slot()
    def prepareFallbackTrimPreview(self):
        """Crea un MP4 local corto cuando Qt no acepta el flujo web directo."""
        local_file = str(self._state.get("localFile") or "")
        if local_file:
            self._refresh_trim_preview_source()
            return
        playable, raw = self._selected_trim_video()
        source = str(raw.get("url") or "")
        if not source:
            self._set_state(
                trimPreviewBusy=False,
                trimPreviewError="El sitio no entregó un flujo reproducible.",
            )
            return
        start = self._parse_clock(str(self._options.get("startTime") or "")) or 0.0
        end = self._parse_clock(str(self._options.get("endTime") or ""))
        total = float(self._state.get("duration") or 0.0)
        if end is None or end <= start:
            end = total if total > start else start + 30.0
        duration = max(0.5, end - start)
        request_seed = (
            f"{self._current_filmstrip_key()}|full-preview-proxy|"
            f"{raw.get('format_id') or playable.get('formatId') or ''}"
        )
        request_key = hashlib.sha256(request_seed.encode("utf-8", "ignore")).hexdigest()
        target = self.preview_dir / f"{request_key}.mp4"
        self._trim_preview_request = request_key
        if target.is_file() and target.stat().st_size > 4096:
            self._fallback_trim_preview_ready(request_key, 0.0, str(target))
            return
        self._set_state(
            trimPreviewBusy=True, trimPreviewFallback=True, trimPreviewError="",
        )
        cookie_options, using_cookies = self._cookie_options()
        self.pool.submit(
            self._remote_fallback_trim_preview_worker,
            self.ffmpeg.ffmpeg_path,
            str(self._state.get("url") or ""),
            source,
            target,
            0.0,
            max(0.5, total or duration),
            dict(raw.get("http_headers") or {}),
            str(raw.get("format_id") or playable.get("formatId") or ""),
            cookie_options if using_cookies else {},
            on_result=lambda path: self._fallback_trim_preview_ready(request_key, 0.0, path),
            on_error=lambda message, _detail: self._fallback_trim_preview_failed(request_key, message),
        )

    def _remote_fallback_trim_preview_worker(
        self,
        ffmpeg_path: str,
        page_url: str,
        direct_source: str,
        target: Path,
        start: float,
        duration: float,
        headers: dict[str, str],
        format_id: str,
        cookie_options: dict[str, Any],
    ) -> str:
        """Prepara un proxy completo y estable para poder mover libremente el cabezal."""
        if direct_source:
            safe_console_print(
                "Preparando un proxy completo y ligero con el descargador nativo."
            )
        if not page_url:
            raise RuntimeError("No se conservó el enlace original para renovar la vista previa.")

        # download_ranges usa el descargador externo de FFmpeg. YouTube puede
        # entregar una URL firmada que funciona en el navegador pero devuelve
        # 403 cuando FFmpeg intenta abrirla. Descargamos una sola copia MP4
        # progresiva y pequeña con el cliente HTTP nativo de yt-dlp; después el
        # recorte y la reproducción suceden enteramente desde disco.
        source_key = hashlib.sha256(page_url.encode("utf-8", "ignore")).hexdigest()
        preview_root = target.parent / "sources" / source_key
        preview_root.mkdir(parents=True, exist_ok=True)

        def downloaded_candidates() -> list[Path]:
            return [
                path for path in preview_root.iterdir()
                if path.is_file()
                and path.suffix.lower() not in {".part", ".ytdl", ".json"}
                and path.stat().st_size > 4096
            ]

        candidates = downloaded_candidates()
        if not candidates:
            combined_proxy = (
                "best[height<=480][ext=mp4][vcodec!=none][acodec!=none]/"
                "best[height<=480][vcodec!=none][acodec!=none]/"
                "worst[ext=mp4][vcodec!=none][acodec!=none]/"
                "worst[vcodec!=none][acodec!=none]"
            )
            base_options: dict[str, Any] = {
                "quiet": True,
                "no_warnings": True,
                "noplaylist": True,
                "playlist_items": "1",
                "format": combined_proxy,
                "outtmpl": str(preview_root / "source.%(ext)s"),
                "continuedl": True,
                "retries": 3,
                "fragment_retries": 3,
                "socket_timeout": 25,
            }
            if is_youtube_url(page_url):
                # El cliente automático puede entregar enlaces ANDROID_VR que
                # el CDN rechaza con 403. web_embedded produjo el proxy válido
                # en el mismo equipo y evita primero repetir esa ruta fallida.
                base_options["extractor_args"] = {
                    "youtube": {"player_client": ["web_embedded"]},
                }
            configured = configure_ytdlp_options({**base_options, **cookie_options})
            try:
                extract_info_resilient(page_url, configured, download=True)
            except Exception:
                # Conserva un segundo intento limpio por si un sitio no admite
                # el selector limitado pero sí ofrece otro formato combinado.
                fallback = dict(configured)
                fallback["format"] = "best[vcodec!=none][acodec!=none]/worst"
                try:
                    extract_info_resilient(page_url, fallback, download=True)
                except Exception as fallback_error:
                    raise RuntimeError(
                        "YouTube rechazó también la copia ligera. El video puede requerir Cookies, "
                        "tener restricción regional, de edad o de privacidad."
                    ) from fallback_error
            candidates = downloaded_candidates()

        if not candidates:
            raise RuntimeError("La copia ligera terminó sin un archivo de video válido.")
        downloaded = max(candidates, key=lambda path: path.stat().st_size)
        if downloaded.suffix.lower() == ".mp4":
            # El proxy progresivo H.264/AAC se reproduce directamente. Evitar
            # una segunda recodificación reduce mucho la espera y, al contener
            # el video completo, permite mover la selección sin quedar fuera.
            return str(downloaded)
        return self._fallback_trim_preview_worker(
            ffmpeg_path, str(downloaded), target, 0.0, duration, {},
        )

    @staticmethod
    def _fallback_trim_preview_worker(
        ffmpeg_path: str,
        source: str,
        target: Path,
        start: float,
        duration: float,
        headers: dict[str, str],
    ) -> str:
        target.parent.mkdir(parents=True, exist_ok=True)
        temporary = target.with_name(f"{target.stem}.part.mp4")
        temporary.unlink(missing_ok=True)
        header_args: list[str] = []
        if headers:
            header_blob = "".join(f"{key}: {value}\r\n" for key, value in headers.items())
            header_args = ["-headers", header_blob]
        creationflags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
        input_args = [
            str(ffmpeg_path), "-hide_banner", "-loglevel", "error", "-y",
            "-ss", f"{start:.3f}", *header_args, "-i", source,
            "-t", f"{duration:.3f}", "-map", "0:v:0", "-map", "0:a:0?",
        ]
        attempts = [
            [
                *input_args,
                "-vf", "scale=960:-2:force_original_aspect_ratio=decrease",
                "-c:v", "libx264", "-preset", "ultrafast", "-crf", "28",
                "-c:a", "aac", "-b:a", "128k", "-movflags", "+faststart",
                str(temporary),
            ],
            [*input_args, "-c", "copy", "-movflags", "+faststart", str(temporary)],
        ]
        last_error = ""
        for command in attempts:
            temporary.unlink(missing_ok=True)
            completed = subprocess.run(
                command, capture_output=True, text=True, errors="ignore",
                creationflags=creationflags,
            )
            if completed.returncode == 0 and temporary.is_file() and temporary.stat().st_size > 4096:
                os.replace(temporary, target)
                return str(target)
            last_error = (completed.stderr or completed.stdout or "FFmpeg no pudo abrir el flujo").strip()
        temporary.unlink(missing_ok=True)
        raise RuntimeError(last_error[-800:])

    def _fallback_trim_preview_ready(self, request_key: str, offset: float, path: str):
        if request_key != self._trim_preview_request or not Path(path).is_file():
            return
        self._set_state(
            trimPreviewSource=QUrl.fromLocalFile(str(path)).toString(),
            trimPreviewHasAudio=True, trimPreviewOffset=float(offset),
            trimPreviewBusy=False, trimPreviewFallback=True, trimPreviewError="",
        )
        # La tira y la forma de onda reutilizan este proxy local. Así no abren
        # de nuevo el enlace remoto ni descargan copias temporales separadas.
        self.prepareTrimFilmstrip()
        self.prepareWaveform()

    def _fallback_trim_preview_failed(self, request_key: str, message: str):
        if request_key != self._trim_preview_request:
            return
        friendly = str(message or "").strip()
        if not friendly or "YouTube" not in friendly:
            friendly = (
                "No se pudo crear la copia local. El video puede requerir Cookies, "
                "tener restricción regional, de edad o de privacidad."
            )
        self._set_state(
            trimPreviewBusy=False,
            trimPreviewError=friendly,
        )

    def _selected_trim_video(self) -> tuple[dict, dict]:
        selected = dict(self._video_map.get(self._state.get("selectedVideo"), {}) or {})
        candidates = [selected, *self._video_map.values()]
        playable = next(
            (
                dict(entry) for entry in candidates
                if entry.get("combined")
                and "m3u8" not in str((entry.get("raw") or {}).get("url") or "").lower()
                and "dash" not in str((entry.get("raw") or {}).get("protocol") or "").lower()
                and "m3u8" not in str((entry.get("raw") or {}).get("protocol") or "").lower()
            ),
            None,
        ) or next(
            (
                dict(entry) for entry in candidates
                if str((entry.get("raw") or {}).get("url") or "")
            ),
            selected,
        )
        return playable, dict(playable.get("raw") or {})

    def _current_filmstrip_key(self) -> str:
        local_path = str(self._state.get("localFile") or "")
        if local_path and Path(local_path).is_file():
            local = Path(local_path)
            stat = local.stat()
            return f"{local.resolve()}|{stat.st_mtime_ns}|{stat.st_size}"
        return f"{self._state.get('url')}|{self._state.get('selectedVideo')}"

    def _local_trim_preview_path(self) -> str:
        if not self._state.get("trimPreviewFallback"):
            return ""
        preview_url = QUrl(str(self._state.get("trimPreviewSource") or ""))
        candidate = Path(preview_url.toLocalFile()) if preview_url.isLocalFile() else None
        return str(candidate) if candidate and candidate.is_file() else ""

    @Slot()
    def prepareTrimFilmstrip(self):
        """Genera miniaturas cronológicas para seleccionar el fragmento de video."""
        duration = float(self._state.get("duration") or 0)
        if not self._state.get("analyzed") or not self._state.get("hasVideo") or duration <= 0:
            self._set_state(trimFilmstripSource="", trimFilmstripBusy=False, trimFilmstripError="")
            return
        if self._state.get("trimFilmstripBusy"):
            return

        local_path = str(self._state.get("localFile") or "")
        preview_path = self._local_trim_preview_path()
        render_locally = bool(local_path or preview_path)
        headers: dict[str, str] = {}
        format_id = ""
        if render_locally:
            source = local_path or preview_path
            if not Path(source).is_file():
                self._set_state(
                    trimFilmstripSource="", trimFilmstripBusy=False,
                    trimFilmstripError="El archivo ya no está disponible.",
                )
                return
        else:
            playable, raw = self._selected_trim_video()
            source = str(raw.get("url") or "")
            headers = dict(raw.get("http_headers") or {})
            format_id = str(playable.get("formatId") or raw.get("format_id") or "")
            if not source:
                self._set_state(
                    trimFilmstripSource="", trimFilmstripBusy=False,
                    trimFilmstripError="El sitio no ofrece fotogramas de previsualización.",
                )
                return

        request_key = f"{self._current_filmstrip_key()}|filmstrip-v4-64"
        target = filmstrip_target(self.filmstrip_dir, request_key)
        if target.is_file() and target.stat().st_size > 256:
            self._set_state(
                trimFilmstripSource=QUrl.fromLocalFile(str(target)).toString(),
                trimFilmstripBusy=False,
                trimFilmstripError="",
            )
            return

        self._set_state(trimFilmstripSource="", trimFilmstripBusy=True, trimFilmstripError="")
        if render_locally:
            self.pool.submit(
                render_filmstrip,
                self.ffmpeg.ffmpeg_path,
                source,
                target,
                duration,
                headers,
                on_result=lambda path: self._download_filmstrip_ready(request_key, path),
                on_error=lambda message, _detail: self._download_filmstrip_failed(request_key, message),
            )
            return

        cookie_options, using_cookies = self._cookie_options()
        self.pool.submit(
            self._remote_filmstrip_worker,
            str(self._state.get("url") or ""),
            source,
            format_id,
            target,
            duration,
            headers,
            cookie_options,
            using_cookies,
            on_result=lambda path: self._download_filmstrip_ready(request_key, path),
            on_error=lambda message, _detail: self._download_filmstrip_failed(request_key, message),
        )

    def _remote_filmstrip_worker(
        self,
        page_url: str,
        direct_source: str,
        format_id: str,
        target: Path,
        duration: float,
        headers: dict[str, str],
        cookie_options: dict[str, Any],
        using_cookies: bool,
    ) -> str:
        """Prueba la URL directa y renueva el video temporal si el sitio la expiró."""
        try:
            return render_filmstrip(
                self.ffmpeg.ffmpeg_path, direct_source, target, duration, headers,
            )
        except Exception as direct_error:
            safe_console_print(
                f"Filmstrip directo rechazado; creando copia temporal: {direct_error}"
            )
        if not page_url:
            raise RuntimeError("No hay un enlace original para recuperar los fotogramas.")

        with tempfile.TemporaryDirectory(prefix="xomacito-filmstrip-") as temporary_dir:
            preview_root = Path(temporary_dir)
            base_options: dict[str, Any] = {
                "quiet": True,
                "no_warnings": True,
                "noplaylist": True,
                "playlist_items": "1",
                "format": format_id or "bestvideo/best",
                "outtmpl": str(preview_root / "video.%(ext)s"),
                "overwrites": True,
            }
            configured = configure_ytdlp_options(base_options)
            if using_cookies:
                configured = apply_yt_patch({**configured, **cookie_options})
            try:
                extract_info_resilient(page_url, configured, download=True)
            except Exception as selected_error:
                if not format_id:
                    raise RuntimeError(
                        "El sitio no permitió recuperar los fotogramas del video."
                    ) from selected_error
                fallback = dict(configured)
                fallback["format"] = "bestvideo/best"
                extract_info_resilient(page_url, fallback, download=True)

            candidates = [
                path for path in preview_root.iterdir()
                if path.is_file() and path.suffix.lower() not in {".part", ".ytdl"}
            ]
            if not candidates:
                raise RuntimeError("El video temporal terminó sin fotogramas reproducibles.")
            preview = max(candidates, key=lambda path: path.stat().st_size)
            return render_filmstrip(
                self.ffmpeg.ffmpeg_path, str(preview), target, duration,
            )

    def _download_filmstrip_ready(self, request_key: str, path: str):
        expected_key = f"{self._current_filmstrip_key()}|filmstrip-v4-64"
        if request_key != expected_key:
            return
        self._set_state(
            trimFilmstripSource=QUrl.fromLocalFile(str(path)).toString(),
            trimFilmstripBusy=False,
            trimFilmstripError="",
        )

    def _download_filmstrip_failed(self, request_key: str, _message: str):
        expected_key = f"{self._current_filmstrip_key()}|filmstrip-v4-64"
        if request_key != expected_key:
            return
        self._set_state(
            trimFilmstripSource="",
            trimFilmstripBusy=False,
            trimFilmstripError="No se pudieron generar las miniaturas de este video.",
        )

    @Slot()
    def chooseLocalFile(self):
        path, _ = QFileDialog.getOpenFileName(
            None, "Importar archivo para procesar", "",
            "Multimedia (*.mp4 *.mkv *.webm *.mov *.flv *.avi *.gif *.m4a *.mp3 *.ogg *.opus *.flac *.wav);;Todos (*.*)",
        )
        if path:
            self.importLocalPath(path)

    @Slot(str)
    def importLocalPath(self, value: str):
        path = QUrl(value).toLocalFile() if value.startswith("file:") else value
        if not path or not Path(path).is_file():
            return
        self.cancel()
        self._clear_analysis_lists()
        self._set_state(
            localFile=str(Path(path)), url="", title=Path(path).stem, busy=True,
            analyzed=False, progress=0.0, status="Analizando archivo local…",
            thumbnailSource="", imagePost=False, waveformSource="", waveformBusy=False,
            waveformError="", trimPreviewSource="", trimPreviewHasAudio=False,
            trimPreviewOffset=0.0, trimPreviewBusy=False, trimPreviewFallback=False,
            trimPreviewError="",
            trimFilmstripSource="", trimFilmstripBusy=False, trimFilmstripError="",
        )
        self._active_worker = self.pool.submit(
            self._analyze_local_worker, str(Path(path)),
            on_result=self._apply_local_analysis,
            on_error=lambda message, detail: self._operation_error(f"No se pudo analizar el archivo: {message}", detail),
        )

    def _analyze_local_worker(self, path: str):
        info = self.ffmpeg.get_local_media_info(path)
        # Algunos reels públicos devuelven metadatos incompletos a yt-dlp sin
        # lanzar una excepción. En ese caso todavía podemos recuperar el MP4
        # expuesto por la página pública de Instagram.
        if not info and instagram_reel:
            try:
                info = extract_instagram_reel_info(
                    url,
                    ydl_options=options,
                )
            except Exception as fallback_error:
                logs.append(f"Fallback de reel de Instagram: {fallback_error}")

        if not info:
            raise RuntimeError("FFprobe no devolvió información del archivo.")
        streams = info.get("streams", [])
        fmt = info.get("format", {})
        duration = float(fmt.get("duration") or 0)
        video_streams = [stream for stream in streams if stream.get("codec_type") == "video"]
        audio_streams = [stream for stream in streams if stream.get("codec_type") == "audio"]
        first_video = video_streams[0] if video_streams else {}
        thumbnail = self.ffmpeg.get_frame_from_video(path, duration) if video_streams else ""
        source_has_alpha = pixel_format_has_alpha(first_video.get("pix_fmt"))
        return {
            "media": info, "duration": duration, "videoStreams": video_streams,
            "audioStreams": audio_streams, "thumbnail": thumbnail or "",
            "sourceHasAlpha": source_has_alpha,
        }

    @Slot()
    def resetSource(self):
        if self._state["busy"]:
            return
        self._analysis_info = None
        self._image_post = None
        self._clear_analysis_lists()
        self._set_state(
            localFile="", title="", analyzed=False, thumbnailSource="", imagePost=False, imageCount=0,
            hasVideo=False, hasAudio=False, sourceHasAlpha=False, status="Pega un enlace o importa un archivo.",
            waveformSource="", waveformBusy=False, waveformError="",
            trimPreviewSource="", trimPreviewHasAudio=False,
            trimPreviewOffset=0.0, trimPreviewBusy=False, trimPreviewFallback=False,
            trimPreviewError="",
            trimFilmstripSource="", trimFilmstripBusy=False, trimFilmstripError="",
        )

    @Slot()
    def analyze(self):
        url = str(self._state["url"]).strip()
        if not url:
            self.notificationRequested.emit("warning", "Falta el enlace", "Pega un enlace antes de analizar.")
            return
        if self._state["busy"]:
            return
        self.cancellation.clear()
        self._analysis_info = None
        self._image_post = None
        self._clear_analysis_lists()
        self._set_state(
            localFile="", title="Analizando…", busy=True, analyzed=False, progress=-1.0,
            status="Contactando el sitio y leyendo formatos…", thumbnailSource="", imagePost=False, imageCount=0,
            waveformSource="", waveformBusy=False, waveformError="",
            trimPreviewSource="", trimPreviewHasAudio=False,
            trimPreviewOffset=0.0, trimPreviewBusy=False, trimPreviewFallback=False,
            trimPreviewError="",
            trimFilmstripSource="", trimFilmstripBusy=False, trimFilmstripError="",
        )
        self._active_worker = self.pool.submit(
            self._analyze_url_worker, url,
            on_result=self._apply_url_analysis,
            on_error=lambda message, detail: self._operation_error(f"Análisis fallido: {message}", detail),
        )

    def _cookie_options(self) -> tuple[dict, bool]:
        mode = self.settings.get("cookies_mode", "No usar")
        options: dict[str, Any] = {}
        if mode == "Archivo Manual..." and self.settings.get("cookies_path"):
            options["cookiefile"] = self.settings.get("cookies_path")
            return options, True
        if mode != "No usar":
            browser = self.settings.get("selected_browser", "chrome")
            profile = self.settings.get("browser_profile", "")
            options["cookiesfrombrowser"] = ((browser, profile) if profile else (browser,))
            return options, True
        return options, False

    def _analyze_url_worker(self, url: str):
        logs: list[str] = []
        info = None

        class Logger:
            def debug(self, value):
                if not str(value).startswith("[debug]"):
                    logs.append(str(value))
            warning = debug
            error = debug

        instagram_post = is_instagram_post_url(url)
        instagram_reel = is_instagram_reel_url(url)
        instagram_url = instagram_post or instagram_reel
        if is_x_status_url(url):
            try:
                x_info = extract_x_media_post_info(url)
                if x_info:
                    return normalize_info(x_info)
            except Exception as x_error:
                logs.append(str(x_error))
        options = configure_ytdlp_options({
            "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "referer": url, "noplaylist": not instagram_url, "listsubtitles": True,
            "logger": Logger(),
            "progress_hooks": [lambda _data: self.cancellation.is_set() and (_ for _ in ()).throw(UserCancelledError("Análisis cancelado."))],
        })
        if is_youtube_url(url):
            # El cliente incrustado evita el enlace ANDROID_VR que YouTube
            # rechaza después con 403 y ahorra ese segundo análisis fallido.
            options["extractor_args"] = {
                "youtube": {"player_client": ["web_embedded"]},
            }
        if not instagram_url:
            options["playlist_items"] = "1"
        cookie, using_cookies = self._cookie_options()
        captured = io.StringIO()
        try:
            with redirect_stdout(captured):
                info = extract_info_resilient(url, options, download=False)
            info = normalize_info(info)
            image_info = instagram_image_post_info_from_metadata(url, info or {}) if instagram_post else None
            if image_info:
                info = image_info
        except Exception as exc:
            if using_cookies:
                try:
                    authenticated = apply_yt_patch({**options, **cookie})
                    with redirect_stdout(captured):
                        info = extract_info_resilient(url, authenticated, download=False)
                    info = normalize_info(info)
                    image_info = instagram_image_post_info_from_metadata(url, info or {}) if instagram_post else None
                    if image_info:
                        info = image_info
                except Exception as cookie_error:
                    logs.append(str(cookie_error))
                    info = None
                if info:
                    exc = None
            if exc is None:
                pass
            if instagram_post:
                try:
                    # Mantener el intento público barato; cargar cookies sólo si
                    # Instagram exige una sesión para completar el carrusel.
                    info = info or extract_instagram_image_post_info(url, ydl_options=options)
                    if not info and using_cookies:
                        info = extract_instagram_image_post_info(url, ydl_options={**options, **cookie})
                except Exception as fallback_error:
                    logs.append(str(fallback_error))
                    raise RuntimeError(friendly_ytdlp_error(exc, logs)) from exc
            elif instagram_reel:
                try:
                    info = info or extract_instagram_reel_info(url, ydl_options=options)
                    if not info and using_cookies:
                        info = extract_instagram_reel_info(url, ydl_options={**options, **cookie})
                except Exception as fallback_error:
                    logs.append(str(fallback_error))
            elif not info:
                raise RuntimeError(friendly_ytdlp_error(exc, logs)) from exc
        if not info:
            if instagram_post and not using_cookies:
                raise RuntimeError(
                    "Instagram sólo mostró la portada. Para leer todas las imágenes del carrusel, "
                    "elige tu navegador en Configuración > Cookies e inicia sesión en Instagram."
                )
            if instagram_reel:
                raise RuntimeError(
                    "Instagram no expuso un video reproducible para este reel. "
                    "En ConfiguraciÃ³n > Cookies, vuelve a importar las cookies de un navegador "
                    "donde tengas abierta la sesiÃ³n de Instagram y prueba de nuevo."
                )
            raise RuntimeError(friendly_ytdlp_error("No se recibió información.", logs))
        # An Instagram carousel deliberately uses playlist-shaped metadata,
        # but it must remain one image publication so every slide is kept.
        if (
            info.get("_type") in {"playlist", "multi_video"}
            and info.get("xomacito_media_type") != "image"
        ):
            entries = [entry for entry in info.get("entries", []) if entry]
            if not entries:
                raise RuntimeError("La lista está vacía o no es válida.")
            info = normalize_info(entries[0])
        if info.get("is_live"):
            raise RuntimeError("Las transmisiones en vivo no se descargan desde el modo individual.")
        if self.cancellation.is_set():
            raise UserCancelledError("Análisis cancelado.")
        return info

    def _apply_url_analysis(self, info: dict):
        self._analysis_info = info
        image_post = info.get("xomacito_media_type") == "image"
        self._image_post = info if image_post else None
        choices = build_media_choices(info) if not image_post else {
            "video": [], "audio": [], "subtitles": {}, "subtitleLanguages": [],
            "hasVideo": False, "hasAudio": False,
        }
        self._apply_choices(choices)
        raw_title = str(info.get("title") or "Sin título")
        title = safe_filename(raw_title) if self.settings.get("clean_titles", True) else raw_title
        thumbnail = info.get("thumbnail") or ""
        duration = float(info.get("duration") or 0)
        mode = "Imágenes" if image_post else ("Video+Audio" if self._video_choices else "Solo Audio")
        image_count = int(info.get("image_count") or len(info.get("xomacito_images") or []) or (1 if image_post else 0))
        self._options.update({
            "fragmentEnabled": False,
            "fragmentRanges": [],
            "startTime": "00:00:00",
            "endTime": self._format_clock(duration) if duration > 0 else "",
            "preciseClip": True,
        })
        self.optionsChanged.emit()
        self._set_state(
            title=title, busy=False, analyzed=True, progress=1.0, imagePost=image_post, imageCount=image_count,
            status="Publicación de imagen lista." if image_post else "Enlace analizado. Elige calidad y descarga.",
            thumbnailSource=thumbnail, duration=duration, mode=mode,
            originalWidth=int(info.get("width") or 0), originalHeight=int(info.get("height") or 0),
            hasVideo=choices["hasVideo"], hasAudio=choices["hasAudio"], sourceHasAlpha=False,
        )
        if not image_post:
            self._ensure_preset_for_mode(mode)
            self._refresh_trim_preview_source()

    def _apply_local_analysis(self, result: dict):
        video_choices = []
        for index, stream in enumerate(result["videoStreams"]):
            label = f"Video {index + 1} · {stream.get('width', '?')}×{stream.get('height', '?')} · {stream.get('codec_name', 'desconocido')}"
            video_choices.append((label, {"formatId": str(stream.get("index", index)), "raw": stream}))
        audio_choices = []
        for index, stream in enumerate(result["audioStreams"]):
            label = f"Audio {index + 1} · {stream.get('codec_name', 'desconocido')} · {stream.get('sample_rate', '?')} Hz"
            audio_choices.append((label, {"formatId": str(stream.get("index", index)), "raw": stream}))
        self._video_map = dict(video_choices)
        self._audio_map = dict(audio_choices)
        self._video_choices = list(self._video_map)
        self._audio_choices = list(self._audio_map)
        self.videoChoicesChanged.emit()
        self.audioChoicesChanged.emit()
        first_video = result["videoStreams"][0] if result["videoStreams"] else {}
        source_has_alpha = result["sourceHasAlpha"]
        if source_has_alpha:
            self._set_state(preset=ALPHA_PRESET)
            self._options["applyPreset"] = True
            self.optionsChanged.emit()
        self._set_state(
            busy=False, analyzed=True, progress=1.0, status="Archivo local listo para procesar.",
            selectedVideo=self._video_choices[0] if self._video_choices else "",
            selectedAudio=self._audio_choices[0] if self._audio_choices else "",
            hasVideo=bool(self._video_choices), hasAudio=bool(self._audio_choices),
            mode="Video+Audio" if self._video_choices else "Solo Audio",
            thumbnailSource=Path(result["thumbnail"]).as_uri() if result["thumbnail"] else "",
            sourceHasAlpha=source_has_alpha, duration=result["duration"],
            originalWidth=int(first_video.get("width") or 0), originalHeight=int(first_video.get("height") or 0),
        )
        self._options.update({
            "fragmentEnabled": False,
            "fragmentRanges": [],
            "startTime": "00:00:00",
            "endTime": self._format_clock(float(result["duration"] or 0)) if result["duration"] else "",
            "preciseClip": True,
        })
        self.optionsChanged.emit()
        self._ensure_preset_for_mode("Video+Audio" if self._video_choices else "Solo Audio")
        self._refresh_trim_preview_source()
        # Para archivos locales ambas vistas se generan sin competir por red
        # con el monitor. En enlaces se preparan al abrir el recortador.
        self.prepareTrimFilmstrip()
        self.prepareWaveform()

    @Slot()
    def prepareWaveform(self):
        """Genera una forma de onda local o desde el flujo de audio analizado."""
        if not self._state.get("analyzed") or self._state.get("imagePost") or not self._state.get("hasAudio"):
            self._set_state(waveformSource="", waveformBusy=False, waveformError="")
            return
        if self._state.get("waveformBusy"):
            return
        source = str(self._state.get("localFile") or "")
        preview_path = self._local_trim_preview_path()
        render_locally = bool(source or preview_path)
        headers: dict[str, str] = {}
        cache_key = source
        if render_locally:
            source = source or preview_path
            local = Path(source)
            if not local.is_file():
                self._set_state(waveformSource="", waveformBusy=False, waveformError="El archivo ya no está disponible.")
                return
            stat = local.stat()
            cache_key = f"{local.resolve()}|{stat.st_mtime_ns}|{stat.st_size}"
        else:
            audio_entry = dict(self._audio_map.get(self._state.get("selectedAudio"), {}) or {})
            raw = dict(audio_entry.get("raw") or {})
            source = str(raw.get("url") or "")
            headers = dict(raw.get("http_headers") or {})
            format_id = str(audio_entry.get("formatId") or raw.get("format_id") or "")
            cache_key = f"{self._state.get('url')}|{self._state.get('selectedAudio')}"
            if not source:
                self._set_state(
                    waveformSource="", waveformBusy=False,
                    waveformError="El sitio no ofrece una vista previa de audio.",
                )
                return
        target = waveform_target(self.waveform_dir, cache_key)
        if target.is_file() and target.stat().st_size > 256:
            self._set_state(
                waveformSource=QUrl.fromLocalFile(str(target)).toString(),
                waveformBusy=False,
                waveformError="",
            )
            return
        request_key = cache_key
        self._set_state(waveformSource="", waveformBusy=True, waveformError="")
        if render_locally:
            self.pool.submit(
                render_waveform,
                self.ffmpeg.ffmpeg_path,
                source,
                target,
                headers,
                on_result=lambda path: self._download_waveform_ready(request_key, path),
                on_error=lambda message, _detail: self._download_waveform_failed(request_key, message),
            )
            return
        cookie_options, using_cookies = self._cookie_options()
        self.pool.submit(
            self._remote_waveform_worker,
            str(self._state.get("url") or ""),
            source,
            format_id,
            target,
            headers,
            cookie_options,
            using_cookies,
            on_result=lambda path: self._download_waveform_ready(request_key, path),
            on_error=lambda message, _detail: self._download_waveform_failed(request_key, message),
        )

    def _remote_waveform_worker(
        self,
        page_url: str,
        direct_source: str,
        format_id: str,
        target: Path,
        headers: dict[str, str],
        cookie_options: dict[str, Any],
        using_cookies: bool,
    ) -> str:
        """Usa la URL efímera y recurre a yt-dlp si el servidor la rechaza."""
        try:
            return render_waveform(
                self.ffmpeg.ffmpeg_path, direct_source, target, headers,
            )
        except Exception as direct_error:
            safe_console_print(
                f"Vista previa directa rechazada; creando copia temporal: {direct_error}"
            )

        if not page_url:
            raise RuntimeError("No hay un enlace original para recuperar la pista de audio.")

        with tempfile.TemporaryDirectory(prefix="xomacito-wave-") as temporary_dir:
            preview_root = Path(temporary_dir)
            base_options: dict[str, Any] = {
                "quiet": True,
                "no_warnings": True,
                "noplaylist": True,
                "playlist_items": "1",
                "format": format_id or "bestaudio/best",
                "outtmpl": str(preview_root / "audio.%(ext)s"),
                "overwrites": True,
            }
            configured = configure_ytdlp_options(base_options)
            if using_cookies:
                configured = apply_yt_patch({**configured, **cookie_options})
            try:
                extract_info_resilient(page_url, configured, download=True)
            except Exception as selected_error:
                if not format_id:
                    raise RuntimeError(
                        "El sitio no permitió recuperar el audio para dibujar la forma de onda."
                    ) from selected_error
                # Algunos extractores renuevan sus identificadores entre el análisis y
                # el segundo acceso. En ese caso basta la mejor pista para visualizar.
                fallback = dict(configured)
                fallback["format"] = "bestaudio/best"
                extract_info_resilient(page_url, fallback, download=True)

            candidates = [
                path for path in preview_root.iterdir()
                if path.is_file() and path.suffix.lower() not in {".part", ".ytdl"}
            ]
            if not candidates:
                raise RuntimeError("La pista temporal terminó sin contenido reproducible.")
            preview = max(candidates, key=lambda path: path.stat().st_size)
            return render_waveform(self.ffmpeg.ffmpeg_path, str(preview), target)

    def _current_waveform_key(self) -> str:
        local_path = str(self._state.get("localFile") or "")
        if local_path and Path(local_path).is_file():
            stat = Path(local_path).stat()
            return f"{Path(local_path).resolve()}|{stat.st_mtime_ns}|{stat.st_size}"
        preview_path = self._local_trim_preview_path()
        if preview_path and Path(preview_path).is_file():
            stat = Path(preview_path).stat()
            return f"{Path(preview_path).resolve()}|{stat.st_mtime_ns}|{stat.st_size}"
        return f"{self._state.get('url')}|{self._state.get('selectedAudio')}"

    def _download_waveform_ready(self, request_key: str, path: str):
        if request_key != self._current_waveform_key():
            return
        self._set_state(
            waveformSource=QUrl.fromLocalFile(str(path)).toString(),
            waveformBusy=False,
            waveformError="",
        )

    def _download_waveform_failed(self, request_key: str, _message: str):
        if request_key != self._current_waveform_key():
            return
        self._set_state(
            waveformSource="",
            waveformBusy=False,
            waveformError=(
                "No se pudo leer esta pista. Reanaliza el enlace o elige otra calidad de audio."
            ),
        )

    @staticmethod
    def _format_clock(seconds: float) -> str:
        total = max(0, int(float(seconds or 0)))
        hours, remainder = divmod(total, 3600)
        minutes, secs = divmod(remainder, 60)
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"

    @staticmethod
    def _parse_clock(value: str) -> float | None:
        match = re.fullmatch(r"(\d{1,3}):([0-5]\d):([0-5]\d(?:\.\d{1,3})?)", str(value).strip())
        if not match:
            return None
        return int(match.group(1)) * 3600 + int(match.group(2)) * 60 + float(match.group(3))

    def _fragment_range_error(self, start_value: str, end_value: str) -> str:
        start = self._parse_clock(start_value)
        end = self._parse_clock(end_value)
        if start is None or end is None:
            return "Usa el formato HH:MM:SS en Inicio y Final; por ejemplo 00:01:30."
        if end <= start:
            return "El tiempo Final debe ser posterior al tiempo de Inicio."
        duration = float(self._state.get("duration") or 0)
        if duration > 0 and end > duration + 0.75:
            return f"El Final supera la duración ({self._format_clock(duration)})."
        return ""

    def _fragment_error(self) -> str:
        if not self._options.get("fragmentEnabled"):
            return ""
        ranges = self._options.get("fragmentRanges", [])
        if isinstance(ranges, list) and ranges:
            for index, fragment in enumerate(ranges, 1):
                if not isinstance(fragment, dict):
                    return f"El fragmento {index} no es válido."
                error = self._fragment_range_error(
                    str(fragment.get("startTime") or ""),
                    str(fragment.get("endTime") or ""),
                )
                if error:
                    return f"Fragmento {index}: {error}"
            return ""
        return self._fragment_range_error(
            self._options.get("startTime", ""),
            self._options.get("endTime", ""),
        )

    def _apply_choices(self, choices: dict):
        self._video_map = {entry["label"]: entry for entry in choices["video"]}
        self._audio_map = {entry["label"]: entry for entry in choices["audio"]}
        self._video_choices = list(self._video_map)
        self._audio_choices = list(self._audio_map)
        self._subtitle_map = choices["subtitles"]
        self._subtitle_language_code = {entry["label"]: entry["code"] for entry in choices["subtitleLanguages"]}
        self._subtitle_languages = list(self._subtitle_language_code)
        self.videoChoicesChanged.emit()
        self.audioChoicesChanged.emit()
        self.subtitleLanguagesChanged.emit()
        mode = "Video+Audio" if choices["hasVideo"] else "Solo Audio"
        self._set_state(
            mode=mode,
            selectedVideo=self._video_choices[0] if self._video_choices else "",
            selectedAudio=self._audio_choices[0] if self._audio_choices else "",
            selectedSubtitleLanguage=self._subtitle_languages[0] if self._subtitle_languages else "",
        )
        self._refresh_subtitle_formats(self._state["selectedSubtitleLanguage"])

    def _refresh_subtitle_formats(self, language_label: str):
        code = self._subtitle_language_code.get(language_label, "")
        entries = self._subtitle_map.get(code, [])
        labels = []
        for index, entry in enumerate(entries):
            kind = "Automático" if entry.get("automatic") else "Manual"
            labels.append(f"{kind} · {str(entry.get('ext') or 'best').upper()} · {index + 1}")
        self._subtitle_formats = labels
        self.subtitleFormatsChanged.emit()
        self._set_state(selectedSubtitleFormat=labels[0] if labels else "")

    def _selected_subtitle(self) -> dict | None:
        code = self._subtitle_language_code.get(self._state["selectedSubtitleLanguage"], "")
        entries = self._subtitle_map.get(code, [])
        try:
            index = self._subtitle_formats.index(self._state["selectedSubtitleFormat"])
        except ValueError:
            index = 0
        return entries[index] if entries else None

    @Slot()
    def start(self):
        if self._state["busy"]:
            return
        if not self._state["analyzed"]:
            self.notificationRequested.emit("warning", "Analiza primero", "Analiza un enlace o importa un archivo.")
            return
        fragment_error = self._fragment_error()
        if fragment_error:
            self.notificationRequested.emit("warning", "Revisa el fragmento", fragment_error)
            return
        output = Path(str(self._state["effectiveOutputPath"]))
        try:
            output.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            self.notificationRequested.emit("error", "Carpeta inválida", str(exc))
            return
        self.cancellation.clear()
        self._current_counts_as_download = not bool(self._state["localFile"])
        self._set_state(busy=True, progress=0.0, status="Preparando proceso…", lastOutput="")
        options = self._collect_process_options()
        self._active_worker = self.pool.submit(
            self._process_worker, options,
            on_result=self._operation_success,
            on_error=lambda message, detail: self._operation_error(message, detail),
        )

    def _collect_process_options(self) -> dict:
        options = {
            "url": self._state["url"], "local_file": self._state["localFile"],
            "output_path": self._state["effectiveOutputPath"], "title": safe_filename(self._state["title"]),
            "mode": self._state["mode"], "video_label": self._state["selectedVideo"],
            "audio_label": self._state["selectedAudio"], "subtitle": self._selected_subtitle(),
            "duration": self._state["duration"], "operation_mode": self._state["operationMode"],
            "thumbnail_url": (self._analysis_info or {}).get("thumbnail", ""),
            "image_format": self._state.get("imageFormat", "Original"),
            **self._options,
        }
        if self._state["operationMode"] == "Rápido" and self._options["applyPreset"]:
            preset = self.presets.find(self._state["preset"])
            options.update(preset)
            options["keep_original_file"] = self._options["keepOriginal"]
        else:
            options.update({
                "recode_video_enabled": self._options["recodeVideoEnabled"],
                "recode_audio_enabled": self._options["recodeAudioEnabled"],
                "keep_original_file": self._options["keepOriginal"],
                "recode_proc": self._options["recodeProc"],
                "recode_codec_name": self._options["recodeCodecName"],
                "recode_profile_name": self._options["recodeProfileName"],
                "recode_audio_codec_name": self._options["recodeAudioCodecName"],
                "recode_audio_profile_name": self._options["recodeAudioProfileName"],
                "custom_bitrate_value": self._options["customBitrate"],
                "custom_gif_fps": self._options["customGifFps"],
                "custom_gif_width": self._options["customGifWidth"],
                "fps_force_enabled": self._options["fpsForceEnabled"],
                "fps_value": self._options["fpsValue"],
                "resolution_change_enabled": self._options["resolutionChangeEnabled"],
                "res_width": self._options["resWidth"], "res_height": self._options["resHeight"],
                "maintain_aspect": self._options["maintainAspect"],
            })
        if options.get("fragmentEnabled"):
            # Los cortes por copia de flujo dependen de fotogramas clave y pueden
            # comenzar congelados o adelantados. Todo fragmento se procesa con
            # precisión de fotograma, incluso si una configuración antigua decía
            # lo contrario.
            options["preciseClip"] = True
        return options

    def _process_worker(self, options: dict) -> str:
        input_file = options.get("local_file")
        downloaded = False
        if self._image_post:
            return self._download_image_post(options)
        if not input_file:
            input_file = self._download_worker(options)
            downloaded = True
        if self.cancellation.is_set():
            raise UserCancelledError("Proceso cancelado.")

        if options.get("fragmentEnabled") and options.get("fragmentRanges"):
            result = self._process_multiple_fragments(input_file, options, downloaded)
        elif options.get("extractFramesEnabled"):
            result = self._extract_frames(input_file, options, downloaded)
        elif options.get("upscaleVideoEnabled"):
            result = self._upscale_video(input_file, options, downloaded)
        elif options.get("recode_video_enabled") or options.get("recode_audio_enabled"):
            result = self._recode_file(input_file, options, downloaded)
        elif options.get("fragmentEnabled") and options.get("local_file"):
            result = self._clip_without_recode(input_file, options)
        elif options.get("fragmentEnabled") and downloaded and not self._last_download_was_partial:
            result = self._clip_without_recode(input_file, options)
            if not options.get("keepOriginalOnClip") and Path(input_file) != Path(result):
                Path(input_file).unlink(missing_ok=True)
        elif (
            downloaded
            and options.get("mode") == "Video+Audio"
            and (
                Path(input_file).suffix.lower() != ".mp4"
                or not is_editor_mp4_selection(
                    self._video_map.get(options.get("video_label"), {}),
                    self._audio_map.get(options.get("audio_label"), {}),
                )
            )
        ):
            self.progressReported.emit(0.0, "Preparando MP4 compatible con editores…")
            result = self._recode_file(
                input_file,
                editor_mp4_fallback_options(options),
                downloaded=True,
            )
        else:
            result = input_file
        if (
            downloaded
            and options.get("mode") == "Solo Audio"
            and options.get("embedThumbnail")
            and options.get("thumbnail_url")
        ):
            result = self._embed_audio_thumbnail(result, options["thumbnail_url"])
        return result

    def _embed_audio_thumbnail(self, audio_file: str, thumbnail_url: str) -> str:
        """Inserta la miniatura como portada en MP3/M4A sin recodificar el audio."""
        source = Path(audio_file)
        if source.suffix.lower() not in {".mp3", ".m4a", ".mp4"}:
            return audio_file
        self.progressReported.emit(0.97, "Añadiendo portada al audio…")
        with tempfile.TemporaryDirectory(prefix="xomacito-cover-") as directory:
            cover = Path(directory) / "cover.jpg"
            response = requests.get(thumbnail_url, timeout=30)
            response.raise_for_status()
            from PIL import Image
            with Image.open(io.BytesIO(response.content)) as image:
                image.convert("RGB").save(cover, "JPEG", quality=92)
            temporary = source.with_name(f"{source.stem}.cover-temp{source.suffix}")
            command = [
                self.ffmpeg.ffmpeg_path, "-y", "-nostdin",
                "-i", str(source), "-i", str(cover),
                "-map", "0:a:0", "-map", "1:v:0",
                "-c:a", "copy", "-c:v", "mjpeg",
            ]
            if source.suffix.lower() == ".mp3":
                command += [
                    "-id3v2_version", "3",
                    "-metadata:s:v", "title=Album cover",
                    "-metadata:s:v", "comment=Cover (front)",
                ]
            else:
                command += ["-disposition:v:0", "attached_pic"]
            command.append(str(temporary))
            creationflags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
            completed = subprocess.run(
                command, capture_output=True, text=True, encoding="utf-8",
                errors="ignore", creationflags=creationflags,
            )
            if completed.returncode:
                temporary.unlink(missing_ok=True)
                raise RuntimeError(f"No se pudo insertar la portada: {completed.stderr[-800:]}")
            os.replace(temporary, source)
        return str(source)

    def _download_x_video_as_mp4(self, direct_url: str, target: Path) -> str:
        """Descarga un stream de X y entrega un MP4 H.264/AAC reproducible."""
        ffmpeg_path = str(self.ffmpeg.ffmpeg_path or "")
        if not ffmpeg_path or not Path(ffmpeg_path).is_file():
            raise RuntimeError("No se encontró FFmpeg para preparar el video de X en MP4.")
        self.progressReported.emit(0.04, "Preparando video MP4 compatible de X…")
        command = [
            ffmpeg_path, "-y", "-nostdin", "-hide_banner", "-loglevel", "error",
            "-i", direct_url,
            "-map", "0:v:0", "-map", "0:a?",
            "-c:v", "libx264", "-preset", "veryfast", "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-movflags", "+faststart", str(target),
        ]
        creationflags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
        completed = subprocess.run(
            command,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
            creationflags=creationflags,
        )
        if self.cancellation.is_set():
            target.unlink(missing_ok=True)
            raise UserCancelledError("Descarga cancelada.")
        if completed.returncode:
            target.unlink(missing_ok=True)
            details = (completed.stderr or "").strip()
            suffix = f" Detalle: {details[-600:]}" if details else ""
            raise RuntimeError("No se pudo convertir el video de X a MP4 compatible." + suffix)
        if not target.is_file() or target.stat().st_size < 1024:
            target.unlink(missing_ok=True)
            raise RuntimeError("X no entregó un video MP4 válido.")
        self.progressReported.emit(0.96, "Video MP4 de X listo…")
        return str(target)

    def _download_worker(self, options: dict) -> str:
        options = dict(options)
        self._last_download_was_partial = False
        options["title"] = next_available_media_stem(
            options["output_path"], options["title"]
        )
        video = self._video_map.get(options["video_label"], {})
        audio = self._audio_map.get(options["audio_label"], {})
        if (
            options["mode"] != "Solo Audio"
            and str((self._analysis_info or {}).get("extractor") or "").startswith("x:media")
        ):
            direct_url = str((video or {}).get("raw", {}).get("url") or "")
            if direct_url:
                target = next_available_path(
                    Path(options["output_path"]) / f"{options['title']}.mp4"
                )
                return self._download_x_video_as_mp4(direct_url, target)
        video_id, audio_id = video.get("formatId"), audio.get("formatId")
        if options["mode"] == "Solo Audio":
            selector = audio_id or "bestaudio/best"
        elif video.get("combined"):
            selector = video_id
        elif video_id and audio_id:
            selector = f"{video_id}+{audio_id}"
        else:
            selector = video_id or "bestvideo+bestaudio/best"
        output_template = str(Path(options["output_path"]) / f"{options['title']}.%(ext)s")
        ydl_options: dict[str, Any] = {
            "outtmpl": output_template, "format": selector, "postprocessors": [], "noplaylist": True,
            "ffmpeg_location": self.ffmpeg.ffmpeg_path, "retries": 2, "fragment_retries": 2,
            "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "referer": options["url"],
        }
        merge_container = preferred_merge_container(video, audio)
        if merge_container:
            ydl_options["merge_output_format"] = merge_container
        subtitle = options.get("subtitle")
        if options.get("downloadSubtitles") and subtitle:
            ydl_options.update({
                "writesubtitles": True, "subtitleslangs": [subtitle["lang"]],
                "writeautomaticsub": bool(subtitle.get("automatic")),
                "embedsubtitles": options["mode"] == "Video+Audio",
                "subtitlesformat": "best/vtt/best" if options.get("cleanSubtitle") else subtitle.get("ext", "best"),
            })
            if options.get("cleanSubtitle"):
                ydl_options["convertsubtitles"] = "srt"
        cookie, using_cookies = self._cookie_options()
        partial = (
            options.get("fragmentEnabled")
            and not options.get("fragmentRanges")
            and not options.get("forceFullDownload")
            and not options.get("keepOriginalOnClip")
            and not options.get("preciseClip")
        )
        if partial and (options.get("startTime") or options.get("endTime")):
            try:
                from yt_dlp.utils import download_range_func
                start = seconds_from_time(options.get("startTime"))
                end = seconds_from_time(options.get("endTime")) or float("inf")
                ydl_options["download_ranges"] = download_range_func(None, [(start, end)])
                ydl_options["force_keyframes_at_cuts"] = bool(options.get("preciseClip"))
            except Exception:
                partial = False
        self.progressReported.emit(0.02, "Descargando…")
        invalid_argument_retry = False
        try:
            result = download_media(options["url"], ydl_options, self._download_progress, self.cancellation)
        except Exception as first_error:
            if self.cancellation.is_set():
                raise UserCancelledError("Descarga cancelada.") from first_error
            if using_cookies:
                try:
                    authenticated = apply_yt_patch({**ydl_options, **cookie})
                    self.progressReported.emit(0.02, "Reintentando con las cookies configuradas…")
                    authenticated_result = download_media(
                        options["url"], authenticated, self._download_progress, self.cancellation,
                    )
                    self._last_download_was_partial = "download_ranges" in authenticated
                    return authenticated_result
                except Exception:
                    pass
            fallback = dict(ydl_options)
            fallback.pop("download_ranges", None)
            fallback.pop("force_keyframes_at_cuts", None)
            fallback.pop("merge_output_format", None)
            fallback["format"] = (
                "bestaudio[ext=m4a]/bestaudio/best"
                if options["mode"] == "Solo Audio"
                else (
                    "bestvideo[ext=mp4][vcodec^=avc1]+bestaudio[ext=m4a]/"
                    "best[ext=mp4][vcodec^=avc1]/"
                    "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/"
                    "bestvideo+bestaudio/best"
                )
            )
            invalid_argument_retry = self._is_invalid_argument_error(first_error)
            if invalid_argument_retry:
                # Algunos volúmenes sincronizados de Windows rechazan temporalmente
                # el nombre final aunque la carpeta sea válida. Un nombre ASCII corto
                # evita EINVAL; al terminar restauramos el título elegido.
                staging_name = f"xomacito-{os.getpid()}-{threading.get_ident()}-{time.time_ns()}"
                fallback["outtmpl"] = str(Path(options["output_path"]) / f"{staging_name}.%(ext)s")
                self.progressReported.emit(0.02, "Reintentando con una ruta compatible con Windows…")
            else:
                alternative_result = (
                    "La mejor alternativa se entregará como MP4 compatible."
                    if options["mode"] == "Video+Audio"
                    else "Se priorizará M4A; si el sitio no lo ofrece, se mostrará el formato de audio disponible."
                )
                choice = self.dialogs.ask(
                    "choice", "Calidad no disponible",
                    f"El formato exacto falló. {alternative_result}\n\n¿Deseas continuar?",
                    ["Usar alternativa", "Cancelar"], "Cancelar",
                )
                if choice != "Usar alternativa":
                    raise UserCancelledError("Descarga cancelada.") from first_error
            result = download_media(options["url"], fallback, self._download_progress, self.cancellation)
            self._last_download_was_partial = False
        else:
            self._last_download_was_partial = "download_ranges" in ydl_options
        if not result or not Path(result).is_file():
            raise RuntimeError("La descarga terminó sin producir un archivo válido.")
        if invalid_argument_retry:
            result = self._restore_download_title(result, options)
        if options.get("autoSaveThumbnail"):
            self._save_thumbnail_to(Path(options["output_path"]), options["title"])
        return str(result)

    @staticmethod
    def _is_invalid_argument_error(error: BaseException) -> bool:
        """Reconoce EINVAL incluso cuando yt-dlp lo envuelve en DownloadError."""
        current: BaseException | None = error
        visited: set[int] = set()
        while current is not None and id(current) not in visited:
            visited.add(id(current))
            if getattr(current, "errno", None) == 22 or "[Errno 22]" in str(current):
                return True
            current = current.__cause__ or current.__context__
        return False

    def _restore_download_title(self, downloaded_path: str, options: dict) -> str:
        source = Path(downloaded_path)
        desired = self._resolve_output(
            Path(options["output_path"]), options["title"], source.suffix, ask=False,
        )
        if desired is None or source == desired:
            return str(source)
        os.replace(source, desired)
        return str(desired)

    def _download_progress(self, percent, message):
        value = float(percent or 0)
        if value > 1:
            value /= 100.0
        self.progressReported.emit(max(0.0, min(1.0, value)), str(message or "Descargando…"))

    def _recode_file(self, input_file: str, options: dict, downloaded: bool) -> str:
        params, container = resolve_recode_parameters(options)
        output = self._resolve_output(Path(options["output_path"]), options["title"] + "_recodificado", container)
        if not output:
            raise UserCancelledError("Recodificación cancelada.")
        temporary = output.with_name(f"{output.stem}.temp{output.suffix}")
        pre_params = []
        expected_duration = float(options.get("duration") or 0)
        if options.get("fragmentEnabled") and (options.get("startTime") or options.get("endTime")):
            start = seconds_from_time(options.get("startTime"))
            end = seconds_from_time(options.get("endTime"))
            if start:
                pre_params += ["-ss", str(start)]
            if end and end > start:
                pre_params += ["-t", str(end - start)]
                expected_duration = end - start
        video_index = None
        audio_index: int | str | None = None
        if options.get("local_file"):
            selected_video = self._video_map.get(options["video_label"], {})
            selected_audio = self._audio_map.get(options["audio_label"], {})
            if selected_video.get("formatId", "").isdigit():
                video_index = int(selected_video["formatId"])
            if options.get("useAllAudioTracks"):
                audio_index = "all"
            elif selected_audio.get("formatId", "").isdigit():
                audio_index = int(selected_audio["formatId"])
        self.progressReported.emit(0.0, "Recodificando y validando…")
        result = self.ffmpeg.execute_recode({
            "input_file": input_file, "output_file": str(temporary), "ffmpeg_params": params,
            "pre_params": pre_params, "duration": expected_duration, "mode": options["mode"],
            "selected_video_stream_index": video_index, "selected_audio_stream_index": audio_index,
            "output_container": container,
        }, self._ffmpeg_progress, self.cancellation)
        os.replace(result, output)
        if downloaded and not options.get("keep_original_file") and Path(input_file) != output:
            Path(input_file).unlink(missing_ok=True)
        return str(output)

    def _process_multiple_fragments(self, input_file: str, options: dict, downloaded: bool) -> str:
        ranges = [item for item in options.get("fragmentRanges", []) if isinstance(item, dict)]
        if not ranges:
            raise RuntimeError("No hay fragmentos en la lista.")
        source = Path(input_file)
        base_title = safe_filename(options.get("title") or source.stem)
        for index, fragment in enumerate(ranges, 1):
            if self.cancellation.is_set():
                raise UserCancelledError("Proceso cancelado.")
            self.progressReported.emit(
                (index - 1) / max(1, len(ranges)),
                f"Procesando fragmento {index} de {len(ranges)}…",
            )
            fragment_options = dict(options)
            fragment_options.update({
                "fragmentRanges": [],
                "startTime": str(fragment.get("startTime") or ""),
                "endTime": str(fragment.get("endTime") or ""),
                "title": f"{base_title}_fragmento_{index:02d}",
            })
            if options.get("recode_video_enabled") or options.get("recode_audio_enabled"):
                self._recode_file(str(source), fragment_options, downloaded=False)
            else:
                self._clip_without_recode(
                    str(source), fragment_options,
                    output_stem=fragment_options["title"],
                )
        if downloaded and not options.get("keepOriginalOnClip") and source.exists():
            source.unlink(missing_ok=True)
        self.progressReported.emit(1.0, f"{len(ranges)} fragmentos completados.")
        return str(Path(options["output_path"]))

    def _clip_without_recode(
        self, input_file: str, options: dict, *, output_stem: str | None = None,
    ) -> str:
        source = Path(input_file)
        audio_only = options.get("mode") == "Solo Audio"
        output_suffix = ".m4a" if audio_only else ".mp4"
        output = self._resolve_output(
            Path(options["output_path"]),
            output_stem or options["title"] + "_fragmento",
            output_suffix,
        )
        if not output:
            raise UserCancelledError("Corte cancelado.")
        start = seconds_from_time(options.get("startTime"))
        end = seconds_from_time(options.get("endTime"))
        command = [
            self.ffmpeg.ffmpeg_path,
            "-y",
            "-nostdin",
            "-fflags",
            "+genpts",
            "-i",
            str(source),
        ]
        # Buscar después de abrir la entrada evita el salto al fotograma clave
        # anterior. Al recodificar se generan PTS nuevos desde cero y se elimina
        # el congelamiento que algunos reproductores muestran al inicio.
        if start:
            command += ["-ss", f"{start:.6f}"]
        if end and end > start:
            command += ["-t", f"{end - start:.6f}"]
        if audio_only:
            command += [
                "-map", "0:a:0?",
                "-vn",
                "-c:a", "aac",
                "-b:a", "192k",
            ]
        else:
            command += [
                "-map", "0:v:0?",
                "-map", "0:a:0?",
                "-sn",
                "-dn",
                "-c:v", "libx264",
                "-preset", "veryfast",
                "-crf", "18",
                "-pix_fmt", "yuv420p",
                "-c:a", "aac",
                "-b:a", "192k",
                "-movflags", "+faststart",
            ]
        command += [
            "-avoid_negative_ts", "make_zero",
            "-reset_timestamps", "1",
            str(output),
        ]
        self.progressReported.emit(0.0, "Creando corte preciso y compatible…")
        creationflags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
        completed = subprocess.run(command, capture_output=True, text=True, creationflags=creationflags)
        if completed.returncode:
            raise RuntimeError(completed.stderr[-1200:])
        if not output.exists() or output.stat().st_size <= 0:
            raise RuntimeError("FFmpeg no generó un fragmento válido.")
        return str(output)

    def _extract_frames(self, input_file: str, options: dict, downloaded: bool) -> str:
        folder_name = safe_filename(options.get("extractFolderName") or f"{options['title']}_fotogramas")
        folder = Path(options["output_path"]) / folder_name
        if folder.exists() and any(folder.iterdir()):
            choice = self.dialogs.ask("choice", "La carpeta ya existe", f"{folder}\n\n¿Cómo deseas continuar?", ["Combinar", "Vaciar y reemplazar", "Cancelar"], "Cancelar")
            if choice == "Cancelar":
                raise UserCancelledError("Extracción cancelada.")
            if choice == "Vaciar y reemplazar":
                shutil.rmtree(folder)
        folder.mkdir(parents=True, exist_ok=True)
        extract_type = options.get("extractType", "Todos los fotogramas")
        fps = options.get("extractFps") if "FPS" in extract_type or options.get("extractFps") else None
        self.ffmpeg.execute_video_to_images({
            "input_file": input_file, "output_folder": str(folder),
            "image_format": options.get("extractFormat", "png"), "fps": fps,
            "jpg_quality": options.get("extractJpgQuality", "2"),
            "duration": options.get("duration", 0),
        }, self._ffmpeg_progress, self.cancellation)
        if downloaded and not options.get("keepOriginalExtract", True):
            Path(input_file).unlink(missing_ok=True)
        return str(folder)

    def _upscale_video(self, input_file: str, options: dict, downloaded: bool) -> str:
        source = Path(input_file)
        raw_container = options.get("upscaleContainer", "Mismo que el original")
        suffix = source.suffix if raw_container == "Mismo que el original" else "." + str(raw_container).lower().lstrip(".")
        name = safe_filename(options.get("upscaleOutputName") or options["title"] + "_reescalado")
        output = self._resolve_output(Path(options["output_path"]), name, suffix)
        if not output:
            raise UserCancelledError("Reescalado cancelado.")
        upscaler = VideoUpscaler(
            ffmpeg_dir=str(Path(self.ffmpeg.ffmpeg_path).parent),
            upscaling_dir=UPSCALING_DIR,
            cancellation_event=self.cancellation,
            progress_callback=self._ffmpeg_progress,
        )
        result = upscaler.upscale_video(str(source), str(output), {
            "upscale_engine": options.get("upscaleEngine"),
            "upscale_model_friendly": options.get("upscaleModel"),
            "upscale_scale": options.get("upscaleScale", "4x"),
            "upscale_tile": options.get("upscaleTile", "0"),
            "upscale_denoise": options.get("upscaleDenoise", "-1"),
            "upscale_tta": options.get("upscaleTta", False),
            "upscale_concurrency": options.get("upscaleConcurrency", "Automático"),
            "upscale_container": suffix,
            "upscale_transparency": options.get("upscaleTransparency", False),
        })
        if downloaded and not options.get("keepOriginal", True):
            source.unlink(missing_ok=True)
        return str(result or output)

    def _download_image_post(self, options: dict) -> str:
        entries = self._image_post.get("xomacito_images") or [self._image_post.get("url")]
        entries = [entry for entry in entries if entry]
        if not entries:
            raise RuntimeError("La publicación no contiene imágenes descargables.")
        outputs = []
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept": "image/avif,image/webp,image/apng,image/*,*/*;q=0.8",
            "Referer": str(self._image_post.get("webpage_url") or options.get("url") or "https://www.instagram.com/"),
        }
        for index, url in enumerate(entries, 1):
            response = requests.get(url, headers=headers, timeout=45, allow_redirects=True)
            response.raise_for_status()
            content_type = response.headers.get("Content-Type", "").lower()
            if content_type and not content_type.startswith("image/"):
                raise RuntimeError(f"La imagen {index} no pudo descargarse: el servidor no entregó una imagen.")
            image_format = str(options.get("image_format") or "Original").upper()
            suffix_map = {"JPEG": ".jpeg", "JPG": ".jpg", "PNG": ".png", "WEBP": ".webp"}
            suffix = suffix_map.get(image_format, Path(urlparse(response.url).path).suffix.lower())
            if suffix not in {".jpg", ".jpeg", ".png", ".webp", ".avif"}:
                suffix = ".jpg"
            name = options["title"] + (f"_{index}" if len(entries) > 1 else "")
            output = self._resolve_output(Path(options["output_path"]), name, suffix, ask=False)
            if image_format in suffix_map:
                try:
                    from PIL import Image
                    with Image.open(io.BytesIO(response.content)) as image:
                        if image_format in {"JPEG", "JPG"}:
                            image.convert("RGB").save(output, "JPEG", quality=95, optimize=True)
                        elif image_format == "PNG":
                            image.save(output, "PNG", optimize=True)
                        else:
                            image.save(output, "WEBP", quality=95, method=6)
                except (OSError, ValueError) as exc:
                    raise RuntimeError(f"La imagen {index} no pudo convertirse a {image_format}.") from exc
            else:
                output.write_bytes(response.content)
            outputs.append(str(output))
            self.progressReported.emit(index / len(entries), f"Guardando imagen {index}/{len(entries)}…")
        return outputs[0] if len(outputs) == 1 else str(Path(outputs[0]).parent)

    def _resolve_output(self, folder: Path, name: str, suffix: str, *, ask: bool = True) -> Path | None:
        suffix = suffix if str(suffix).startswith(".") else f".{suffix}"
        desired = folder / f"{safe_filename(name)}{suffix}"
        if not desired.exists():
            return desired
        if ask:
            choice = self.dialogs.ask("choice", "El archivo ya existe", str(desired), ["Reemplazar", "Crear copia", "Cancelar"], "Cancelar")
            if choice == "Cancelar":
                return None
            if choice == "Reemplazar":
                return desired
        return next_available_path(desired)

    def _ffmpeg_progress(self, percent, message):
        value = float(percent or 0)
        if value > 1:
            value /= 100.0
        self.progressReported.emit(max(0.0, min(1.0, value)), str(message or "Procesando…"))

    @Slot(float, str)
    def _apply_progress(self, value: float, message: str):
        self._set_state(progress=value, status=message)

    def _operation_success(self, output: str):
        completed_download = self._current_counts_as_download
        self._set_state(busy=False, progress=1.0, status="Proceso completado.", lastOutput=output)
        self.notificationRequested.emit("success", "Proceso completado", output)
        if completed_download:
            self.successfulDownload.emit(1)
            self.gachaSourceCompleted.emit(self._reward_source_key())
            if self.settings.get("open_explorer_after_download", True):
                reveal_in_file_manager(output)
        self._current_counts_as_download = False

    def _reward_source_key(self) -> str:
        info = self._analysis_info or {}
        extractor = str(info.get("extractor_key") or info.get("extractor") or "url").strip().casefold()
        media_id = str(info.get("id") or "").strip()
        if media_id:
            return f"{extractor}:{media_id}"
        parsed = urlparse(str(self._state.get("url") or "").strip())
        normalized = f"{parsed.netloc.casefold()}{parsed.path.rstrip('/')}"
        return normalized or str(self._state.get("url") or "").strip()

    def _operation_error(self, message: str, detail: str = ""):
        cancelled = self.cancellation.is_set() or "cancel" in message.lower()
        self._current_counts_as_download = False
        self._set_state(busy=False, progress=0.0, status="Proceso cancelado." if cancelled else message)
        if not cancelled:
            safe_console_print(detail)
            self.notificationRequested.emit("error", "No se pudo completar", message)

    def _clear_analysis_lists(self):
        self._video_choices = []
        self._audio_choices = []
        self._subtitle_languages = []
        self._subtitle_formats = []
        self._video_map.clear()
        self._audio_map.clear()
        self._subtitle_map.clear()
        self._subtitle_language_code.clear()
        self.videoChoicesChanged.emit()
        self.audioChoicesChanged.emit()
        self.subtitleLanguagesChanged.emit()
        self.subtitleFormatsChanged.emit()

    @Slot()
    def cancel(self):
        self.cancellation.set()
        self.ffmpeg.cancel_current_process()
        self._set_state(status="Cancelando…")

    @Slot()
    def openOutput(self):
        target = self._state["lastOutput"] or self._state["outputPath"]
        reveal_in_file_manager(target)

    @Slot()
    def sendToQueue(self):
        url = str(self._state["url"]).strip()
        if url:
            self.queueRequested.emit(url)
            self.navigateRequested.emit("queue")

    @Slot()
    def saveThumbnail(self):
        if not self._state["thumbnailSource"]:
            return
        destination, _ = QFileDialog.getSaveFileName(
            None,
            "Guardar miniatura para Premiere",
            f"{safe_filename(self._state['title'])}.jpg",
            PREMIERE_THUMBNAIL_FILTER,
        )
        if destination:
            try:
                source = self._state["thumbnailSource"]
                if source.startswith("file:"):
                    image_data = Path(QUrl(source).toLocalFile()).read_bytes()
                else:
                    response = requests.get(source, timeout=30)
                    response.raise_for_status()
                    image_data = response.content
                saved = save_premiere_thumbnail(image_data, destination)
                self.notificationRequested.emit("success", "Miniatura compatible con Premiere", str(saved))
            except Exception as exc:
                self.notificationRequested.emit("error", "No se pudo guardar", str(exc))

    def _save_thumbnail_to(self, folder: Path, title: str):
        source = self._state["thumbnailSource"]
        if not source:
            return
        try:
            destination = premiere_thumbnail_path(self._resolve_output(folder, title, ".jpg", ask=False))
            if source.startswith("file:"):
                image_data = Path(QUrl(source).toLocalFile()).read_bytes()
            else:
                response = requests.get(source, timeout=30)
                response.raise_for_status()
                image_data = response.content
            save_premiere_thumbnail(image_data, destination)
        except Exception as exc:
            safe_console_print(f"ADVERTENCIA: no se pudo guardar la miniatura: {exc}")

    @Slot()
    def saveSubtitle(self):
        subtitle = self._selected_subtitle()
        if not subtitle or not subtitle.get("url"):
            self.notificationRequested.emit("warning", "Subtítulo no disponible", "Selecciona un subtítulo con enlace directo.")
            return
        ext = str(subtitle.get("ext") or "vtt")
        destination, _ = QFileDialog.getSaveFileName(None, "Guardar subtítulo", f"{safe_filename(self._state['title'])}.{ext}", f"Subtítulo (*.{ext});;Todos (*.*)")
        if not destination:
            return
        try:
            response = requests.get(subtitle["url"], timeout=45)
            response.raise_for_status()
            Path(destination).write_bytes(response.content)
            if self._options["cleanSubtitle"] and ext == "vtt":
                clean_and_convert_vtt_to_srt(destination)
            self.notificationRequested.emit("success", "Subtítulo guardado", destination)
        except Exception as exc:
            self.notificationRequested.emit("error", "No se pudo guardar", str(exc))

    def shutdown(self):
        self.cancellation.set()
        self.ffmpeg.cancel_current_process()
        self.preview_proxy.shutdown()
