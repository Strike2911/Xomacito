"""Serial, cancellable preflight before the Premiere file bridge."""
from collections import deque
from pathlib import Path
import threading

from PySide6.QtCore import QObject, Signal

from src.core.exceptions import UserCancelledError
from src.core.processor import FFmpegProcessor
from src.core.premiere_media import compatibility_issue, conversion_plan, prepare_for_premiere
from .media_library_controller import IMAGE_MEDIA


class PremierePreparation(QObject):
    ready = Signal(object, object)
    progress = Signal(float, str)
    notice = Signal(str, str, str)

    def __init__(self, library, dialogs, parent=None):
        super().__init__(parent)
        self.library, self.dialogs = library, dialogs
        self.queue = deque()
        self.active = None
        self.cancel_event = threading.Event()
        self.closed = False
        self.processor_factory = FFmpegProcessor

    def enqueue(self, paths, context):
        key = (tuple(paths), context.get("timeline"), context.get("projectId"),
               context.get("prepareOnly", False), context.get("automatic", False))
        if any(job[0] == key for job in ([self.active] if self.active else []) + list(self.queue)):
            return
        if len(self.queue) >= 50 or self.closed:
            self.notice.emit("warning", "Premiere ocupado", "Espera a que terminen los envíos pendientes.")
            return
        self.queue.append((key, paths, context))
        self._next()

    def _next(self):
        if self.active or not self.queue or self.closed:
            return
        self.active = self.queue.popleft()
        self.cancel_event.clear()
        self.progress.emit(0, "Comprobando códecs antes de enviar a Premiere…")
        _, paths, context = self.active
        self.library.pool.submit(self._worker, paths, context,
                                 on_result=self._done, on_error=self._error)

    def _worker(self, paths, context):
        # Own processor: cancellation must not stop an unrelated download.
        processor = self.processor_factory()
        checked, needs_copy = [], []
        for path in paths:
            if self.cancel_event.is_set():
                raise UserCancelledError("Preparación cancelada.")
            if Path(path).suffix.lower() in IMAGE_MEDIA:
                checked.append((path, ""))
                continue
            info = processor.get_local_media_info(path)
            if not info or not info.get("streams"):
                raise ValueError(f"No se pudo verificar el archivo: {Path(path).name}")
            issue = compatibility_issue(info, path)
            checked.append((path, issue))
            if issue:
                plan = conversion_plan(info, path)
                needs_copy.append(f"{Path(path).name}: {issue} {plan['label']}.")
        skipped = []
        if needs_copy and not context.get("prepareOnly") and not context.get("automatic"):
            message = ("\n".join(needs_copy[:5]) + "\n\nSe creará una copia compatible conservando resolución, FPS y pistas de audio. "
                       "La conversión usa compresión de alta calidad y consume recursos; no es idéntica al original. "
                       "El archivo original se conserva. HDR/10-bit o transparencia se preparan en ProRes y ocupan más espacio.")
            if not self.dialogs or self.dialogs.ask("choice", "Preparar para Premiere", message,
                    ["Crear copia y enviar", "Cancelar"], "Cancelar", cancellation_event=self.cancel_event) != "Crear copia y enviar":
                raise UserCancelledError("Envío cancelado; el original se conserva.")
        outputs = []
        for path, issue in checked:
            if self.cancel_event.is_set():
                raise UserCancelledError("Preparación cancelada.")
            if issue and context.get("automatic"):
                skipped.append(Path(path).name)
                continue  # Autoimport never authorizes a CPU-intensive conversion.
            output = prepare_for_premiere(path, self.library.root / "Premiere", processor,
                        self.cancel_event, self._progress) if issue else path
            outputs.append(output)
        return outputs, skipped

    def _progress(self, value, message):
        # FFmpeg reports percentages, including the interval from 0 to 1%.
        self.progress.emit(max(0, min(1, float(value or 0) / 100)), message)

    def _done(self, result):
        _, _, context = self.active
        self.active = None
        self.progress.emit(1, "Preparación terminada.")
        if not self.closed and not self.cancel_event.is_set():
            outputs, skipped = result
            if skipped:
                self.notice.emit("warning", "Preparación necesaria", f"{len(skipped)} archivo(s) no se enviaron automáticamente por sus códecs. En Biblioteca usa Preparar para Premiere.")
            self.ready.emit(outputs, context)
        self._next()

    def _error(self, message, _detail):
        self.active = None
        if not self.closed:
            self.notice.emit("warning" if self.cancel_event.is_set() else "error", "Preparación para Premiere", message)
        self.progress.emit(1, message)
        self._next()

    def cancel(self):
        self.queue.clear()
        self.cancel_event.set()

    def shutdown(self):
        self.closed = True
        self.cancel()
