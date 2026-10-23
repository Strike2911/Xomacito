from copy import deepcopy
from pathlib import Path

from PySide6.QtCore import QObject, QUrl, Signal

from .download_controller import DEFAULT_OPTIONS, DownloadController
from .media_logic import safe_filename
from .presets import PREMIERE_AUDIO_PRESET
from src.core.thumbnail_export import save_premiere_thumbnail
from src.core.video_quality import video_quality_key, video_resolution


class _JobSettings(QObject):
    """A job may read preferences, but must never overwrite the user's controls."""
    changed = Signal(str, object)

    def __init__(self, source, parent=None):
        super().__init__(parent)
        self.source = source
        self.values = {"download_tags": [], "selected_download_tag": "Sin etiqueta",
                       "recode_settings": {}, "open_explorer_after_download": False}

    def get(self, key, default=None):
        return deepcopy(self.values.get(key, self.source.get(key, default)))

    def set(self, key, value):
        self.values[key] = deepcopy(value)
        self.changed.emit(key, value)


def choose_video(formats: dict, quality: str) -> str:
    """Keep the requested resolution; prefer an editor-friendly stream at that size."""
    if not formats:
        return ""
    limit = int(quality[:-1]) if quality.endswith("p") else 100000
    entries = list(formats.items())
    known = [(key, fmt) for key, fmt in entries if video_resolution(fmt)]
    entries = known or entries
    eligible = [(key, fmt) for key, fmt in entries if video_resolution(fmt) <= limit]
    if not eligible:
        smallest = min(video_resolution(fmt) for _, fmt in entries)
        eligible = [(key, fmt) for key, fmt in entries if video_resolution(fmt) == smallest]
    return max(eligible, key=lambda entry: (
        *video_quality_key(entry[1]), bool(entry[1].get("compatible")),
        float(entry[1].get("tbr") or 0),
    ))[0]


class _QuickRunner(DownloadController):
    finished = Signal(str, str)

    def _process_worker(self, options):
        self.quick_outputs = []
        result = super()._process_worker(options)
        if Path(result).is_file(): self.quick_outputs.append(result)
        self.quick_outputs = list(dict.fromkeys(path for path in self.quick_outputs if Path(path).is_file()))
        return result

    def _recode_file(self, *args, **kwargs):
        result = super()._recode_file(*args, **kwargs)
        self.quick_outputs.append(str(result))
        return result

    def _clip_without_recode(self, *args, **kwargs):
        result = super()._clip_without_recode(*args, **kwargs)
        self.quick_outputs.append(str(result))
        return result

    def _resolve_output(self, folder, name, suffix, *, ask=True):
        # A background queue must not wait for a modal collision prompt.
        return super()._resolve_output(folder, name, suffix, ask=False)

    def _apply_url_analysis(self, info):
        if self.cancellation.is_set():
            self._operation_error("Cancelado")
            return
        super()._apply_url_analysis(info)
        job = self.quick_options
        mode = "Solo Audio" if job["mode"] == "Audio" or not self._video_map else "Video+Audio"
        if self._image_post:
            self._operation_error("Este enlace contiene imágenes. Usa la pestaña Descargar para importarlas.")
            return
        if job.get("thumbnailOnly"):
            self._set_state(busy=True, status="Guardando miniatura…")
            source, folder, title = self.state['thumbnailSource'], job['outputPath'], self.state['title']
            self.pool.submit(self._thumbnail_worker, source, folder, title,
                             on_result=self._operation_success, on_error=self._operation_error)
            return
        selected = choose_video(self._video_map, job["quality"])
        if mode == "Video+Audio" and job["quality"].endswith("p"):
            actual = video_resolution(self._video_map.get(selected, {}))
            if actual < int(job["quality"][:-1]):
                available = f"{actual}p" if actual else "una resolución sin verificar"
                self._operation_error(
                    f"Pediste {job['quality']}, pero el sitio solo ofrece {available} para esta descarga. "
                    "Elige esa calidad o Mejor disponible para continuar; no se bajará automáticamente."
                )
                return
        self._set_state(mode=mode, selectedVideo=selected)
        self._options = deepcopy(DEFAULT_OPTIONS)
        self._options.update(keepOriginal=False, autoSaveThumbnail=job["thumbnail"])
        if job.get('ranges'):
            self._options.update(fragmentEnabled=True, fragmentRanges=deepcopy(job['ranges']))
        if mode == "Solo Audio":
            preset = PREMIERE_AUDIO_PRESET if job["audioFormat"] == "WAV" else "Audio - MP3 " + job["audioFormat"].split()[-1] + "kbps"
            self._set_state(preset=preset)
            self._options["applyPreset"] = True
        elif job.get('postprocess') and job.get('preset'):
            self._set_state(preset=job['preset'])
            self._options['applyPreset'] = True
        fragment_error = self._fragment_error()
        if fragment_error:
            self._operation_error(fragment_error)
            return
        if self.cancellation.is_set():
            self._operation_error("Cancelado")
        else:
            self.start()

    def _thumbnail_worker(self, source, folder, title):
        import requests
        if not source:
            raise ValueError('El sitio no ofrece una miniatura para este enlace.')
        if self.cancellation.is_set(): raise ValueError('Cancelado')
        destination = Path(folder).expanduser()
        destination.mkdir(parents=True, exist_ok=True)
        target = self._resolve_output(destination, safe_filename(title), '.jpg', ask=False)
        if source.startswith('file:'):
            data = Path(QUrl(source).toLocalFile()).read_bytes()
        else:
            response = requests.get(source, timeout=30); response.raise_for_status(); data = response.content
        if self.cancellation.is_set(): raise ValueError('Cancelado')
        save_premiere_thumbnail(data, target)
        self.quick_outputs = [str(target)]
        return str(target)

    def _operation_success(self, output):
        super()._operation_success(output)
        self.finished.emit("Completado", output)

    def _operation_error(self, message, detail=""):
        cancelled = self.cancellation.is_set() or "cancel" in message.lower()
        super()._operation_error(message, detail)
        self.finished.emit("Cancelado" if cancelled else "Error", "")


