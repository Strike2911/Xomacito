from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Any

from PySide6.QtCore import QObject, Property, QUrl, Signal, Slot
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import QFileDialog

from src.core.processor import FFmpegProcessor

from .list_model import ObjectListModel
from .media_logic import safe_filename
from .settings_store import SettingsStore
from .waveform import render_waveform, waveform_target
from .workers import TaskPool


SUPPORTED_MEDIA = {
    ".mp4", ".mov", ".m4v", ".mkv", ".webm", ".avi", ".mxf", ".mts", ".m2ts",
    ".mp3", ".m4a", ".wav", ".flac", ".aac", ".ogg", ".opus", ".wma",
    ".png", ".jpg", ".jpeg", ".webp", ".avif", ".bmp", ".tif", ".tiff", ".gif",
}

IMAGE_MEDIA = {".png", ".jpg", ".jpeg", ".webp", ".avif", ".bmp", ".tif", ".tiff", ".gif"}
GREEN_SCREEN_WORDS = ("green screen", "greenscreen", "chroma", "croma", "fondo verde")
MUSIC_WORDS = ("music", "musica", "música", "song", "cancion", "canción", "beat", "instrumental", "track")
PREMIERE_PLUGIN_ID = "com.strike2911.xomacito.link"
FOLDER_ACCENTS = (
    "#F5A623", "#22C7A9", "#5BA7FF", "#A77BFF", "#F06F91", "#E3C34C",
)


def _folder_accent(path: str | Path) -> str:
    """Asigna un color estable a cada carpeta sin guardar estado adicional."""
    normalized = str(Path(path).expanduser()).replace("\\", "/").casefold()
    digest = hashlib.sha1(normalized.encode("utf-8")).digest()
    return FOLDER_ACCENTS[digest[0] % len(FOLDER_ACCENTS)]


def _editorial_category(path: Path, kind: str, duration: float) -> str:
    """Clasifica como lo haría un editor, sin depender de carpetas perfectas."""
    searchable = " ".join(part.casefold().replace("_", "-") for part in path.parts)
    if any(word in searchable for word in GREEN_SCREEN_WORDS):
        return "Green screen"
    if kind == "Imagen":
        return "Imágenes"
    if kind == "Audio":
        if duration >= 45 or any(word in searchable for word in MUSIC_WORDS):
            return "Música"
        return "SFX"
    return "Video"


def _format_duration(seconds: float) -> str:
    seconds = max(0, int(round(float(seconds or 0))))
    hours, remainder = divmod(seconds, 3600)
    minutes, secs = divmod(remainder, 60)
    return f"{hours:02d}:{minutes:02d}:{secs:02d}" if hours else f"{minutes:02d}:{secs:02d}"


def _format_size(size: int) -> str:
    value = float(max(0, size))
    for unit in ("B", "KB", "MB", "GB"):
        if value < 1024 or unit == "GB":
            return f"{value:.1f} {unit}" if unit != "B" else f"{int(value)} B"
        value /= 1024
    return f"{value:.1f} GB"


def _format_bytes(size: int) -> str:
    return f"{max(0, int(size)):,}".replace(",", " ") + " bytes"


def _format_bitrate(value: Any) -> str:
    try:
        bits = float(value or 0)
    except (TypeError, ValueError):
        bits = 0
    if bits <= 0:
        return "—"
    if bits >= 1_000_000:
        return f"{bits / 1_000_000:.2f} Mbps"
    return f"{bits / 1_000:.0f} kbps"


def _frame_rate(stream: dict[str, Any] | None) -> str:
    if not stream:
        return "—"
    raw = str(stream.get("avg_frame_rate") or stream.get("r_frame_rate") or "").strip()
    if not raw or raw == "0/0":
        return "—"
    try:
        numerator, denominator = raw.split("/", 1)
        value = float(numerator) / float(denominator)
    except (ValueError, ZeroDivisionError):
        try:
            value = float(raw)
        except ValueError:
            return raw
    return f"{value:.2f} fps".replace(".00 ", " ")


def _metadata_summary(info: dict[str, Any]) -> tuple[str, int]:
    tags: dict[str, Any] = {}
    tags.update((info.get("format") or {}).get("tags") or {})
    for stream in info.get("streams") or []:
        for key, value in (stream.get("tags") or {}).items():
            tags.setdefault(key, value)
    preferred = ("title", "artist", "album", "date", "creation_time", "encoder", "comment")
    labels = {
        "title": "Título", "artist": "Artista", "album": "Álbum", "date": "Fecha",
        "creation_time": "Creado", "encoder": "Codificador", "comment": "Comentario",
    }
    parts = []
    lowered = {str(key).lower(): value for key, value in tags.items()}
    for key in preferred:
        value = str(lowered.get(key) or "").strip().replace("\n", " ")
        if value:
            parts.append(f"{labels[key]}: {value[:80]}")
        if len(parts) == 3:
            break
    return (" · ".join(parts) if parts else "Sin etiquetas embebidas", len(tags))


def _unique_destination(folder: Path, stem: str, suffix: str) -> Path:
    candidate = folder / f"{stem}{suffix}"
    number = 2
    while candidate.exists():
        candidate = folder / f"{stem} ({number}){suffix}"
        number += 1
    return candidate


def _premiere_panel_installed() -> bool:
    """Detecta el panel distribuido por Adobe sin depender del estado interno de Xomacito."""
    candidates: list[Path] = []
    roaming = str(os.environ.get("APPDATA", "") or "").strip()
    if roaming:
        candidates.append(Path(roaming) / "Adobe" / "UXP" / "Plugins" / "External")
    candidates.append(
        Path.home() / "Library" / "Application Support" / "Adobe" / "UXP" / "Plugins" / "External"
    )
    for root in candidates:
        if not root.is_dir():
            continue
        for manifest in root.glob(f"{PREMIERE_PLUGIN_ID}_*/manifest.json"):
            try:
                payload = json.loads(manifest.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                continue
            if payload.get("id") == PREMIERE_PLUGIN_ID:
                return True
    return False


class MediaLibraryController(QObject):
    stateChanged = Signal()
    notificationRequested = Signal(str, str, str)
    libraryPathChanged = Signal(str)

    ROLES = [
        "path", "name", "kind", "duration", "durationLabel", "sizeLabel", "dimensions",
        "videoCodec", "audioCodec", "modified", "previewSource", "thumbnailSource",
        "extension", "formatName", "formatLongName", "formatLabel", "sizeBytes",
        "sizeBytesLabel", "frameRate", "pixelFormat", "videoProfile", "videoBitrate",
        "audioBitrate", "totalBitrate", "sampleRate", "channels", "metadataSummary",
        "metadataCount", "category", "searchText", "isFavorite",
    ]
    LIBRARY_ROW_ROLES = [
        "rowType", "folderPath", "folderName", "folderCount", "folderColor",
        "expanded", "canRemove", *ROLES,
    ]

    def __init__(
        self,
        project_root: str | Path,
        settings: SettingsStore,
        pool: TaskPool,
        ffmpeg: FFmpegProcessor,
        parent=None,
    ):
        super().__init__(parent)
        self.project_root = Path(project_root)
        self.settings = settings
        self.pool = pool
        self.ffmpeg = ffmpeg
        configured = str(settings.get("premiere_library_path", "") or "").strip()
        default_root = Path.home() / "Videos" / "Xomacito"
        self.root = Path(configured).expanduser() if configured else default_root
        self.root.mkdir(parents=True, exist_ok=True)
        self.clips_dir = self.root / "Recortes"
        self.thumbnails_dir = self.root / ".xomacito-thumbnails"
        self.clips_dir.mkdir(parents=True, exist_ok=True)
        self.thumbnails_dir.mkdir(parents=True, exist_ok=True)
        self.settings.set("premiere_library_path", str(self.root))
        self.items = ObjectListModel(self.ROLES, self)
        self.library_rows = ObjectListModel(self.LIBRARY_ROW_ROLES, self)
        self._collapsed_folders: set[str] = set()
        self._hidden_folders: set[str] = {
            str(Path(value).resolve())
            for value in list(settings.get("media_library_hidden_folders", []) or [])
            if str(value).strip()
        }
        self._favorite_paths: set[str] = {
            str(Path(value).resolve())
            for value in list(settings.get("media_library_favorites", []) or [])
            if str(value).strip()
        }
        self._status_after_refresh = ""
        self._state: dict[str, Any] = {
            "rootPath": str(self.root),
            "rootAccent": _folder_accent(self.root),
            "busy": False,
            "progress": 0.0,
            "status": "Biblioteca lista.",
            "selectedIndex": -1,
            "selected": {},
            "selectedFolderColor": _folder_accent(self.root),
            "clipIn": 0.0,
            "clipOut": 0.0,
            "clipMode": "Video + audio",
            "clipOutputDir": str(self.clips_dir),
            "lastClipPath": "",
            "waveformSource": "",
            "waveformBusy": False,
            "waveformError": "",
            "itemCount": 0,
            "hiddenFolderCount": len(self._hidden_folders),
            "searchText": "",
            "categoryFilter": "Todos",
            "visibleCount": 0,
            "favoriteCount": len(self._favorite_paths),
            "premiereLinkEnabled": bool(
                settings.get("premiere_auto_import_enabled", False) or _premiere_panel_installed()
            ),
            "premierePanelAvailable": (self.project_root / "premiere-panel" / "Xomacito-Link.ccx").is_file(),
        }
        self.refresh()

    @Property("QVariantMap", notify=stateChanged)
    def state(self):
        return self._state

    @Property(QObject, constant=True)
    def itemModel(self):
        return self.items

    @Property(QObject, constant=True)
    def libraryRowsModel(self):
        return self.library_rows

    def _rebuild_library_rows(self):
        groups: dict[str, list[dict[str, Any]]] = {}
        query = str(self._state.get("searchText") or "").strip().casefold()
        category_filter = str(self._state.get("categoryFilter") or "Todos")
        visible_items: list[dict[str, Any]] = []
        for item in self.items.items():
            is_favorite = str(Path(item["path"]).resolve()) in self._favorite_paths
            item = {**item, "isFavorite": is_favorite}
            if query and query not in str(item.get("searchText") or "").casefold():
                continue
            if category_filter == "Favoritos" and not is_favorite:
                continue
            if category_filter not in {"Todos", "Favoritos"} and item.get("category") != category_filter:
                continue
            visible_items.append(item)
            folder = str(self._group_folder(Path(item["path"])))
            groups.setdefault(folder, []).append(item)
        rows: list[dict[str, Any]] = []
        for folder, items in sorted(groups.items(), key=lambda pair: pair[0].casefold()):
            folder_path = Path(folder)
            if str(folder_path.resolve()) in self._hidden_folders:
                continue
            try:
                relative = folder_path.relative_to(self.root)
                label = "Biblioteca" if str(relative) == "." else str(relative)
            except ValueError:
                label = folder_path.name or folder
            expanded = folder not in self._collapsed_folders
            folder_row = {
                role: False if role in {"isFavorite", "expanded", "canRemove"} else ""
                for role in self.LIBRARY_ROW_ROLES
            }
            folder_row.update({
                "rowType": "folder", "folderPath": folder, "folderName": label,
                "folderCount": len(items), "folderColor": _folder_accent(folder),
                "expanded": expanded,
                "canRemove": folder_path.resolve() != self.root.resolve(),
            })
            rows.append(folder_row)
            if expanded:
                items.sort(key=lambda item: (not bool(item.get("isFavorite")), str(item.get("name") or "").casefold()))
                rows.extend(
                    {
                        **item, "rowType": "file", "folderPath": folder,
                        "folderColor": _folder_accent(folder),
                    }
                    for item in items
                )
        self.library_rows.replace(rows)
        self._set_state(visibleCount=len(visible_items), favoriteCount=len(self._favorite_paths))

    def _group_folder(self, media_path: Path) -> Path:
        """Agrupa por importación, no por cada subcarpeta interna del material."""
        parent = media_path.parent
        try:
            relative = parent.resolve().relative_to(self.root.resolve())
        except (OSError, ValueError):
            return parent
        parts = relative.parts
        if not parts:
            return self.root
        if parts[0].casefold() == "importados" and len(parts) >= 2:
            return self.root / parts[0] / parts[1]
        return self.root / parts[0]

    def _set_state(self, **values):
        changed = False
        for key, value in values.items():
            if self._state.get(key) != value:
                self._state[key] = value
                changed = True
        if changed:
            self.stateChanged.emit()

    @Slot()
    def refresh(self):
        if self._state["busy"]:
            return
        self._set_state(busy=True, progress=-1.0, status="Analizando archivos…")
        self.pool.submit(
            self._scan_worker,
            on_result=self._scan_ready,
            on_error=lambda message, detail: self._task_error("No se pudo analizar la biblioteca", message, detail),
        )

    def _scan_worker(self):
        rows: list[dict[str, Any]] = []
        for path in sorted(self.root.rglob("*"), key=lambda item: item.stat().st_mtime if item.is_file() else 0, reverse=True):
            if (
                not path.is_file()
                or path.suffix.lower() not in SUPPORTED_MEDIA
                or ".xomacito-thumbnails" in path.parts
            ):
                continue
            try:
                info = self.ffmpeg.get_local_media_info(str(path)) or {}
                streams = list(info.get("streams") or [])
                video = next((stream for stream in streams if stream.get("codec_type") == "video"), None)
                audio = next((stream for stream in streams if stream.get("codec_type") == "audio"), None)
                is_image = path.suffix.lower() in IMAGE_MEDIA
                kind = "Imagen" if is_image else "Video" if video else "Audio"
                duration = float((info.get("format") or {}).get("duration") or 0)
                if duration <= 0:
                    duration = max((float(stream.get("duration") or 0) for stream in streams), default=0.0)
                thumb = str(path) if is_image else self._thumbnail_for(path, duration) if video else ""
                stat = path.stat()
                format_info = info.get("format") or {}
                format_name = str(format_info.get("format_name") or path.suffix.lstrip(".")).upper()
                format_long_name = str(format_info.get("format_long_name") or "Contenedor multimedia")
                metadata_summary, metadata_count = _metadata_summary(info)
                channels = int((audio or {}).get("channels") or 0)
                channel_label = str((audio or {}).get("channel_layout") or "").replace("stereo", "Estéreo").replace("mono", "Mono")
                if not channel_label:
                    channel_label = f"{channels} canales" if channels else "—"
                category = _editorial_category(path, kind, duration)
                favorite = str(path.resolve()) in self._favorite_paths
                search_text = " ".join((
                    path.name, str(path.parent), category, kind, metadata_summary,
                    format_name, str((video or {}).get("codec_name") or ""),
                    str((audio or {}).get("codec_name") or ""),
                ))
                rows.append({
                    "path": str(path),
                    "name": path.name,
                    "kind": kind,
                    "duration": duration,
                    "durationLabel": _format_duration(duration),
                    "sizeLabel": _format_size(stat.st_size),
                    "dimensions": f"{video.get('width', 0)} × {video.get('height', 0)}" if video else "Solo audio",
                    "videoCodec": str((video or {}).get("codec_name") or "—").upper(),
                    "audioCodec": str((audio or {}).get("codec_name") or "—").upper(),
                    "modified": datetime.fromtimestamp(stat.st_mtime).strftime("%d/%m/%Y · %H:%M"),
                    "previewSource": QUrl.fromLocalFile(str(path)).toString(),
                    "thumbnailSource": QUrl.fromLocalFile(thumb).toString() if thumb else "",
                    "extension": path.suffix.lstrip(".").upper(),
                    "formatName": format_name,
                    "formatLongName": format_long_name,
                    "formatLabel": f"{path.suffix.lstrip('.').upper()} · {format_long_name}",
                    "sizeBytes": stat.st_size,
                    "sizeBytesLabel": f"{_format_size(stat.st_size)} · {_format_bytes(stat.st_size)}",
                    "frameRate": _frame_rate(video),
                    "pixelFormat": str((video or {}).get("pix_fmt") or "—").upper(),
                    "videoProfile": str((video or {}).get("profile") or "—"),
                    "videoBitrate": _format_bitrate((video or {}).get("bit_rate")),
                    "audioBitrate": _format_bitrate((audio or {}).get("bit_rate")),
                    "totalBitrate": _format_bitrate(format_info.get("bit_rate")),
                    "sampleRate": f"{int(float((audio or {}).get('sample_rate') or 0)):,} Hz".replace(",", " ") if audio else "—",
                    "channels": channel_label,
                    "metadataSummary": metadata_summary,
                    "metadataCount": metadata_count,
                    "category": category,
                    "searchText": search_text,
                    "isFavorite": favorite,
                })
            except (OSError, ValueError, subprocess.SubprocessError):
                continue
        self._write_manifest(rows)
        return rows

    def _thumbnail_for(self, path: Path, duration: float) -> str:
        digest = hashlib.sha1(f"{path}:{path.stat().st_mtime_ns}".encode("utf-8")).hexdigest()[:16]
        target = self.thumbnails_dir / f"{digest}.jpg"
        if target.is_file():
            return str(target)
        position = min(max(duration * 0.15, 0.2), 8.0)
        command = [
            self.ffmpeg.ffmpeg_path, "-y", "-nostdin", "-hide_banner", "-loglevel", "error",
            "-ss", f"{position:.3f}", "-i", str(path), "-frames:v", "1",
            "-vf", "scale=480:-2", "-q:v", "3", str(target),
        ]
        result = subprocess.run(command, capture_output=True, creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0)
        return str(target) if result.returncode == 0 and target.is_file() else ""

    def _write_manifest(self, rows: list[dict[str, Any]]):
        payload = {
            "schema": 1,
            "library": "Xomacito",
            "updatedAt": datetime.now().astimezone().isoformat(timespec="seconds"),
            "items": [{key: value for key, value in row.items() if key not in {"previewSource", "thumbnailSource"}} for row in rows],
        }
        temporary = self.root / ".xomacito-library.tmp"
        temporary.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
        os.replace(temporary, self.root / ".xomacito-library.json")

    def _scan_ready(self, rows):
        self.items.replace(list(rows or []))
        self._rebuild_library_rows()
        selected_index = 0 if rows else -1
        status = self._status_after_refresh or f"{len(rows)} archivo(s) listo(s)."
        self._status_after_refresh = ""
        self._set_state(busy=False, progress=1.0, status=status, itemCount=len(rows))
        self.select(selected_index)

    @Slot(int)
    def select(self, index: int):
        row = self.items.item(int(index)) or {}
        duration = float(row.get("duration") or 0)
        self._set_state(
            selectedIndex=int(index) if row else -1,
            selected=row,
            selectedFolderColor=(
                _folder_accent(self._group_folder(Path(row["path"])))
                if row.get("path") else _folder_accent(self.root)
            ),
            clipIn=0.0,
            clipOut=duration,
            clipMode="Video + audio" if row.get("kind") == "Video" else "Solo audio" if row.get("kind") == "Audio" else "Vista previa",
            waveformSource="",
            waveformBusy=False,
            waveformError="",
        )
        self._request_waveform(row)

    def _request_waveform(self, selected: dict[str, Any], force: bool = False):
        if not selected or selected.get("kind") == "Imagen" or selected.get("audioCodec") in {"", "—", None}:
            self._set_state(waveformSource="", waveformBusy=False, waveformError="")
            return
        source = Path(str(selected.get("path") or ""))
        if not source.is_file():
            self._set_state(waveformSource="", waveformBusy=False, waveformError="El archivo ya no está disponible.")
            return
        cache_key = f"{source.resolve()}|{source.stat().st_mtime_ns}|{source.stat().st_size}"
        target = waveform_target(self.thumbnails_dir, cache_key)
        if force:
            target.unlink(missing_ok=True)
        if target.is_file() and target.stat().st_size > 256:
            self._set_state(
                waveformSource=QUrl.fromLocalFile(str(target)).toString(),
                waveformBusy=False,
                waveformError="",
            )
            return
        selected_path = str(source)
        self._set_state(waveformSource="", waveformBusy=True, waveformError="")
        self.pool.submit(
            render_waveform,
            self.ffmpeg.ffmpeg_path,
            selected_path,
            target,
            on_result=lambda path: self._waveform_ready(selected_path, path),
            on_error=lambda message, _detail: self._waveform_failed(selected_path, message),
        )

    def _waveform_ready(self, selected_path: str, path: str):
        if str((self._state.get("selected") or {}).get("path") or "") != selected_path:
            return
        self._set_state(
            waveformSource=QUrl.fromLocalFile(str(path)).toString(),
            waveformBusy=False,
            waveformError="",
        )

    def _waveform_failed(self, selected_path: str, message: str):
        if str((self._state.get("selected") or {}).get("path") or "") != selected_path:
            return
        self._set_state(
            waveformSource="",
            waveformBusy=False,
            waveformError="No se encontró una pista de audio utilizable.",
        )

    @Slot()
    def retryWaveform(self):
        self._request_waveform(dict(self._state.get("selected") or {}), force=True)

    @Slot(str)
    def selectPath(self, path: str):
        wanted = str(path)
        for index, row in enumerate(self.items.items()):
            if str(row.get("path") or "") == wanted:
                self.select(index)
                return

    @Slot(str)
    def setSearchText(self, value: str):
        value = str(value or "").strip()
        if value == self._state.get("searchText"):
            return
        self._set_state(searchText=value)
        self._rebuild_library_rows()

    @Slot(str)
    def setCategoryFilter(self, value: str):
        allowed = {"Todos", "Favoritos", "Video", "SFX", "Música", "Imágenes", "Green screen"}
        value = str(value or "Todos")
        if value not in allowed:
            value = "Todos"
        if value == self._state.get("categoryFilter"):
            return
        self._set_state(categoryFilter=value)
        self._rebuild_library_rows()

    @Slot(str)
    def toggleFavorite(self, path: str):
        target = str(Path(str(path)).resolve())
        if target in self._favorite_paths:
            self._favorite_paths.remove(target)
            message = "Quitado de favoritos."
        else:
            self._favorite_paths.add(target)
            message = "Guardado para encontrarlo rápidamente."
        self.settings.set("media_library_favorites", sorted(self._favorite_paths))
        self._rebuild_library_rows()
        selected = dict(self._state.get("selected") or {})
        if selected and str(Path(selected.get("path", "")).resolve()) == target:
            self._set_state(selected={**selected, "isFavorite": target in self._favorite_paths})
        self.notificationRequested.emit("success", "Favoritos actualizados", message)

    @Slot(str)
    def toggleFolder(self, folder: str):
        folder = str(folder)
        if folder in self._collapsed_folders:
            self._collapsed_folders.remove(folder)
        else:
            self._collapsed_folders.add(folder)
        self._rebuild_library_rows()

    @Slot(str)
    def removeFolder(self, folder: str):
        """Oculta un grupo de la biblioteca sin modificar ningún archivo del editor."""
        target = Path(str(folder)).resolve()
        if self._state["busy"] or target == self.root.resolve() or not target.is_dir():
            self.notificationRequested.emit(
                "error", "No se pudo quitar la carpeta",
                "La carpeta principal de la biblioteca no puede ocultarse.",
            )
            return
        self._hidden_folders.add(str(target))
        self.settings.set("media_library_hidden_folders", sorted(self._hidden_folders))
        self._collapsed_folders.discard(str(target))
        selected = dict(self._state.get("selected") or {})
        if selected and self._group_folder(Path(selected.get("path", ""))).resolve() == target:
            self.select(-1)
        self._rebuild_library_rows()
        self._set_state(
            hiddenFolderCount=len(self._hidden_folders),
            status="Carpeta oculta; los archivos siguen intactos.",
        )
        self.notificationRequested.emit(
            "success", "Carpeta quitada de la lista", "Tus archivos no se modificaron.",
        )

    @Slot()
    def restoreHiddenFolders(self):
        if not self._hidden_folders:
            return
        self._hidden_folders.clear()
        self.settings.set("media_library_hidden_folders", [])
        self._rebuild_library_rows()
        self._set_state(hiddenFolderCount=0, status="Carpetas ocultas restauradas.")
        self.notificationRequested.emit("success", "Carpetas restauradas", "Vuelven a aparecer en la biblioteca.")

    @Slot(str, "QVariant")
    def setValue(self, key: str, value):
        if key not in {"clipIn", "clipOut", "clipMode"}:
            return
        if key in {"clipIn", "clipOut"}:
            duration = float(self._state.get("selected", {}).get("duration") or 0)
            number = max(0.0, min(duration, float(value or 0)))
            clip_in = number if key == "clipIn" else float(self._state["clipIn"])
            clip_out = number if key == "clipOut" else float(self._state["clipOut"])
            if key == "clipIn":
                clip_in = min(number, max(0.0, clip_out - 0.05))
            else:
                clip_out = max(number, min(duration, clip_in + 0.05))
            self._set_state(clipIn=clip_in, clipOut=clip_out)
            return
        self._set_state(clipMode=str(value))

    @Slot()
    def chooseLibraryFolder(self):
        folder = QFileDialog.getExistingDirectory(None, "Biblioteca de Xomacito para Premiere", str(self.root))
        if not folder:
            return
        self.root = Path(folder)
        self.root.mkdir(parents=True, exist_ok=True)
        self.clips_dir = self.root / "Recortes"
        self.thumbnails_dir = self.root / ".xomacito-thumbnails"
        self.clips_dir.mkdir(parents=True, exist_ok=True)
        self.thumbnails_dir.mkdir(parents=True, exist_ok=True)
        self.settings.set("premiere_library_path", str(self.root))
        self._set_state(rootPath=str(self.root), rootAccent=_folder_accent(self.root))
        self._set_state(clipOutputDir=str(self.clips_dir), lastClipPath="")
        self.libraryPathChanged.emit(str(self.root))
        self.refresh()

    @Slot()
    def importFolder(self):
        folder = QFileDialog.getExistingDirectory(None, "Importar carpeta a la biblioteca", str(Path.home()))
        if not folder or self._state["busy"]:
            return
        self._set_state(busy=True, progress=-1.0, status="Copiando y analizando carpeta…")
        self.pool.submit(
            self._import_paths_worker,
            [Path(folder)],
            on_result=lambda count: self._import_ready(count),
            on_error=lambda message, detail: self._task_error("No se pudo importar la carpeta", message, detail),
        )

    @Slot("QVariantList")
    def addDroppedPaths(self, values):
        if self._state["busy"]:
            return
        sources: list[Path] = []
        for value in list(values or []):
            if isinstance(value, QUrl):
                local = value.toLocalFile()
            else:
                url = QUrl(str(value))
                local = url.toLocalFile() if url.isLocalFile() else str(value)
            path = Path(local).expanduser()
            if path.exists() and path not in sources:
                sources.append(path)
        if not sources:
            self.notificationRequested.emit("error", "No se pudo importar", "Suelta una carpeta o archivo multimedia válido.")
            return
        self._set_state(busy=True, progress=-1.0, status="Copiando elementos arrastrados…")
        self.pool.submit(
            self._import_paths_worker,
            sources,
            on_result=lambda count: self._import_ready(count),
            on_error=lambda message, detail: self._task_error("No se pudo importar lo arrastrado", message, detail),
        )

    def _inside_library(self, path: Path) -> bool:
        try:
            path.resolve().relative_to(self.root.resolve())
            return True
        except (OSError, ValueError):
            return False

    def _import_paths_worker(self, sources: list[Path]) -> int:
        imports_root = self.root / "Importados"
        count = 0
        for source in sources:
            if self._inside_library(source):
                continue
            if source.is_file():
                if source.suffix.lower() not in SUPPORTED_MEDIA:
                    continue
                imports_root.mkdir(parents=True, exist_ok=True)
                destination = _unique_destination(imports_root, safe_filename(source.stem) or "Archivo", source.suffix.lower())
                shutil.copy2(source, destination)
                count += 1
                continue
            media_files = [
                path for path in source.rglob("*")
                if path.is_file() and path.suffix.lower() in SUPPORTED_MEDIA
                and ".xomacito-thumbnails" not in path.parts
            ]
            if not media_files:
                continue
            imports_root.mkdir(parents=True, exist_ok=True)
            destination_root = _unique_destination(imports_root, safe_filename(source.name) or "Carpeta", "")
            destination_root.mkdir(parents=True, exist_ok=True)
            for path in media_files:
                destination = destination_root / path.relative_to(source)
                destination.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(path, destination)
                count += 1
        return count

    def _import_ready(self, count: int):
        self._set_state(busy=False, status=f"{count} archivo(s) importado(s).")
        self.notificationRequested.emit("success", "Carpeta importada", f"Se agregaron {count} archivo(s) a la biblioteca.")
        self.refresh()

    @Slot()
    def createClip(self):
        selected = dict(self._state.get("selected") or {})
        if not selected or self._state["busy"]:
            return
        if selected.get("kind") == "Imagen":
            self.notificationRequested.emit(
                "info", "La imagen ya está lista",
                "Las imágenes no necesitan recorte temporal; puedes usarlas directamente.",
            )
            return
        start = float(self._state["clipIn"])
        end = float(self._state["clipOut"])
        if end - start < 0.05:
            self.notificationRequested.emit("error", "Recorte demasiado corto", "Separa los puntos de entrada y salida.")
            return
        self._set_state(busy=True, progress=-1.0, status="Creando recorte para Premiere…")
        self.pool.submit(
            self._clip_worker,
            selected, start, end, str(self._state["clipMode"]),
            on_result=self._clip_ready,
            on_error=lambda message, detail: self._task_error("No se pudo crear el recorte", message, detail),
        )

    def _clip_worker(self, selected: dict, start: float, end: float, mode: str) -> str:
        source = Path(selected["path"])
        duration = end - start
        stem = f"{safe_filename(source.stem)} — {int(start * 1000)}-{int(end * 1000)}ms"
        audio_only = selected.get("kind") == "Audio" or mode == "Solo audio"
        suffix = ".wav" if audio_only else ".mp4"
        target = _unique_destination(self.clips_dir, stem, suffix)
        command = [
            self.ffmpeg.ffmpeg_path, "-y", "-nostdin", "-hide_banner", "-loglevel", "error",
            "-ss", f"{start:.3f}", "-i", str(source), "-t", f"{duration:.3f}",
        ]
        if audio_only:
            command += ["-map", "0:a:0", "-vn", "-c:a", "pcm_s24le"]
        else:
            command += ["-map", "0:v:0", "-map", "0:a:0?"]
            command += ["-c:v", "libx264", "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p"]
            if mode == "Solo video":
                command += ["-an"]
            else:
                command += ["-c:a", "aac", "-b:a", "256k"]
            command += ["-movflags", "+faststart"]
        command.append(str(target))
        result = subprocess.run(command, capture_output=True, text=True, creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0)
        if result.returncode != 0 or not target.is_file() or target.stat().st_size <= 0:
            raise RuntimeError((result.stderr or "FFmpeg no generó el recorte.").strip())
        return str(target)

    def _clip_ready(self, path: str):
        result = Path(path)
        self._set_state(
            busy=False,
            progress=1.0,
            status=f"Recorte guardado en {result.parent}",
            lastClipPath=str(result),
            clipOutputDir=str(result.parent),
        )
        self._status_after_refresh = f"Recorte guardado en {result.parent}"
        self.notificationRequested.emit(
            "success",
            "Recorte creado",
            f"{result.name}\nCarpeta: {result.parent}",
        )
        self.refresh()

    def _task_error(self, title: str, message: str, detail: str):
        print(detail)
        self._set_state(busy=False, progress=0.0, status=str(message))
        self.notificationRequested.emit("error", title, str(message))

    @Slot()
    def openLibrary(self):
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(self.root)))

    @Slot()
    def openClipOutput(self):
        target = Path(str(self._state.get("lastClipPath") or self.clips_dir))
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(target.parent if target.is_file() else target)))

    @Slot()
    def connectPremiere(self):
        """Prepara la biblioteca y guía la instalación o apertura del panel UXP."""
        package = self.project_root / "premiere-panel" / "Xomacito-Link.ccx"
        panel_installed = _premiere_panel_installed()
        if not panel_installed and not package.is_file():
            self.notificationRequested.emit(
                "error", "Panel no disponible", "Primero hay que compilar Xomacito Link.",
            )
            return
        marker = self.root / ".xomacito-premiere-link.json"
        marker.write_text(
            json.dumps(
                {
                    "schema": 1,
                    "enabled": True,
                    "bin": "Xomacito Import",
                    "library": str(self.root),
                    "updatedAt": datetime.now().astimezone().isoformat(),
                },
                ensure_ascii=False,
                indent=2,
            ) + "\n",
            encoding="utf-8",
        )
        self.settings.set("premiere_auto_import_enabled", True)
        if panel_installed:
            message = (
                "Reinicia Premiere si estaba abierto y entra a Ventana > Plugins UXP > "
                "Xomacito Link. El menú >> sólo muestra paneles ya abiertos."
            )
            self._set_state(
                premiereLinkEnabled=True,
                status="Xomacito Link instalado. Ábrelo desde Ventana > Plugins UXP.",
            )
            self.notificationRequested.emit("success", "Xomacito Link instalado", message)
            return

        self._set_state(
            premiereLinkEnabled=True,
            status="Instala Xomacito Link, reinicia Premiere y ábrelo desde Ventana > Plugins UXP.",
        )
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(package)))
        self.notificationRequested.emit(
            "success", "Instalador de Xomacito Link abierto",
            "Al terminar, reinicia Premiere y abre Ventana > Plugins UXP > Xomacito Link.",
        )

    def shutdown(self):
        return None
