from __future__ import annotations

import threading
import uuid

from PySide6.QtCore import QObject, Signal, Slot


class DialogBroker(QObject):
    """Puente no bloqueante para QML y bloqueante sólo para el worker solicitante."""

    requested = Signal(str, str, str, str, "QVariantList", str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._lock = threading.Lock()
        self._pending: dict[str, tuple[threading.Event, dict]] = {}

    def ask(
        self,
        kind: str,
        title: str,
        message: str,
        options: list[str] | None = None,
        default: str = "",
        timeout: float | None = None,
    ) -> str:
        request_id = uuid.uuid4().hex
        event = threading.Event()
        response: dict[str, str] = {"value": default}
        with self._lock:
            self._pending[request_id] = (event, response)
        self.requested.emit(request_id, kind, title, message, options or [], default)
        event.wait(timeout)
        with self._lock:
            self._pending.pop(request_id, None)
        return response["value"]

    @Slot(str, str)
    def respond(self, request_id: str, value: str):
        with self._lock:
            pending = self._pending.get(request_id)
        if not pending:
            return
        event, response = pending
        response["value"] = value
        event.set()

    def close_all(self):
        with self._lock:
            pending = list(self._pending.values())
        for event, _response in pending:
            event.set()
