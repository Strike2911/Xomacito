"""Local, acknowledged requests to Xomacito Link (no network listener)."""
from __future__ import annotations

import json
import os
import re
import time
from pathlib import Path
from uuid import uuid4

from PySide6.QtCore import QObject, Property, QTimer, Signal, Slot

from .media_library_controller import SUPPORTED_MEDIA


class PremiereController(QObject):
    stateChanged = Signal()
    notificationRequested = Signal(str, str, str)

    def __init__(self, library, parent=None):
        super().__init__(parent)
        self.library = library
        self._state = {"connected": False, "project": "", "status": "Abre Xomacito Link en Premiere y vincula esta biblioteca.", "pending": 0}
        self._pending = {}
        self._pending_paths = {}
        self.timer = QTimer(self)
        self.timer.setInterval(1500)
        self.timer.timeout.connect(self.poll)
        self.timer.start()

    @Property("QVariantMap", notify=stateChanged)
    def state(self): return self._state

    def _set(self, **values):
        if any(self._state.get(key) != value for key, value in values.items()):
            self._state.update(values)
            self.stateChanged.emit()

    def poll(self):
        folder = self.library.root / ".xomacito-link"
        try:
            heartbeat = json.loads((folder / "heartbeat.json").read_text(encoding="utf-8"))
            live = 0 <= time.time() - float(heartbeat["time"]) < 12
            project = str(heartbeat.get("project", "")) if live else ""
            self._set(connected=live and bool(project), project=project,
                      projectId=str(heartbeat.get("projectId", "")) if live else "",
                      autoImport=live and bool(project) and heartbeat.get("autoImport") is True,
                      protocol=heartbeat.get("protocol", 1) if live else 1)
        except (OSError, ValueError, KeyError, TypeError):
            self._set(connected=False, project="", projectId="", autoImport=False, protocol=1)
        self._receive_selection(folder)
        for request_id, (request_folder, started) in list(self._pending.items()):
            response_file = request_folder / f"{request_id}.result.json"
            try:
                response = json.loads(response_file.read_text(encoding="utf-8"))
                if not isinstance(response, dict) or response.get("id") != request_id:
                    raise ValueError("Respuesta incompleta o ajena a esta solicitud")
            except (OSError, ValueError):
                if time.time() - started < 125:
                    continue
                response = {"ok": False, "message": "Premiere no confirmó el envío. Revisa el panel Xomacito Link antes de volver a enviarlo."}
            self._pending.pop(request_id, None)
            self._pending_paths.pop(request_id, None)
            message = str(response.get("message") or "Respuesta recibida de Premiere.")
            self._set(status=message, pending=len(self._pending))
            self.notificationRequested.emit("success" if response.get("ok") else "error", "Premiere", message)
            for suffix in (".request.json", ".result.json", ".claimed.json"):
                try:
                    (request_folder / f"{request_id}{suffix}").unlink(missing_ok=True)
                except OSError:
                    pass

    @Slot(str, bool)
    def send(self, path, timeline=False):
        self.sendMany([path], timeline)

    @Slot(str)
    def completed(self, path):
        self.poll()
        if self._state.get("autoImport"):
            self.sendMany([path], False, automatic=True)

    @Slot("QVariantList", bool)
    def sendMany(self, paths, timeline=False, automatic=False):
        targets = list(dict.fromkeys(str(Path(path).resolve()) for path in paths))
        if not targets or len(targets) > 500 or any(not Path(path).is_file() or Path(path).suffix.lower() not in SUPPORTED_MEDIA for path in targets):
            if automatic:
                return
            self.notificationRequested.emit("warning", "Archivo no disponible", "Selecciona un archivo multimedia terminado antes de enviarlo.")
            return
        if timeline and len(targets) != 1:
            self.notificationRequested.emit("warning", "Selecciona un archivo", "La inserción en V1/A1 admite un archivo por envío.")
            return
        self.poll()
        if not self._state["connected"]:
            self.notificationRequested.emit("warning", "Conecta Premiere", "Abre Xomacito Link en Premiere y elige la misma carpeta de Biblioteca. Después vuelve a enviar el archivo.")
            return
        if len(self._pending) >= 50:
            self.notificationRequested.emit("warning", "Premiere ocupado", "Espera a que Premiere procese los envíos pendientes.")
            return
        # A quick-download completion and its explicit send can arrive together.
        pending_paths = {path for group in self._pending_paths.values() for path in group}
        if not timeline:
            targets = [path for path in targets if (path, self._state.get("projectId", "")) not in pending_paths]
            if not targets:
                return
        modern = self._state.get("protocol", 1) == 2
        if not modern and len(targets) > 1:
            for path in targets:
                self.send(path, False)
            return
        request_id = uuid4().hex
        folder = self.library.root / ".xomacito-link"
        now = time.time()
        try:
            folder.mkdir(exist_ok=True)
            payload = {"schema": 2 if modern else 1, "id": request_id, "path": targets[0],
                       "action": "timeline" if timeline else "import", "expires": now + 120,
                       "project": self._state["project"], "projectId": self._state.get("projectId", ""),
                       "automatic": automatic}
            if modern:
                payload["paths"] = targets
            temporary = folder / f"{request_id}.tmp"
            temporary.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
            os.replace(temporary, folder / f"{request_id}.request.json")
        except OSError as exc:
            self.notificationRequested.emit("error", "No se pudo enviar a Premiere", str(exc))
            return
        self._pending[request_id] = (folder, now)
        self._pending_paths[request_id] = [(path, self._state.get("projectId", "")) for path in targets]
        self._set(pending=len(self._pending), status="Enviado al panel; esperando confirmación de Premiere…")

    def _receive_selection(self, folder):
        for source in list(folder.glob("*.to-app.json"))[:10]:
            request_id = source.name.removesuffix(".to-app.json")
            if not re.fullmatch(r"[a-f0-9]{32}", request_id):
                continue
            try:
                data = json.loads(source.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                continue  # UXP may still be writing the message.
            try:
                if not isinstance(data, dict) or data.get("schema") != 1 or data.get("id") != request_id:
                    raise ValueError("Solicitud de Premiere inválida.")
                paths = data.get("paths")
                if not isinstance(paths, list) or not paths or len(paths) > 500 or float(data.get("expires", 0)) < time.time():
                    raise ValueError("Selección vacía, demasiado grande o caducada.")
                if any(not isinstance(path, str) or not Path(path).is_absolute() for path in paths):
                    raise ValueError("La selección contiene rutas inválidas.")
                valid = list(dict.fromkeys(path for path in paths if Path(path).is_file() and Path(path).suffix.lower() in SUPPORTED_MEDIA))
                if not valid:
                    raise ValueError("Los medios seleccionados no están disponibles en disco.")
                self.library.linkPaths(valid)
                message = f"{len(valid)} de {len(paths)} medios vinculados en la biblioteca de Xomacito."
                result = {"id": request_id, "ok": True, "message": message}
            except (ValueError, TypeError, OSError) as exc:
                result = {"id": request_id, "ok": False, "message": str(exc)}
            try:
                temporary = folder / f"{request_id}.app-tmp"
                temporary.write_text(json.dumps(result, ensure_ascii=False), encoding="utf-8")
                os.replace(temporary, folder / f"{request_id}.app-result.json")
                source.unlink(missing_ok=True)
                self.notificationRequested.emit("success" if result["ok"] else "error", "Premiere", result["message"])
            except OSError:
                pass

    def shutdown(self):
        self.timer.stop()
