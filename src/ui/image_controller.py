from __future__ import annotations

import os
import shutil
import tempfile
import threading
import uuid
from io import BytesIO
from pathlib import Path
from urllib.parse import urlparse

import requests
from PIL import Image, UnidentifiedImageError
from PySide6.QtCore import QObject, Property, QMimeData, QUrl, Signal, Slot
from PySide6.QtGui import QDesktopServices, QGuiApplication
from PySide6.QtWidgets import QColorDialog, QFileDialog

from src.core.constants import (
    IMAGE_INPUT_FORMATS,
    IMAGE_RAW_FORMATS,
    REMBG_MODEL_FAMILIES,
    UPSCAYL_MODELS_MAP,
)
from src.core.downloader import (
    extract_info_resilient,
    extract_instagram_image_post_info,
    extract_x_media_post_info,
    is_instagram_post_url,
    is_x_status_url,
)
from src.core.processor import FFmpegProcessor
from src.core.image_intelligence import (
    PERFORMANCE_PROFILES,
    analyze_image,
    detect_hardware,
    estimate_output,
    performance_recipe,
)
from main import MODELS_PATH, UPSCALING_DIR

from .list_model import ObjectListModel
from .media_logic import safe_filename
from .settings_store import SettingsStore
from .workers import TaskPool


IMAGE_OPTIONS = {
    "resizeEnabled": False, "resizeWidth": "1920", "resizeHeight": "1080",
    "resizeMaintainAspect": True, "interpolation": "Lanczos (Mejor Calidad)",
    "canvasEnabled": False, "canvasOption": "Sin ajuste", "canvasWidth": "1080",
    "canvasHeight": "1080", "canvasMargin": 100, "canvasPosition": "Centro",
    "canvasOverflow": "Reducir hasta que quepa", "backgroundEnabled": False,
    "backgroundType": "Color Sólido", "backgroundColor": "#FFFFFF",
    "gradientColor1": "#102A43", "gradientColor2": "#20C9E8",
    "gradientDirection": "Horizontal (Izq → Der)", "backgroundImage": "",
    "pngTransparency": True, "pngCompression": 6, "jpgQuality": 90,
    "jpgSubsampling": "4:2:0 (Estándar)", "jpgProgressive": False,
    "webpLossless": False, "webpQuality": 90, "webpTransparency": True,
    "webpMetadata": False, "avifLossless": False, "avifQuality": 80,
    "avifSpeed": 6, "avifTransparency": True, "pdfCombine": False,
    "pdfTitle": "imagenes_combinadas", "tiffCompression": "LZW (Recomendada)",
    "tiffTransparency": True, "ico16": True, "ico32": True, "ico48": True,
    "ico64": True, "ico128": True, "ico256": True, "bmpRle": False,
    "pdfTransparent": False, "rembgEnabled": False, "rembgGpu": True,
    "rembgFamily": "BiRefNet (Next-Gen 2024)", "rembgModel": "General Lite (Rápido)",
    "rembgSmooth": 0, "rembgExpand": 0, "upscaleEnabled": False,
    "upscaleEngine": "Upscayl", "upscaleModel": "Real-ESRGAN (General / Fotografía)",
    "upscaleScale": "2", "upscaleDenoise": "0", "upscaleTile": "0", "upscaleTta": False,
    "performanceProfile": "Automático", "upscaleConcurrency": "Automático",
    "videoTitle": "video_xomacito", "videoWidth": "1920", "videoHeight": "1080",
    "videoFps": "30", "videoFrameDuration": "3", "videoFitMode": "Mantener Tamaño Original",
}

VIDEO_EXTENSIONS = {".mp4", ".mov", ".mkv", ".webm", ".avi", ".m4v"}

UPSCALE_PROFILES = {
    "Automático (recomendado)": {
        "model": "Real-ESRGAN (General / Fotografía)",
        "description": "Equilibrio seguro para fotos, capturas y recursos cotidianos.",
    },
    "Foto real": {
        "model": "Real-ESRGAN (General / Fotografía)",
        "description": "Recupera textura sin convertir la foto en una ilustración.",
    },
    "Anime e ilustración": {
        "model": "Real-ESRGAN (Anime / Ilustración)",
        "description": "Conserva líneas y colores planos con menos ruido.",
    },
    "Video animado": {
        "model": "Anime Video V3 (x4)",
        "description": "Modelo oficial optimizado para animación cuadro a cuadro.",
    },
    "Rápido": {
        "model": "Real-ESRGAN V3 (Ligero y Rápido)",
        "description": "Menor espera para lotes grandes y equipos modestos.",
    },
}

STABLE_REMBG_FAMILY = "BiRefNet (Next-Gen 2024)"
STABLE_REMBG_MODELS = (
    "General Lite (Rápido)",
    "General (Estándar)",
    "Portrait (Retratos)",
    "DIS (Bordes Finos/Complejo)",
)
STABLE_UPSCALE_MODELS = tuple(dict.fromkeys(
    profile["model"] for profile in UPSCALE_PROFILES.values()
))

TASK_DEFAULTS = {
    "removeBackground": {
        "format": "PNG", "rembgEnabled": True, "upscaleEnabled": False,
        "rembgFamily": "BiRefNet (Next-Gen 2024)", "rembgModel": "General Lite (Rápido)",
    },
    "upscaleImage": {
        "format": "PNG", "rembgEnabled": False, "upscaleEnabled": True,
        "upscaleEngine": "Upscayl", "upscaleModel": UPSCALE_PROFILES["Automático (recomendado)"]["model"],
    },
    "upscaleVideo": {
        "format": "MP4", "rembgEnabled": False, "upscaleEnabled": True,
        "upscaleEngine": "Upscayl", "upscaleModel": UPSCALE_PROFILES["Automático (recomendado)"]["model"],
    },
    "convert": {
        "format": "PNG", "rembgEnabled": False, "upscaleEnabled": False,
    },
}


class ImageController(QObject):
    stateChanged = Signal()
    optionsChanged = Signal()
    selectedChanged = Signal()
    progressReported = Signal(float, str)
    notificationRequested = Signal(str, str, str)

    ROLES = ["itemId", "path", "name", "page", "pages", "title", "status", "detail", "output", "preview", "mediaType"]

    def __init__(self, project_root, settings: SettingsStore, pool: TaskPool, app_version: str, parent=None):
        super().__init__(parent)
        self.project_root = Path(project_root)
        self.settings = settings
        self.pool = pool
        self.ffmpeg = FFmpegProcessor(app_version=app_version)
        self.inkscape = None
        self.processor = None
        self.converter = None
        self._engine_lock = threading.Lock()
        self.cancel_event = threading.Event()
        self.items = ObjectListModel(self.ROLES, self)
        upscayl_exe = Path(UPSCALING_DIR) / "upscayl" / "upscayl-bin.exe"
        self._hardware = detect_hardware(upscayl_exe)
        configured_output = Path(str(settings.get("image_output_path") or "")).expanduser()
        if not configured_output.is_absolute():
            configured_output = Path.home() / "Downloads"
            settings.set("image_output_path", str(configured_output))
        self._state = {
            "url": "", "outputPath": str(configured_output),
            "format": "PNG", "conflictPolicy": "Renombrar", "createSubfolder": False,
            "subfolderName": "imagenes_xomacito", "processOnlyNew": False,
            "status": "Importa imágenes, documentos o pega un enlace.", "progress": 0.0,
            "busy": False, "selectedIndex": -1, "previewSource": "", "resultPreviewSource": "",
            "lastOutput": "", "itemCount": 0, "task": settings.get("image_task", "removeBackground"),
            "upscaleProfile": "Automático (recomendado)",
            "analysis": {}, "analysisReady": False,
            "analysisTitle": "Análisis local pendiente",
            "analysisDetail": "Importa un recurso para crear una receta inteligente.",
            "recommendation": "Xomacito elegirá el modelo según el contenido.",
            "outputEstimate": "Importa un archivo para estimar la salida",
            "hardwareLabel": self._hardware["label"],
            "hardwareDetail": self._hardware["detail"],
            "previewBusy": False,
        }
        self._options = dict(IMAGE_OPTIONS)
        saved = settings.get("image_settings", {})
        if isinstance(saved, dict):
            self._options.update({key: value for key, value in saved.items() if key in self._options})
            if saved.get("format"): self._state["format"] = saved["format"]
        legacy_engines = {
            "realesrgan-ncnn-vulkan": "Upscayl",
            "waifu2x-ncnn-vulkan": "Waifu2x",
            "srmd-ncnn-vulkan": "SRMD",
        }
        self._options["upscaleEngine"] = legacy_engines.get(
            self._options.get("upscaleEngine"), self._options.get("upscaleEngine", "Upscayl")
        )
        if self._options["upscaleModel"] not in UPSCAYL_MODELS_MAP.values():
            self._options["upscaleModel"] = UPSCALE_PROFILES["Automático (recomendado)"]["model"]
        # Las versiones antiguas permitían guardar familias enormes o modelos
        # experimentales. Se migran a perfiles curados para evitar resultados
        # impredecibles y descargas que no podían completarse.
        if self._options.get("rembgFamily") != STABLE_REMBG_FAMILY:
            self._options["rembgFamily"] = STABLE_REMBG_FAMILY
        if self._options.get("rembgModel") not in STABLE_REMBG_MODELS:
            self._options["rembgModel"] = STABLE_REMBG_MODELS[0]
        if self._options.get("upscaleModel") not in STABLE_UPSCALE_MODELS:
            self._options["upscaleModel"] = UPSCALE_PROFILES["Automático (recomendado)"]["model"]
        self._options["upscaleEngine"] = "Upscayl"
        active_task = self._state["task"] if self._state["task"] in TASK_DEFAULTS else "removeBackground"
        self._state["task"] = active_task
        for key in ("rembgEnabled", "upscaleEnabled"):
            self._options[key] = TASK_DEFAULTS[active_task][key]
        if active_task == "upscaleVideo":
            self._state["format"] = "MP4"
        elif active_task == "removeBackground" and self._state["format"] not in {"PNG", "WEBP"}:
            self._state["format"] = "PNG"
        self._next_id = 1
        self.progressReported.connect(self._apply_progress)

    def _ensure_engines(self):
        """Carga el motor pesado de imagen sólo cuando el usuario lo necesita."""
        if self.converter is not None:
            return
        with self._engine_lock:
            if self.converter is not None:
                return
            from src.core.image_converter import ImageConverter
            from src.core.image_processor import ImageProcessor
            from src.core.inkscape_service import InkscapeService

            self.inkscape = InkscapeService(self.settings.get("inkscape_path") or None)
            poppler = self.project_root / "bin" / "poppler"
            self.processor = ImageProcessor(str(poppler), self.inkscape, self.ffmpeg.ffmpeg_path)
            self.converter = ImageConverter(str(poppler), self.inkscape, self.ffmpeg)

    @Property("QVariantMap", notify=stateChanged)
    def state(self): return self._state

    @Property("QVariantMap", notify=optionsChanged)
    def options(self): return self._options

    @Property(QObject, constant=True)
    def model(self): return self.items

    @Property("QVariantMap", notify=selectedChanged)
    def selected(self):
        return self.items.item(self._state["selectedIndex"]) or {}

    @Property("QStringList", constant=True)
    def formats(self):
        return ["No Convertir", "PNG", "JPEG", "JPG", "WEBP", "AVIF", "PDF", "TIFF", "ICO", "BMP", ".mp4 (H.264)", ".mov (ProRes)", ".webm (VP9)", ".gif (Animado)"]

    @Property("QStringList", constant=True)
    def rembgFamilies(self): return [STABLE_REMBG_FAMILY]

    @Property("QStringList", constant=True)
    def upscaleProfiles(self): return list(UPSCALE_PROFILES)

    @Property("QStringList", constant=True)
    def upscaleModels(self): return list(STABLE_UPSCALE_MODELS)

    @Property("QStringList", constant=True)
    def performanceProfiles(self): return list(PERFORMANCE_PROFILES)

    @Slot(str, result="QStringList")
    def rembgModels(self, family):
        return list(STABLE_REMBG_MODELS) if family == STABLE_REMBG_FAMILY else []

    def _set_state(self, **values):
        changed = False
        for key, value in values.items():
            if self._state.get(key) != value:
                self._state[key] = value; changed = True
        if changed: self.stateChanged.emit()

    @Slot(str, "QVariant")
    def setValue(self, key, value):
        if key not in self._state: return
        self._set_state(**{key: value})
        if key == "outputPath": self.settings.set("image_output_path", str(value))
        elif key == "format":
            saved = dict(self._options); saved["format"] = value
            self.settings.set("image_settings", saved)

    @Slot(str, "QVariant")
    def setOption(self, key, value):
        if key not in self._options or self._options[key] == value: return
        self._options[key] = value
        self.optionsChanged.emit()
        saved = dict(self._options); saved["format"] = self._state["format"]
        self.settings.set("image_settings", saved)
        if key == "upscaleScale":
            self._refresh_output_estimate()

    @Slot(str)
    def setTask(self, task):
        if task not in TASK_DEFAULTS or self._state["task"] == task:
            return
        old_video = self._state["task"] == "upscaleVideo"
        new_video = task == "upscaleVideo"
        if old_video != new_video and self.items.rowCount():
            self.clear()
        defaults = TASK_DEFAULTS[task]
        self._state["task"] = task
        self._state["format"] = defaults["format"]
        if task in {"upscaleImage", "upscaleVideo"}:
            self._state["upscaleProfile"] = "Automático (recomendado)"
        for key, value in defaults.items():
            if key != "format":
                self._options[key] = value
        self.stateChanged.emit()
        self.optionsChanged.emit()
        self.settings.set("image_task", task)
        self.settings.set("image_settings", {**self._options, "format": self._state["format"]})
        self._apply_smart_recipe(self._state.get("analysis") or {})
        self._refresh_output_estimate()

    @Slot(str)
    def setUpscaleProfile(self, profile):
        data = UPSCALE_PROFILES.get(profile)
        if not data:
            return
        self._state["upscaleProfile"] = profile
        self._options["upscaleEngine"] = "Upscayl"
        if profile == "Automático (recomendado)" and self._state.get("analysis"):
            self._options["upscaleModel"] = self._state["analysis"].get("upscaleModel", data["model"])
        else:
            self._options["upscaleModel"] = data["model"]
        self.stateChanged.emit()
        self.optionsChanged.emit()

    @Slot(str)
    def setPerformanceProfile(self, profile):
        if profile not in PERFORMANCE_PROFILES:
            return
        self._options["performanceProfile"] = profile
        recipe = performance_recipe(profile, self._hardware)
        self._options["upscaleConcurrency"] = recipe["concurrency"]
        self._options["upscaleTile"] = recipe["tile"]
        self._options["upscaleTta"] = recipe["tta"]
        self.optionsChanged.emit()
        saved = dict(self._options); saved["format"] = self._state["format"]
        self.settings.set("image_settings", saved)

    def _refresh_output_estimate(self):
        analysis = self._state.get("analysis") or {}
        self._set_state(outputEstimate=estimate_output(
            analysis, self._options.get("upscaleScale", "1"), self._state.get("task", "convert")
        ))

    def _apply_smart_recipe(self, analysis):
        if not analysis:
            return
        task = self._state.get("task")
        recommendation = "Conversión sin IA; se conservarán proporciones y metadatos compatibles."
        changed = False
        if task == "removeBackground":
            model = analysis.get("rembgModel", STABLE_REMBG_MODELS[0])
            if self._options.get("rembgModel") != model:
                self._options["rembgModel"] = model; changed = True
            recommendation = f"{model}: {analysis.get('rembgReason', 'recorte general')}."
        elif task in {"upscaleImage", "upscaleVideo"}:
            if self._state.get("upscaleProfile") == "Automático (recomendado)":
                model = analysis.get("upscaleModel", UPSCALE_PROFILES["Automático (recomendado)"]["model"])
                if task == "upscaleVideo" and analysis.get("kind") == "illustration":
                    model = UPSCALE_PROFILES["Video animado"]["model"]
                if self._options.get("upscaleModel") != model:
                    self._options["upscaleModel"] = model; changed = True
            recommendation = f"{self._options['upscaleModel']}: {analysis.get('upscaleReason', 'mejora equilibrada')}."
        if changed:
            self.optionsChanged.emit()
        self._set_state(recommendation=recommendation)

    @Slot(str, result=str)
    def chooseColor(self, current):
        color = QColorDialog.getColor()
        return color.name() if color.isValid() else current

    @Slot()
    def chooseBackgroundImage(self):
        path, _ = QFileDialog.getOpenFileName(None, "Imagen de fondo", "", "Imágenes (*.png *.jpg *.jpeg *.webp *.avif *.bmp *.tiff)")
        if path: self.setOption("backgroundImage", path)

    @Slot()
    def chooseOutputFolder(self):
        folder = QFileDialog.getExistingDirectory(None, "Carpeta de salida", self._state["outputPath"])
        if folder: self.setValue("outputPath", folder)

    @Slot()
    def importFiles(self):
        video = " *.mp4 *.mov *.mkv *.webm *.avi *.m4v" if self._state["task"] == "upscaleVideo" else ""
        paths, _ = QFileDialog.getOpenFileNames(
            None, "Importar recursos", "",
            f"Recursos compatibles (*.png *.jpg *.jpeg *.webp *.avif *.bmp *.tif *.tiff *.ico *.gif *.svg *.eps *.ai *.pdf *.ps *.cr2 *.dng *.arw *.nef *.orf *.rw2 *.sr2 *.raf *.cr3 *.pef{video});;Todos (*.*)"
        )
        self.addPaths(paths)

    @Slot()
    def importFolder(self):
        folder = QFileDialog.getExistingDirectory(None, "Importar carpeta")
        if not folder: return
        valid = {".png", ".jpg", ".jpeg", ".webp", ".avif", ".bmp", ".tif", ".tiff", ".ico", ".gif", ".svg", ".eps", ".ai", ".pdf", ".ps"} | {ext.lower() for ext in IMAGE_RAW_FORMATS}
        if self._state["task"] == "upscaleVideo":
            valid |= VIDEO_EXTENSIONS
        self.addPaths([str(path) for path in Path(folder).rglob("*") if path.is_file() and path.suffix.lower() in valid])

    @Slot("QStringList")
    def addPaths(self, paths):
        additions = []
        for value in paths:
            path = QUrl(str(value)).toLocalFile() if str(value).startswith("file:") else str(value)
            if not Path(path).is_file(): continue
            ext = Path(path).suffix.lower()
            is_video = ext in VIDEO_EXTENSIONS
            if self._state["task"] == "upscaleVideo" and not is_video:
                continue
            if self._state["task"] != "upscaleVideo" and is_video:
                continue
            pages = 1
            if ext in {".pdf", ".ai", ".eps", ".ps"}:
                try:
                    self._ensure_engines()
                    pages = max(1, int(self.processor.get_document_page_count(path)))
                except Exception: pages = 1
            for page in range(1, pages + 1):
                item_id = str(self._next_id); self._next_id += 1
                suffix = f" · página {page}/{pages}" if pages > 1 else ""
                additions.append({
                    "itemId": item_id, "path": path, "name": Path(path).name + suffix,
                    "page": page, "pages": pages, "title": Path(path).stem,
                    "status": "PENDING", "detail": "Video listo" if is_video else "Imagen lista",
                    "output": "", "preview": "", "mediaType": "video" if is_video else "image",
                })
        for item in additions: self.items.append(item)
        self._set_state(itemCount=self.items.rowCount(), status=f"{self.items.rowCount()} recursos listos.")
        if additions and self._state["selectedIndex"] < 0: self.select(0)

    @Slot()
    def paste(self):
        mime = QGuiApplication.clipboard().mimeData()
        paths = [url.toLocalFile() for url in mime.urls() if url.isLocalFile()]
        if paths:
            self.addPaths(paths); return
        if mime.hasImage():
            target = Path(tempfile.gettempdir()) / f"xomacito_clipboard_{uuid.uuid4().hex}.png"
            if QGuiApplication.clipboard().image().save(str(target), "PNG"):
                self.addPaths([str(target)])
                return
        text = mime.text().strip()
        if text.startswith(("http://", "https://")):
            self.setValue("url", text); self.analyzeUrl()
        elif text and Path(text).exists():
            self.addPaths([text])

    @Slot()
    def analyzeUrl(self):
        url = str(self._state["url"]).strip()
        if not url or self._state["busy"]: return
        self._set_state(busy=True, progress=-1.0, status="Buscando imagen o miniatura…")
        self.pool.submit(self._url_image_worker, url, on_result=self._url_images_done, on_error=lambda m, d: self._failed(m, d))

    def _url_image_worker(self, url):
        host = urlparse(url).netloc.casefold()
        referer = "https://www.pinterest.com/" if "pinimg.com" in host or "pinterest." in host else url
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept": "image/avif,image/webp,image/apng,image/*,*/*;q=0.8",
            "Accept-Language": "es-PE,es;q=0.9,en;q=0.8",
            "Referer": referer,
        }
        image_urls = []
        cookie_mode = self.settings.get("cookies_mode", "No usar")
        if is_x_status_url(url):
            info = extract_x_media_post_info(url)
            if info and info.get("xomacito_media_type") == "image":
                image_urls = info.get("xomacito_images") or []
            elif info:
                raise RuntimeError(
                    "La publicación de X contiene un GIF o video. Descárgala desde la pestaña Descargar."
                )
        if is_instagram_post_url(url):
            cookie_options = {"quiet": True}
            if cookie_mode == "Archivo Manual..." and self.settings.get("cookies_path"):
                cookie_options["cookiefile"] = self.settings.get("cookies_path")
            elif cookie_mode != "No usar":
                browser = self.settings.get("selected_browser", "chrome")
                profile = self.settings.get("browser_profile", "")
                cookie_options["cookiesfrombrowser"] = (
                    (browser, profile) if profile else (browser,)
                )
            info = extract_instagram_image_post_info(url, ydl_options=cookie_options)
            if info:
                image_urls = info.get("xomacito_images") or [info.get("url") or info.get("thumbnail")]
        if not image_urls:
            try:
                response = requests.get(url, headers=headers, timeout=40, allow_redirects=True)
                response.raise_for_status()
                if response.headers.get("Content-Type", "").lower().startswith("image/"):
                    image_urls = [response.url]
            except requests.RequestException:
                pass
        if not image_urls:
            info = extract_info_resilient(url, {"noplaylist": False, "quiet": True}, download=False)
            image_urls = (info or {}).get("xomacito_images") or [(info or {}).get("thumbnail")]
        image_urls = [value for value in image_urls if value]
        if not image_urls:
            if is_instagram_post_url(url) and cookie_mode == "No usar":
                raise RuntimeError(
                    "Instagram sólo mostró la portada. Selecciona tu navegador en "
                    "Configuración > Cookies para importar todas las imágenes del carrusel."
                )
            raise RuntimeError("El enlace no contiene una imagen accesible.")
        targets = []
        for image_url in image_urls:
            image_host = urlparse(image_url).netloc.casefold()
            image_headers = dict(headers)
            if "pinimg.com" in image_host:
                image_headers["Referer"] = "https://www.pinterest.com/"
            elif "cdninstagram.com" in image_host or "fbcdn.net" in image_host:
                image_headers["Referer"] = "https://www.instagram.com/"
            response = requests.get(image_url, headers=image_headers, timeout=40, allow_redirects=True)
            response.raise_for_status()
            try:
                with Image.open(BytesIO(response.content)) as image:
                    detected_format = str(image.format or "JPEG").upper()
                    image.verify()
            except (UnidentifiedImageError, OSError, ValueError) as exc:
                raise RuntimeError("El servidor no entregó una imagen válida.") from exc
            suffix = Path(urlparse(response.url).path).suffix.lower()
            if suffix not in {".png", ".jpg", ".jpeg", ".webp", ".avif"}:
                suffix = {
                    "PNG": ".png", "WEBP": ".webp", "AVIF": ".avif",
                    "JPEG": ".jpeg", "JPG": ".jpg",
                }.get(detected_format, ".jpg")
            target = Path(tempfile.gettempdir()) / f"xomacito_url_{uuid.uuid4().hex}{suffix}"
            target.write_bytes(response.content)
            targets.append(str(target))
        return targets

    def _url_images_done(self, paths):
        count = len(paths)
        self._set_state(
            busy=False, progress=1.0,
            status=f"{count} imagen{'es' if count != 1 else ''} importada{'s' if count != 1 else ''}.",
            url="",
        )
        self.addPaths(paths)

    @Slot(int)
    def select(self, index):
        if not 0 <= index < self.items.rowCount(): return
        self._set_state(
            selectedIndex=index, previewSource="", resultPreviewSource="",
            analysis={}, analysisReady=False, analysisTitle="Analizando en tu equipo…",
            analysisDetail="Leyendo detalle, color, compresión y dimensiones.",
            recommendation="Preparando una receta inteligente.",
        )
        self.selectedChanged.emit()
        item = self.items.item(index)
        self.pool.submit(
            self._thumbnail_worker, item,
            on_result=lambda path, row=index: self._thumbnail_done(row, path),
            on_error=lambda message, detail: self._failed_preview(message, detail),
        )

    def _thumbnail_worker(self, item):
        self._ensure_engines()
        if item.get("mediaType") == "video" or Path(item["path"]).suffix.lower() in VIDEO_EXTENSIONS:
            frame = self.ffmpeg.get_frame_from_video(item["path"])
            if not frame:
                raise RuntimeError("No se pudo leer un fotograma del video.")
            with Image.open(frame) as sample:
                analysis = analyze_image(sample, source_path=item["path"])
            analysis["mediaType"] = "video"
            return {"path": str(frame), "analysis": analysis}
        thumb = self.processor.generate_thumbnail(
            item["path"], size=(900, 700), page_number=item["page"],
            dpi=int(self.settings.get("preview_vector_dpi", 96)),
        )
        if thumb is None: raise RuntimeError("No se pudo generar la previsualización.")
        target = Path(tempfile.gettempdir()) / f"xomacito_preview_{item['itemId']}.png"
        thumb.save(target, "PNG")
        return {"path": str(target), "analysis": analyze_image(thumb, source_path=item["path"])}

    def _thumbnail_done(self, row, payload):
        if isinstance(payload, dict):
            path = payload.get("path", "")
            analysis = payload.get("analysis") or {}
        else:
            path = payload
            analysis = {}
        if row < self.items.rowCount(): self.items.update_item(row, {"preview": QUrl.fromLocalFile(path).toString()})
        if self._state["selectedIndex"] == row:
            self._set_state(
                previewSource=QUrl.fromLocalFile(path).toString(), analysis=analysis,
                analysisReady=bool(analysis),
                analysisTitle=analysis.get("content", "Recurso listo"),
                analysisDetail=(
                    f"{analysis.get('technical', '')} · {analysis.get('issue', 'análisis completado')}"
                    if analysis else "Vista previa preparada."
                ),
            )
            self._apply_smart_recipe(analysis)
            self._refresh_output_estimate()
            self.selectedChanged.emit()

    @Slot(str)
    def setSelectedTitle(self, title):
        row = self._state["selectedIndex"]
        if row >= 0:
            self.items.update_item(row, {"title": title}); self.selectedChanged.emit()

    @Slot(int)
    def remove(self, index):
        if not 0 <= index < self.items.rowCount(): return
        self.items.remove(index)
        next_index = min(index, self.items.rowCount() - 1)
        self._set_state(itemCount=self.items.rowCount(), selectedIndex=next_index)
        if next_index >= 0: self.select(next_index)
        else: self._set_state(previewSource="", resultPreviewSource="", status="Lista vacía.")

    @Slot()
    def removeSelected(self): self.remove(self._state["selectedIndex"])

    @Slot()
    def clear(self):
        if self._state["busy"]: return
        self.items.clear(); self._set_state(itemCount=0, selectedIndex=-1, previewSource="", resultPreviewSource="", status="Lista vacía.")
        self.selectedChanged.emit()

    def _conversion_options(self):
        performance = performance_recipe(self._options.get("performanceProfile", "Automático"), self._hardware)
        options = {
            "format": self._state["format"], "resize_enabled": self._options["resizeEnabled"],
            "resize_width": self._options["resizeWidth"] or None, "resize_height": self._options["resizeHeight"] or None,
            "resize_maintain_aspect": self._options["resizeMaintainAspect"], "interpolation_method": self._options["interpolation"],
            "canvas_enabled": self._options["canvasEnabled"], "canvas_option": self._options["canvasOption"],
            "canvas_width": self._options["canvasWidth"] or None, "canvas_height": self._options["canvasHeight"] or None,
            "canvas_margin": int(self._options["canvasMargin"] or 100), "canvas_position": self._options["canvasPosition"],
            "canvas_overflow_mode": self._options["canvasOverflow"], "background_enabled": self._options["backgroundEnabled"],
            "background_type": self._options["backgroundType"], "background_color": self._options["backgroundColor"],
            "background_gradient_color1": self._options["gradientColor1"], "background_gradient_color2": self._options["gradientColor2"],
            "background_gradient_direction": self._options["gradientDirection"], "background_image_path": self._options["backgroundImage"] or None,
            "png_transparency": self._options["pngTransparency"], "png_compression": int(self._options["pngCompression"]),
            "jpg_quality": int(self._options["jpgQuality"]), "jpg_subsampling": self._options["jpgSubsampling"],
            "jpg_progressive": self._options["jpgProgressive"], "webp_lossless": self._options["webpLossless"],
            "webp_quality": int(self._options["webpQuality"]), "webp_transparency": self._options["webpTransparency"],
            "webp_metadata": self._options["webpMetadata"], "avif_lossless": self._options["avifLossless"],
            "avif_quality": int(self._options["avifQuality"]), "avif_speed": int(self._options["avifSpeed"]),
            "avif_transparency": self._options["avifTransparency"], "pdf_combine": self._options["pdfCombine"],
            "pdf_combined_title": self._options["pdfTitle"], "tiff_compression": self._options["tiffCompression"],
            "tiff_transparency": self._options["tiffTransparency"], "ico_sizes": {size: bool(self._options[f"ico{size}"]) for size in (16, 32, 48, 64, 128, 256)},
            "bmp_rle": self._options["bmpRle"], "vector_dpi": int(self.settings.get("vector_dpi", 300)),
            "force_background": bool(self.settings.get("vector_force_background", False)), "pdf_transparent": self._options["pdfTransparent"],
            "rembg_enabled": self._options["rembgEnabled"], "rembg_gpu": self._options["rembgGpu"],
            "rembg_model": self._real_rembg_model(), "rembg_edge_smooth": int(self._options["rembgSmooth"]),
            "rembg_edge_expand": int(self._options["rembgExpand"]), "upscale_enabled": self._options["upscaleEnabled"],
            "upscale_engine": self._options["upscaleEngine"], "upscale_model_friendly": self._options["upscaleModel"],
            "upscale_scale": self._options["upscaleScale"], "upscale_denoise": self._options["upscaleDenoise"],
            "upscale_tile": self._options["upscaleTile"], "upscale_tta": self._options["upscaleTta"],
            "upscale_concurrency": (
                performance["concurrency"]
                if self._options.get("upscaleConcurrency") == "Automático"
                else self._options["upscaleConcurrency"]
            ),
            "performance_profile": self._options["performanceProfile"],
            "encoder_preset": performance["encoderPreset"],
            "encoder_crf": performance["encoderCrf"],
            "video_custom_title": self._options["videoTitle"], "video_custom_width": self._options["videoWidth"],
            "video_custom_height": self._options["videoHeight"], "video_fps": self._options["videoFps"],
            "video_frame_duration": self._options["videoFrameDuration"], "video_fit_mode": self._options["videoFitMode"],
        }
        return options

    def _ensure_upscaler(self):
        from src.core.setup import check_and_download_upscaling_tools

        def setup_progress(message, percent):
            value = max(0.01, min(0.14, float(percent or 0) / 100.0 * 0.14))
            self.progressReported.emit(value, message or "Preparando mejora local…")

        if not check_and_download_upscaling_tools(setup_progress, target_tool="Upscayl"):
            raise RuntimeError("No se pudo preparar el motor local Upscayl. Revisa tu conexión.")

    @Slot()
    def preparePreview(self):
        row = self._state.get("selectedIndex", -1)
        if self._state.get("busy") or not 0 <= row < self.items.rowCount():
            return
        item = dict(self.items.item(row))
        options = self._conversion_options()
        task = self._state["task"]
        self.cancel_event.clear()
        self._set_state(
            busy=True, previewBusy=True, progress=0.0,
            status="Preparando una muestra local; el original no se modifica…",
        )
        self.pool.submit(
            self._preview_worker, item, options, task,
            on_result=self._preview_done,
            on_error=lambda m, d: self._failed(m, d),
        )

    def _preview_worker(self, item, options, task):
        self._ensure_engines()
        source = item["path"]
        if item.get("mediaType") == "video":
            source = self.ffmpeg.get_frame_from_video(source)
            if not source:
                raise RuntimeError("No se pudo extraer el fotograma de prueba.")
        with Image.open(source) as image:
            image.load()
            sample = image.convert("RGBA" if "A" in image.getbands() else "RGB")
            max_side = 640 if str(options.get("upscale_scale")) == "4" else 960
            sample.thumbnail((max_side, max_side), Image.Resampling.LANCZOS)
            preview_input = Path(tempfile.gettempdir()) / f"xomacito_ai_preview_in_{uuid.uuid4().hex}.png"
            sample.save(preview_input, "PNG", compress_level=1)
        preview_output = Path(tempfile.gettempdir()) / f"xomacito_ai_preview_out_{uuid.uuid4().hex}.png"
        try:
            options = dict(options)
            options.update({
                "format": "PNG", "resize_enabled": False, "canvas_enabled": False,
                "background_enabled": False, "png_compression": 2,
            })
            if options.get("rembg_enabled"):
                self._ensure_rembg_model(options)
            if options.get("upscale_enabled"):
                self._ensure_upscaler()
            self.converter.prepare_ai_sessions(
                options,
                progress_callback=lambda p, m: self.progressReported.emit(
                    max(0.05, min(0.25, float(p or 0) / 100.0)), m or "Cargando modelo…"
                ),
            )
            ok = self.converter.convert_file(
                str(preview_input), str(preview_output), options,
                progress_callback=lambda p, m=None: self.progressReported.emit(
                    max(0.25, min(0.95, float(p or 0) / 100.0)), m or "Generando muestra…"
                ),
                cancellation_event=self.cancel_event,
            )
            if not ok or not preview_output.is_file():
                raise RuntimeError("No se pudo generar la muestra.")
            return str(preview_output)
        finally:
            preview_input.unlink(missing_ok=True)
            if not self.settings.get("keep_ai_models_in_memory", False):
                self.converter.clear_ai_sessions()

    def _preview_done(self, path):
        self._set_state(
            busy=False, previewBusy=False, progress=1.0,
            resultPreviewSource=QUrl.fromLocalFile(path).toString(),
            status="Vista previa lista. Compara el antes y el después.",
        )

    def _real_rembg_model(self):
        family = self._options["rembgFamily"]; label = self._options["rembgModel"]
        data = REMBG_MODEL_FAMILIES.get(family, {}).get(label, {})
        return data.get("file", label or "u2netp.onnx")

    def _ensure_rembg_model(self, options):
        """Instala bajo demanda el modelo elegido, sin congelar el hilo de la interfaz."""
        if not options.get("rembg_enabled"):
            return
        family = self._options.get("rembgFamily")
        label = self._options.get("rembgModel")
        data = REMBG_MODEL_FAMILIES.get(family, {}).get(label, {})
        filename = data.get("file")
        if not filename:
            raise RuntimeError("No se pudo resolver el modelo para quitar el fondo.")
        folder = MODELS_PATH / data.get("folder", "rembg")
        target = folder / filename
        if target.exists():
            return
        url = data.get("url")
        if not url or "/tree/" in url:
            raise RuntimeError("Este modelo requiere instalación manual. Elige BiRefNet General Lite o U2Net.")
        folder.mkdir(parents=True, exist_ok=True)
        partial = target.with_suffix(target.suffix + ".part")
        self.progressReported.emit(0.01, f"Descargando {label} por primera vez…")
        try:
            with requests.get(url, stream=True, timeout=120) as response:
                response.raise_for_status()
                total = int(response.headers.get("content-length", 0))
                done = 0
                with partial.open("wb") as handle:
                    for chunk in response.iter_content(1024 * 1024):
                        if self.cancel_event.is_set():
                            raise RuntimeError("Descarga del modelo cancelada.")
                        if not chunk:
                            continue
                        handle.write(chunk)
                        done += len(chunk)
                        if total:
                            self.progressReported.emit(
                                min(0.12, 0.01 + (done / total) * 0.11),
                                f"Instalando modelo IA… {done * 100 // total}%",
                            )
            partial.replace(target)
        finally:
            partial.unlink(missing_ok=True)

    @Slot()
    def start(self):
        if self._state["busy"] or not self.items.rowCount(): return
        output = Path(str(self._state["outputPath"])).expanduser()
        if not output.is_absolute():
            output = Path.home() / "Downloads"
            self.setValue("outputPath", str(output))
        if self._state["createSubfolder"]: output /= safe_filename(self._state["subfolderName"])
        output.mkdir(parents=True, exist_ok=True)
        self.cancel_event.clear(); self._set_state(busy=True, progress=0.0, status="Preparando conversión…", lastOutput="")
        snapshot = self.items.items(); options = self._conversion_options()
        self.pool.submit(
            self._process_worker, snapshot, output, options,
            on_result=self._process_done, on_error=lambda m, d: self._failed(m, d),
        )

    def _process_worker(self, items, output_dir: Path, options):
        self._ensure_engines()
        if self._state["task"] == "upscaleVideo":
            return self._upscale_videos_worker(items, output_dir, options)
        if str(options["format"]).startswith("."):
            return self._video_worker(items, output_dir, options)
        self._ensure_rembg_model(options)
        if options.get("upscale_enabled"):
            self._ensure_upscaler()
        self.converter.prepare_ai_sessions(options, progress_callback=lambda p, m: self.progressReported.emit((p or 0) / 100.0, m or "Preparando IA…"))
        if self.settings.get("inkscape_enabled", True): self.inkscape.start_session()
        outputs = []; errors = []
        try:
            for index, item in enumerate(items):
                if self.cancel_event.is_set(): raise RuntimeError("Proceso cancelado.")
                if self._state["processOnlyNew"] and item.get("output") and Path(item["output"]).exists():
                    outputs.append(item["output"]); continue
                path = self._output_path(output_dir, item, options["format"])
                path = self._conflict_path(path)
                if path is None: continue
                base = index / len(items)
                def callback(percent, message=None):
                    value = base + (float(percent or 0) / 100.0) / len(items)
                    self.progressReported.emit(value, message or f"Procesando {item['name']}…")
                try:
                    ok = self.converter.convert_file(item["path"], str(path), options, page_number=item["page"], progress_callback=callback, cancellation_event=self.cancel_event)
                    if ok: outputs.append(str(path))
                    else: errors.append(f"{item['name']}: conversión incompleta")
                except Exception as exc:
                    errors.append(f"{item['name']}: {exc}")
            if options["format"] == "PDF" and options.get("pdf_combine") and len(outputs) > 1:
                combined = self._unique(output_dir / f"{safe_filename(options['pdf_combined_title'])}.pdf")
                if self.converter.combine_pdfs(outputs, str(combined)):
                    for path in outputs: Path(path).unlink(missing_ok=True)
                    outputs = [str(combined)]
        finally:
            self.inkscape.stop_session()
            if not self.settings.get("keep_ai_models_in_memory", False): self.converter.clear_ai_sessions()
        if errors: raise RuntimeError("\n".join(errors[:12]))
        if not outputs: raise RuntimeError("No se generó ningún archivo.")
        return outputs

    def _upscale_videos_worker(self, items, output_dir, options):
        from src.core.video_upscaler import VideoUpscaler

        if any(item.get("mediaType") != "video" for item in items):
            raise RuntimeError("Para mejorar video, importa únicamente archivos de video.")

        self._ensure_upscaler()
        outputs = []
        for index, item in enumerate(items):
            if self.cancel_event.is_set():
                raise RuntimeError("Proceso cancelado.")
            output = self._conflict_path(output_dir / f"{safe_filename(item['title'])}_mejorado.mp4")
            if output is None:
                continue

            def report(percent, message, base=index):
                value = (base + float(percent or 0) / 100.0) / len(items)
                self.progressReported.emit(value, message)

            upscaler = VideoUpscaler(
                ffmpeg_dir=str(Path(self.ffmpeg.ffmpeg_path).parent),
                upscaling_dir=UPSCALING_DIR,
                cancellation_event=self.cancel_event,
                progress_callback=report,
            )
            video_options = {
                **options,
                "upscale_engine": "Upscayl",
                "upscale_model_friendly": options["upscale_model_friendly"],
                "upscale_container": ".mp4",
            }
            outputs.append(upscaler.upscale_video(item["path"], str(output), video_options))
        if not outputs:
            raise RuntimeError("No se generó ningún video.")
        return outputs

    def _video_worker(self, items, output_dir, options):
        extension = str(options["format"]).split()[0]
        output = self._conflict_path(output_dir / f"{safe_filename(options['video_custom_title'])}{extension}")
        if output is None: raise RuntimeError("Exportación cancelada.")
        pairs = [(item["path"], item["page"]) for item in items]
        result = self.converter.create_video_from_images(
            pairs, str(output), options,
            lambda _stage, percent, message: self.progressReported.emit(float(percent or 0) / 100.0, message or "Creando video…"),
            self.cancel_event,
        )
        return [str(result)]

    def _output_path(self, folder, item, output_format):
        if output_format == "No Convertir": extension = Path(item["path"]).suffix
        elif output_format == "JPEG": extension = ".jpeg"
        elif output_format == "JPG": extension = ".jpg"
        else: extension = "." + str(output_format).lower()
        page = f"_pagina_{item['page']}" if item["pages"] > 1 else ""
        return folder / f"{safe_filename(item['title'])}{page}{extension}"

    def _conflict_path(self, path):
        if not path.exists(): return path
        policy = self._state["conflictPolicy"]
        if policy == "Omitir": return None
        if policy == "Sobrescribir": return path
        return self._unique(path)

    @staticmethod
    def _unique(path):
        counter = 1; candidate = path
        while candidate.exists():
            candidate = path.with_stem(f"{path.stem}_{counter}"); counter += 1
        return candidate

    def _process_done(self, outputs):
        output_set = list(outputs)
        for row, item in enumerate(self.items.items()):
            matching = next((path for path in output_set if Path(path).stem.startswith(safe_filename(item["title"]))), "")
            if matching: self.items.update_item(row, {"status": "COMPLETED", "detail": "Completado", "output": matching})
        first = outputs[0]
        self._set_state(busy=False, progress=1.0, status=f"Completado: {len(outputs)} archivos.", lastOutput=first)
        if Path(first).is_file():
            self.pool.submit(
                self._thumbnail_worker,
                {"path": first, "page": 1, "itemId": "result", "mediaType": "image"},
                on_result=lambda payload: self._set_state(
                    resultPreviewSource=QUrl.fromLocalFile(
                        payload.get("path", "") if isinstance(payload, dict) else payload
                    ).toString()
                ),
            )
        self.notificationRequested.emit("success", "Conversión completada", str(Path(first).parent))

    @Slot()
    def cancel(self):
        self.cancel_event.set(); self.ffmpeg.cancel_current_process(); self._set_state(status="Cancelando…")

    @Slot()
    def openOutput(self):
        target = Path(self._state["lastOutput"] or self._state["outputPath"])
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(target if target.is_dir() else target.parent)))

    @Slot()
    def copyResult(self):
        target = self._state["lastOutput"]
        if not target or not Path(target).is_file(): return
        mime = QMimeData(); mime.setUrls([QUrl.fromLocalFile(target)]); QGuiApplication.clipboard().setMimeData(mime)
        self.notificationRequested.emit("success", "Copiado", "El archivo está en el portapapeles.")

    @Slot()
    def browseModelFolder(self):
        folder = MODELS_PATH / "rembg"; folder.mkdir(parents=True, exist_ok=True)
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(folder)))

    @Slot()
    def browseUpscaleFolder(self):
        folder = MODELS_PATH / "upscaling"; folder.mkdir(parents=True, exist_ok=True)
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(folder)))

    @Slot(float, str)
    def _apply_progress(self, value, message): self._set_state(progress=value, status=message)

    def _failed(self, message, detail=""):
        cancelled = self.cancel_event.is_set() or "cancel" in message.lower()
        self._set_state(busy=False, previewBusy=False, progress=0.0, status="Proceso cancelado." if cancelled else message)
        if not cancelled:
            print(detail); self.notificationRequested.emit("error", "Error de procesamiento", message)

    def _failed_preview(self, message, detail):
        print(detail); self._set_state(previewSource="", status=f"Vista previa no disponible: {message}")

    def shutdown(self):
        self.cancel_event.set()
        self.ffmpeg.cancel_current_process()
        if self.inkscape is not None:
            self.inkscape.stop_session()
        if self.converter is not None:
            self.converter.clear_ai_sessions()
