from __future__ import annotations

import traceback
from collections.abc import Callable
from typing import Any

from PySide6.QtCore import QObject, QRunnable, QThreadPool, Signal, Slot


class WorkerSignals(QObject):
    result = Signal(object)
    error = Signal(str, str)
    finished = Signal()


class Worker(QRunnable):
    """Ejecuta trabajo bloqueante sin tocar objetos gráficos desde el hilo."""

    def __init__(self, function: Callable[..., Any], *args, **kwargs):
        super().__init__()
        self.function = function
        self.args = args
        self.kwargs = kwargs
        self.signals = WorkerSignals()
        self.setAutoDelete(True)

    @Slot()
    def run(self):
        try:
            result = self.function(*self.args, **self.kwargs)
        except Exception as exc:  # el traceback completo queda disponible en consola
            self.signals.error.emit(str(exc), traceback.format_exc())
        else:
            self.signals.result.emit(result)
        finally:
            self.signals.finished.emit()


class TaskPool(QObject):
    """Fachada compartida para evitar crear un hilo por cada interacción."""

    def __init__(self, parent=None, max_threads: int | None = None):
        super().__init__(parent)
        self.pool = QThreadPool.globalInstance()
        if max_threads:
            self.pool.setMaxThreadCount(max_threads)
        self._workers: set[Worker] = set()

    def submit(
        self,
        function: Callable[..., Any],
        *args,
        on_result: Callable[[Any], None] | None = None,
        on_error: Callable[[str, str], None] | None = None,
        on_finished: Callable[[], None] | None = None,
        **kwargs,
    ) -> Worker:
        worker = Worker(function, *args, **kwargs)
        self._workers.add(worker)
        if on_result:
            worker.signals.result.connect(on_result)
        if on_error:
            worker.signals.error.connect(on_error)
        if on_finished:
            worker.signals.finished.connect(on_finished)

        def release():
            self._workers.discard(worker)

        worker.signals.finished.connect(release)
        self.pool.start(worker)
        return worker

    def wait_for_done(self, timeout_ms: int = 5000) -> bool:
        return self.pool.waitForDone(timeout_ms)
