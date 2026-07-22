from __future__ import annotations

import io
import os
import shutil
import subprocess
import sys
import threading
import time
from contextlib import redirect_stdout
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import requests
from PySide6.QtCore import QObject, Property, QUrl, Signal, Slot
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import QFileDialog

from src.core.constants import AUDIO_EXTENSIONS, VIDEO_EXTENSIONS
from src.core.downloader import (
    apply_yt_patch,
    download_media,
    extract_info_resilient,
    extract_instagram_image_post_info,
    instagram_image_post_info_from_metadata,
    is_instagram_post_url,
)
from src.core.exceptions import UserCancelledError
from src.core.processor import FFmpegProcessor, clean_and_convert_vtt_to_srt, pixel_format_has_alpha
from src.core.video_upscaler import VideoUpscaler
from src.core.ytdlp_runtime import configure_ytdlp_options, friendly_ytdlp_error

from .dialog_broker import DialogBroker
from .media_logic import (
    build_media_choices,
    normalize_info,
    preferred_merge_container,
    safe_filename,
    seconds_from_time,
)
from .presets import ALPHA_PRESET, PresetStore, resolve_recode_parameters
from .settings_store import SettingsStore
from .workers import TaskPool


DEFAULT_OPTIONS: dict[str, Any] = {
    "downloadSubtitles": False,
    "cleanSubtitle": True,
    "keepFullSubtitle": False,
    "autoSaveThumbnail": False,
    "speedLimit": "",
    "fragmentEnabled": False,
    "startTime": "",
    "endTime": "",
    "preciseClip": False,
    "forceFullDownload": False,
    "keepOriginalOnClip": False,
    "applyPreset": False,
    "keepOriginal": True,
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


class DownloadController(QObject):
    stateChanged = Signal()
    optionsChanged = Signal()
    videoChoicesChanged = Signal()
    audioChoicesChanged = Signal()
    subtitleLanguagesChanged = Signal()
    subtitleFormatsChanged = Signal()
    progressReported = Signal(float, str)
    navigateRequested = Signal(str)
    queueRequested = Signal(str)
    notificationRequested = Signal(str, str, str)
    successfulDownload = Signal(int)

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
        self.cancellation = threading.Event()
        output = settings.get("default_download_path") or str(Path.home() / "Downloads")
        self._state: dict[str, Any] = {
            "url": "", "outputPath": output, "title": "", "mode": "Video+Audio",
            "localFile": "", "thumbnailSource": "", "status": "Pega un enlace o importa un archivo.",
            "progress": 0.0, "busy": False, "analyzed": False, "lastOutput": "",
            "operationMode": "Rápido", "preset": settings.get("quick_preset_saved", "Archivo - H.265 Normal"),
            "selectedVideo": "", "selectedAudio": "", "selectedSubtitleLanguage": "",
            "selectedSubtitleFormat": "", "hasVideo": False, "hasAudio": False,
            "imagePost": False, "sourceHasAlpha": False, "duration": 0.0,
            "originalWidth": 0, "originalHeight": 0, "estimatedSize": "",
        }
        saved_recode = settings.get("recode_settings", {})
        self._options = {**DEFAULT_OPTIONS}
        if isinstance(saved_recode, dict):
            legacy_map = {
                "keep_original": "keepOriginal",
                "video_codec": "recodeCodecName",
                "video_profile": "recodeProfileName",
                "video_audio_codec": "recodeAudioCodecName",
                "video_audio_profile": "recodeAudioProfileName",
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
        self.progressReported.connect(self._apply_progress)

    @Property("QVariantMap", notify=stateChanged)
    def state(self):
        return self._state

    @Property("QVariantMap", notify=optionsChanged)
    def options(self):
        return self._options

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
        elif key == "preset":
            self.settings.set("quick_preset_saved", str(value))
        elif key == "mode":
            presets = self.presets.videoPresets if value == "Video+Audio" else self.presets.audioPresets
            if presets and self._state["preset"] not in presets:
                self._set_state(preset=presets[0])
        elif key == "selectedSubtitleLanguage":
            self._refresh_subtitle_formats(str(value))

    @Slot(str, "QVariant")
    def setOption(self, key: str, value):
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
        }
        self.settings.set("recode_settings", persisted)

    @Slot()
    def chooseOutputFolder(self):
        folder = QFileDialog.getExistingDirectory(None, "Carpeta de salida", self._state["outputPath"])
        if folder:
            self.setValue("outputPath", folder)

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
            thumbnailSource="", imagePost=False,
        )
        self._active_worker = self.pool.submit(
            self._analyze_local_worker, str(Path(path)),
            on_result=self._apply_local_analysis,
            on_error=lambda message, detail: self._operation_error(f"No se pudo analizar el archivo: {message}", detail),
        )

    def _analyze_local_worker(self, path: str):
        info = self.ffmpeg.get_local_media_info(path)
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
            localFile="", title="", analyzed=False, thumbnailSource="", imagePost=False,
            hasVideo=False, hasAudio=False, sourceHasAlpha=False, status="Pega un enlace o importa un archivo.",
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
            status="Contactando el sitio y leyendo formatos…", thumbnailSource="", imagePost=False,
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

        class Logger:
            def debug(self, value):
                if not str(value).startswith("[debug]"):
                    logs.append(str(value))
            warning = debug
            error = debug

        options = configure_ytdlp_options({
            "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "referer": url, "noplaylist": True, "playlist_items": "1", "listsubtitles": True,
            "logger": Logger(),
            "progress_hooks": [lambda _data: self.cancellation.is_set() and (_ for _ in ()).throw(UserCancelledError("Análisis cancelado."))],
        })
        cookie, using_cookies = self._cookie_options()
        options.update(cookie)
        if using_cookies:
            options = apply_yt_patch(options)
        captured = io.StringIO()
        try:
            with redirect_stdout(captured):
                info = extract_info_resilient(url, options, download=False)
            info = normalize_info(info)
            image_info = instagram_image_post_info_from_metadata(url, info or {})
            if image_info:
                info = image_info
        except Exception as exc:
            if is_instagram_post_url(url):
                try:
                    info = extract_instagram_image_post_info(url, ydl_options=options)
                except Exception as fallback_error:
                    logs.append(str(fallback_error))
                    raise RuntimeError(friendly_ytdlp_error(exc, logs)) from exc
            else:
                raise RuntimeError(friendly_ytdlp_error(exc, logs)) from exc
        if not info:
            raise RuntimeError(friendly_ytdlp_error("No se recibió información.", logs))
        if info.get("_type") in {"playlist", "multi_video"}:
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
        self._set_state(
            title=title, busy=False, analyzed=True, progress=1.0, imagePost=image_post,
            status="Publicación de imagen lista." if image_post else "Enlace analizado. Elige calidad y descarga.",
            thumbnailSource=thumbnail, duration=float(info.get("duration") or 0),
            originalWidth=int(info.get("width") or 0), originalHeight=int(info.get("height") or 0),
            hasVideo=choices["hasVideo"], hasAudio=choices["hasAudio"], sourceHasAlpha=False,
        )

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
        output = Path(str(self._state["outputPath"]))
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
            "output_path": self._state["outputPath"], "title": safe_filename(self._state["title"]),
            "mode": self._state["mode"], "video_label": self._state["selectedVideo"],
            "audio_label": self._state["selectedAudio"], "subtitle": self._selected_subtitle(),
            "duration": self._state["duration"], "operation_mode": self._state["operationMode"],
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

        if options.get("extractFramesEnabled"):
            return self._extract_frames(input_file, options, downloaded)
        if options.get("upscaleVideoEnabled"):
            return self._upscale_video(input_file, options, downloaded)
        if options.get("recode_video_enabled") or options.get("recode_audio_enabled"):
            return self._recode_file(input_file, options, downloaded)
        if options.get("fragmentEnabled") and options.get("local_file"):
            return self._clip_without_recode(input_file, options)
        return input_file

    def _download_worker(self, options: dict) -> str:
        video = self._video_map.get(options["video_label"], {})
        audio = self._audio_map.get(options["audio_label"], {})
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
        if options.get("speedLimit"):
            try:
                ydl_options["ratelimit"] = float(options["speedLimit"]) * 1024 * 1024
            except ValueError:
                pass
        cookie, using_cookies = self._cookie_options()
        ydl_options.update(cookie)
        if using_cookies:
            ydl_options = apply_yt_patch(ydl_options)
        partial = options.get("fragmentEnabled") and not options.get("forceFullDownload") and not options.get("keepOriginalOnClip")
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
        try:
            result = download_media(options["url"], ydl_options, self._download_progress, self.cancellation)
        except Exception as first_error:
            if self.cancellation.is_set():
                raise UserCancelledError("Descarga cancelada.") from first_error
            fallback = dict(ydl_options)
            fallback.pop("download_ranges", None)
            fallback.pop("force_keyframes_at_cuts", None)
            fallback.pop("merge_output_format", None)
            fallback["format"] = "bestaudio/best" if options["mode"] == "Solo Audio" else "bestvideo+bestaudio/best"
            choice = self.dialogs.ask(
                "choice", "Calidad no disponible",
                "El formato exacto falló. ¿Deseas descargar la mejor alternativa compatible?",
                ["Usar alternativa", "Cancelar"], "Cancelar",
            )
            if choice != "Usar alternativa":
                raise UserCancelledError("Descarga cancelada.") from first_error
            result = download_media(options["url"], fallback, self._download_progress, self.cancellation)
        if not result or not Path(result).is_file():
            raise RuntimeError("La descarga terminó sin producir un archivo válido.")
        if options.get("autoSaveThumbnail"):
            self._save_thumbnail_to(Path(options["output_path"]), options["title"])
        return str(result)

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

    def _clip_without_recode(self, input_file: str, options: dict) -> str:
        source = Path(input_file)
        output = self._resolve_output(Path(options["output_path"]), options["title"] + "_fragmento", source.suffix)
        if not output:
            raise UserCancelledError("Corte cancelado.")
        command = [self.ffmpeg.ffmpeg_path, "-y", "-nostdin"]
        start = seconds_from_time(options.get("startTime"))
        end = seconds_from_time(options.get("endTime"))
        if start:
            command += ["-ss", str(start)]
        command += ["-i", str(source)]
        if end and end > start:
            command += ["-t", str(end - start)]
        command += ["-map", "0", "-c", "copy", str(output)]
        creationflags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
        completed = subprocess.run(command, capture_output=True, text=True, creationflags=creationflags)
        if completed.returncode:
            raise RuntimeError(completed.stderr[-1200:])
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
            upscaling_dir=str(self.project_root / "bin" / "models" / "upscaling"),
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
        for index, url in enumerate(entries, 1):
            response = requests.get(url, timeout=45)
            response.raise_for_status()
            suffix = Path(urlparse(url).path).suffix.lower()
            if suffix not in {".jpg", ".jpeg", ".png", ".webp", ".avif"}:
                suffix = ".jpg"
            name = options["title"] + (f"_{index}" if len(entries) > 1 else "")
            output = self._resolve_output(Path(options["output_path"]), name, suffix, ask=False)
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
        counter = 1
        while True:
            candidate = desired.with_stem(f"{desired.stem}_{counter}")
            if not candidate.exists():
                return candidate
            counter += 1

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
            reveal_in_file_manager(output)
        self._current_counts_as_download = False

    def _operation_error(self, message: str, detail: str = ""):
        cancelled = self.cancellation.is_set() or "cancel" in message.lower()
        self._current_counts_as_download = False
        self._set_state(busy=False, progress=0.0, status="Proceso cancelado." if cancelled else message)
        if not cancelled:
            print(detail)
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
        destination, _ = QFileDialog.getSaveFileName(None, "Guardar miniatura", f"{safe_filename(self._state['title'])}.jpg", "Imágenes (*.jpg *.jpeg *.png *.webp)")
        if destination:
            try:
                source = self._state["thumbnailSource"]
                if source.startswith("file:"):
                    shutil.copy2(QUrl(source).toLocalFile(), destination)
                else:
                    response = requests.get(source, timeout=30)
                    response.raise_for_status()
                    Path(destination).write_bytes(response.content)
                self.notificationRequested.emit("success", "Miniatura guardada", destination)
            except Exception as exc:
                self.notificationRequested.emit("error", "No se pudo guardar", str(exc))

    def _save_thumbnail_to(self, folder: Path, title: str):
        source = self._state["thumbnailSource"]
        if not source:
            return
        try:
            destination = self._resolve_output(folder, title, ".jpg", ask=False)
            if source.startswith("file:"):
                shutil.copy2(QUrl(source).toLocalFile(), destination)
            else:
                response = requests.get(source, timeout=30)
                response.raise_for_status()
                destination.write_bytes(response.content)
        except Exception as exc:
            print(f"ADVERTENCIA: no se pudo guardar la miniatura: {exc}")

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
