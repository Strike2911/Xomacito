from __future__ import annotations

import os
import shutil
import tempfile
import threading
from pathlib import Path
from urllib.parse import urlparse

import requests
from PySide6.QtCore import QObject, Property, QMimeData, QUrl, Signal, Slot
from PySide6.QtGui import QDesktopServices, QGuiApplication
from PySide6.QtWidgets import QColorDialog, QFileDialog

from src.core.constants import IMAGE_INPUT_FORMATS, IMAGE_RAW_FORMATS, REMBG_MODEL_FAMILIES
from src.core.downloader import extract_info_resilient
from src.core.processor import FFmpegProcessor

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
    "rembgFamily": next(iter(REMBG_MODEL_FAMILIES), "General"), "rembgModel": "",
    "rembgSmooth": 0, "rembgExpand": 0, "upscaleEnabled": False,
    "upscaleEngine": "realesrgan-ncnn-vulkan", "upscaleModel": "Real-ESRGAN x4plus",
    "upscaleScale": "2", "upscaleDenoise": "0", "upscaleTile": "0", "upscaleTta": False,
    "videoTitle": "video_xomacito", "videoWidth": "1920", "videoHeight": "1080",
    "videoFps": "30", "videoFrameDuration": "3", "videoFitMode": "Mantener Tamaño Original",
}


class ImageController(QObject):
    stateChanged = Signal()
    optionsChanged = Signal()
    selectedChanged = Signal()
    progressReported = Signal(float, str)
    notificationRequested = Signal(str, str, str)

    ROLES = ["itemId", "path", "name", "page", "pages", "title", "status", "detail", "output", "preview"]

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
        self._state = {
            "url": "", "outputPath": settings.get("image_output_path", str(Path.home() / "Downloads")),
            "format": "PNG", "conflictPolicy": "Renombrar", "createSubfolder": False,
            "subfolderName": "imagenes_xomacito", "processOnlyNew": False,
            "status": "Importa imágenes, documentos o pega un enlace.", "progress": 0.0,
            "busy": False, "selectedIndex": -1, "previewSource": "", "resultPreviewSource": "",
            "lastOutput": "", "itemCount": 0,
        }
        self._options = dict(IMAGE_OPTIONS)
        saved = settings.get("image_settings", {})
        if isinstance(saved, dict):
            self._options.update({key: value for key, value in saved.items() if key in self._options})
            if saved.get("format"): self._state["format"] = saved["format"]
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
        return ["No Convertir", "PNG", "JPG", "WEBP", "AVIF", "PDF", "TIFF", "ICO", "BMP", ".mp4 (H.264)", ".mov (ProRes)", ".webm (VP9)", ".gif (Animado)"]

    @Property("QStringList", constant=True)
    def rembgFamilies(self): return list(REMBG_MODEL_FAMILIES)

    @Slot(str, result="QStringList")
    def rembgModels(self, family): return list(REMBG_MODEL_FAMILIES.get(family, {}))

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
        paths, _ = QFileDialog.getOpenFileNames(None, "Importar recursos", "", "Imágenes y documentos (*.png *.jpg *.jpeg *.webp *.avif *.bmp *.tif *.tiff *.ico *.gif *.svg *.eps *.ai *.pdf *.ps *.cr2 *.dng *.arw *.nef *.orf *.rw2 *.sr2 *.raf *.cr3 *.pef);;Todos (*.*)")
        self.addPaths(paths)

    @Slot()
    def importFolder(self):
        folder = QFileDialog.getExistingDirectory(None, "Importar carpeta")
        if not folder: return
        valid = {".png", ".jpg", ".jpeg", ".webp", ".avif", ".bmp", ".tif", ".tiff", ".ico", ".gif", ".svg", ".eps", ".ai", ".pdf", ".ps"} | {ext.lower() for ext in IMAGE_RAW_FORMATS}
        self.addPaths([str(path) for path in Path(folder).rglob("*") if path.is_file() and path.suffix.lower() in valid])

    @Slot("QStringList")
    def addPaths(self, paths):
        additions = []
        for value in paths:
            path = QUrl(str(value)).toLocalFile() if str(value).startswith("file:") else str(value)
            if not Path(path).is_file(): continue
            ext = Path(path).suffix.lower()
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
                    "status": "PENDING", "detail": "Listo", "output": "", "preview": "",
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
        self.pool.submit(self._url_image_worker, url, on_result=lambda path: self._url_image_done(path), on_error=lambda m, d: self._failed(m, d))

    def _url_image_worker(self, url):
        info = extract_info_resilient(url, {"noplaylist": True, "quiet": True}, download=False)
        image_url = (info or {}).get("thumbnail")
        if not image_url: raise RuntimeError("El enlace no contiene una imagen accesible.")
        response = requests.get(image_url, timeout=40); response.raise_for_status()
        suffix = Path(urlparse(image_url).path).suffix.lower()
        if suffix not in {".png", ".jpg", ".jpeg", ".webp", ".avif"}: suffix = ".jpg"
        target = Path(tempfile.gettempdir()) / f"xomacito_url_{int(os.times().elapsed * 1000)}{suffix}"
        target.write_bytes(response.content)
        return str(target)

    def _url_image_done(self, path):
        self._set_state(busy=False, progress=1.0, status="Imagen del enlace importada.", url="")
        self.addPaths([path])

    @Slot(int)
    def select(self, index):
        if not 0 <= index < self.items.rowCount(): return
        self._set_state(selectedIndex=index, previewSource="", resultPreviewSource="")
        self.selectedChanged.emit()
        item = self.items.item(index)
        self.pool.submit(
            self._thumbnail_worker, item,
            on_result=lambda path, row=index: self._thumbnail_done(row, path),
            on_error=lambda message, detail: self._failed_preview(message, detail),
        )

    def _thumbnail_worker(self, item):
        self._ensure_engines()
        thumb = self.processor.generate_thumbnail(
            item["path"], size=(900, 700), page_number=item["page"],
            dpi=int(self.settings.get("preview_vector_dpi", 96)),
        )
        if thumb is None: raise RuntimeError("No se pudo generar la previsualización.")
        target = Path(tempfile.gettempdir()) / f"xomacito_preview_{item['itemId']}.png"
        thumb.save(target, "PNG")
        return str(target)

    def _thumbnail_done(self, row, path):
        if row < self.items.rowCount(): self.items.update_item(row, {"preview": QUrl.fromLocalFile(path).toString()})
        if self._state["selectedIndex"] == row:
            self._set_state(previewSource=QUrl.fromLocalFile(path).toString())
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
            "video_custom_title": self._options["videoTitle"], "video_custom_width": self._options["videoWidth"],
            "video_custom_height": self._options["videoHeight"], "video_fps": self._options["videoFps"],
            "video_frame_duration": self._options["videoFrameDuration"], "video_fit_mode": self._options["videoFitMode"],
        }
        return options

    def _real_rembg_model(self):
        family = self._options["rembgFamily"]; label = self._options["rembgModel"]
        data = REMBG_MODEL_FAMILIES.get(family, {}).get(label, {})
        return data.get("file", label or "u2netp.onnx")

    @Slot()
    def start(self):
        if self._state["busy"] or not self.items.rowCount(): return
        output = Path(self._state["outputPath"])
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
        if str(options["format"]).startswith("."):
            return self._video_worker(items, output_dir, options)
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
            self.pool.submit(self._thumbnail_worker, {"path": first, "page": 1, "itemId": "result"}, on_result=lambda path: self._set_state(resultPreviewSource=QUrl.fromLocalFile(path).toString()))
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
        folder = self.project_root / "bin" / "models" / "rembg"; folder.mkdir(parents=True, exist_ok=True)
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(folder)))

    @Slot()
    def browseUpscaleFolder(self):
        folder = self.project_root / "bin" / "models" / "upscaling"; folder.mkdir(parents=True, exist_ok=True)
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(folder)))

    @Slot(float, str)
    def _apply_progress(self, value, message): self._set_state(progress=value, status=message)

    def _failed(self, message, detail=""):
        cancelled = self.cancel_event.is_set() or "cancel" in message.lower()
        self._set_state(busy=False, progress=0.0, status="Proceso cancelado." if cancelled else message)
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
