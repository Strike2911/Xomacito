from __future__ import annotations

import json
import os
import shutil
from pathlib import Path
from typing import Any

from PySide6.QtCore import QObject, Property, QUrl, Signal, Slot
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import QFileDialog, QInputDialog

from src.core.console_handler import ConsoleHandler
from src.core.downloader import apply_yt_patch, extract_info_resilient
from src.core.setup import (
    check_and_download_rembg_models,
    check_and_download_upscaling_tools,
    check_environment_status,
    check_ghostscript_status,
    check_inkscape_status,
    download_and_install_deno,
    download_and_install_ffmpeg,
    download_and_install_poppler,
    download_and_install_ytdlp,
    install_custom_upscayl_model,
)

from .list_model import ObjectListModel
from .settings_store import SettingsStore
from .theme import ThemeController
from .workers import TaskPool


class SettingsController(QObject):
    stateChanged = Signal()
    consoleTextChanged = Signal()
    notificationRequested = Signal(str, str, str)
    progressReported = Signal(float, str)
    consoleChunk = Signal(str)
    consoleFinished = Signal()

    DEPENDENCY_ROLES = ["key", "name", "installed", "localVersion", "latestVersion", "detail", "action"]
    MODEL_ROLES = ["key", "name", "family", "path", "installed", "size"]

    def __init__(self, project_root: str | Path, settings: SettingsStore, theme: ThemeController, pool: TaskPool, parent=None):
        super().__init__(parent)
        self.project_root = Path(project_root)
        self.settings = settings
        self.theme = theme
        self.pool = pool
        self.dependencies = ObjectListModel(self.DEPENDENCY_ROLES, self)
        self.models = ObjectListModel(self.MODEL_ROLES, self)
        self._environment: dict[str, Any] = {}
        self._console_text = "Xomacito Console\nEscribe dp help para ver los comandos disponibles.\n"
        self._state = {
            "section": "General",
            "busy": False,
            "progress": 0.0,
            "status": "Configuración lista.",
            "appearance": settings.get("appearance_mode", "Dark"),
            "theme": theme.themeName,
            "animationsEnabled": settings.get("animations_enabled", True),
            "compactMode": settings.get("compact_mode", False),
            "cleanTitles": settings.get("clean_titles", True),
            "cookiesMode": settings.get("cookies_mode", "No usar"),
            "cookiesPath": settings.get("cookies_path", ""),
            "selectedBrowser": settings.get("selected_browser", "chrome"),
            "browserProfile": settings.get("browser_profile", ""),
            "cookieTestUrl": "https://www.youtube.com/",
            "vectorDpi": settings.get("vector_dpi", 300),
            "previewVectorDpi": settings.get("preview_vector_dpi", 96),
            "vectorForceBackground": settings.get("vector_force_background", False),
            "keepAiModels": settings.get("keep_ai_models_in_memory", False),
            "inkscapeEnabled": settings.get("inkscape_enabled", True),
            "inkscapePath": settings.get("inkscape_path", ""),
            "consoleWrap": settings.get("console_wrap", True),
            "consoleBusy": False,
        }
        self.console = ConsoleHandler(str(self.project_root / "bin"), str(self.project_root / "bin" / "ffmpeg"))
        self.console.connect_callbacks(
            lambda text, _tag="normal": self.consoleChunk.emit(str(text)),
            lambda: self.consoleFinished.emit(),
        )
        self.consoleChunk.connect(self._append_console)
        self.consoleFinished.connect(lambda: self._set_state(consoleBusy=False))
        self.progressReported.connect(self._apply_progress)
        self._refresh_local_dependencies()
        self.refreshModels()

    @Property("QVariantMap", notify=stateChanged)
    def state(self):
        return self._state

    @Property(QObject, constant=True)
    def dependencyModel(self):
        return self.dependencies

    @Property(QObject, constant=True)
    def modelModel(self):
        return self.models

    @Property(str, notify=consoleTextChanged)
    def consoleText(self):
        return self._console_text

    def _set_state(self, **values):
        changed = False
        for key, value in values.items():
            if self._state.get(key) != value:
                self._state[key] = value
                changed = True
        if changed:
            self.stateChanged.emit()

    @Slot(str, "QVariant")
    def setValue(self, key: str, value):
        if key not in self._state:
            return
        if key == "appearance":
            self.theme.setAppearance(str(value))
            self._set_state(appearance=self.theme.appearance)
            return
        if key == "theme":
            self.theme.setTheme(str(value))
            self._set_state(theme=self.theme.themeName)
            return
        self._set_state(**{key: value})
        mapping = {
            "animationsEnabled": "animations_enabled",
            "compactMode": "compact_mode",
            "cleanTitles": "clean_titles",
            "cookiesMode": "cookies_mode",
            "cookiesPath": "cookies_path",
            "selectedBrowser": "selected_browser",
            "browserProfile": "browser_profile",
            "vectorDpi": "vector_dpi",
            "previewVectorDpi": "preview_vector_dpi",
            "vectorForceBackground": "vector_force_background",
            "keepAiModels": "keep_ai_models_in_memory",
            "inkscapeEnabled": "inkscape_enabled",
            "inkscapePath": "inkscape_path",
            "consoleWrap": "console_wrap",
        }
        if key in mapping:
            self.settings.set(mapping[key], value)

    @Slot()
    def chooseCookiesFile(self):
        path, _ = QFileDialog.getOpenFileName(None, "Archivo cookies.txt", "", "Netscape cookies (*.txt);;Todos (*.*)")
        if path:
            self.setValue("cookiesPath", path)
            self.setValue("cookiesMode", "Archivo Manual...")

    @Slot()
    def chooseInkscape(self):
        path, _ = QFileDialog.getOpenFileName(None, "Ejecutable de Inkscape", "", "Inkscape (inkscape.exe);;Ejecutables (*.exe);;Todos (*.*)")
        if path:
            self.setValue("inkscapePath", path)

    def _cookie_options(self):
        mode = str(self._state["cookiesMode"])
        if mode == "Archivo Manual..." and self._state["cookiesPath"]:
            return {"cookiefile": self._state["cookiesPath"]}
        if mode != "No usar":
            browser = str(self._state["selectedBrowser"] or "chrome")
            profile = str(self._state["browserProfile"] or "")
            return {"cookiesfrombrowser": ((browser, profile) if profile else (browser,))}
        return {}

    @Slot()
    def testCookies(self):
        if self._state["busy"]:
            return
        url = str(self._state["cookieTestUrl"] or "https://www.youtube.com/")
        self._set_state(busy=True, progress=-1.0, status="Probando acceso con cookies…")
        self.pool.submit(self._test_cookies_worker, url, on_result=self._cookies_ok, on_error=self._cookies_error)

    def _test_cookies_worker(self, url):
        options = {"quiet": True, "no_warnings": True, "skip_download": True, "noplaylist": True}
        cookie_options = self._cookie_options()
        options.update(cookie_options)
        if cookie_options:
            options = apply_yt_patch(options)
        info = extract_info_resilient(url, options, download=False)
        if not info:
            raise RuntimeError("El sitio no devolvió información.")
        return str(info.get("title") or info.get("id") or "Acceso correcto")

    def _cookies_ok(self, title):
        self._set_state(busy=False, progress=1.0, status=f"Cookies válidas: {title}")
        self.notificationRequested.emit("success", "Cookies verificadas", str(title))

    def _cookies_error(self, message, detail):
        print(detail)
        self._set_state(busy=False, progress=0.0, status=f"No se pudieron usar las cookies: {message}")
        self.notificationRequested.emit("error", "Prueba de cookies", str(message))

    def _refresh_local_dependencies(self):
        bin_dir = self.project_root / "bin"
        rows = [
            ("ffmpeg", "FFmpeg", bin_dir / "ffmpeg" / "ffmpeg.exe", bin_dir / "ffmpeg" / "ffmpeg_version.txt"),
            ("deno", "Deno", bin_dir / "deno" / "deno.exe", bin_dir / "deno" / "deno_version.txt"),
            ("poppler", "Poppler", bin_dir / "poppler" / "pdfinfo.exe", bin_dir / "poppler" / "poppler_version.txt"),
            ("ytdlp", "yt-dlp", bin_dir / "ytdlp" / "yt-dlp.zip", bin_dir / "ytdlp" / "ytdlp_version.txt"),
            ("inkscape", "Inkscape", bin_dir / "inkscape" / "inkscape.exe", bin_dir / "inkscape" / "inkscape_version.txt"),
            ("ghostscript", "Ghostscript", bin_dir / "ghostscript" / "gswin64c.exe", None),
        ]
        result = []
        for key, name, executable, version_path in rows:
            version = ""
            if version_path and version_path.is_file():
                try:
                    version = version_path.read_text(encoding="utf-8-sig").strip()
                except OSError:
                    pass
            installed = executable.is_file()
            result.append({
                "key": key, "name": name, "installed": installed,
                "localVersion": version or ("Instalado" if installed else "—"),
                "latestVersion": "", "detail": "Listo" if installed else "No instalado",
                "action": "Actualizar" if installed else "Instalar",
            })
        self.dependencies.replace(result)

    @Slot(bool)
    def refreshDependencies(self, remote=False):
        if self._state["busy"]:
            return
        self._set_state(busy=True, progress=-1.0, status="Revisando componentes…")
        self.pool.submit(
            lambda: check_environment_status(self._setup_progress, check_updates=bool(remote)),
            on_result=self._environment_done,
            on_error=lambda m, d: self._dependency_error(m, d),
        )

    def _environment_done(self, result):
        self._environment = result if isinstance(result, dict) else {}
        self._refresh_local_dependencies()
        latest_map = {
            "ffmpeg": self._environment.get("latest_version"),
            "deno": self._environment.get("latest_deno_version"),
            "poppler": self._environment.get("latest_poppler_version"),
            "ytdlp": self._environment.get("latest_ytdlp_version"),
        }
        for index, item in enumerate(self.dependencies.items()):
            latest = latest_map.get(item["key"]) or ""
            if latest:
                self.dependencies.update_item(index, {"latestVersion": latest, "detail": "Versión más reciente consultada"})
        self._set_state(busy=False, progress=1.0, status="Componentes revisados.")

    @Slot(str)
    def installDependency(self, key):
        if self._state["busy"]:
            return
        self._set_state(busy=True, progress=0.0, status=f"Preparando {key}…")
        self.pool.submit(self._install_dependency_worker, key, on_result=lambda ok: self._dependency_installed(key, ok), on_error=self._dependency_error)

    def _install_dependency_worker(self, key):
        status = check_environment_status(self._setup_progress, check_updates=True)
        installers = {
            "ffmpeg": (download_and_install_ffmpeg, status.get("latest_version"), status.get("download_url")),
            "deno": (download_and_install_deno, status.get("latest_deno_version"), status.get("deno_download_url")),
            "poppler": (download_and_install_poppler, status.get("latest_poppler_version"), status.get("poppler_download_url")),
            "ytdlp": (download_and_install_ytdlp, status.get("latest_ytdlp_version"), status.get("ytdlp_download_url")),
        }
        if key not in installers:
            raise RuntimeError("Este componente se instala manualmente desde su carpeta.")
        function, tag, url = installers[key]
        if not tag or not url:
            raise RuntimeError("No se encontró una descarga compatible.")
        return bool(function(tag, url, self._setup_progress))

    def _dependency_installed(self, key, ok):
        self._refresh_local_dependencies()
        self._set_state(busy=False, progress=1.0 if ok else 0.0, status=f"{key}: {'listo' if ok else 'no se pudo instalar'}.")
        self.notificationRequested.emit("success" if ok else "error", "Componentes", self._state["status"])

    def _dependency_error(self, message, detail):
        print(detail)
        self._set_state(busy=False, progress=0.0, status=str(message))
        self.notificationRequested.emit("error", "Componentes", str(message))

    def _setup_progress(self, message, progress, *_sizes):
        value = float(progress) / 100.0 if float(progress) >= 0 else -1.0
        self.progressReported.emit(value, str(message))

    @Slot(str)
    def downloadModels(self, family):
        if self._state["busy"]:
            return
        self._set_state(busy=True, progress=0.0, status=f"Preparando modelos {family}…")
        if family == "rembg":
            worker = lambda: check_and_download_rembg_models(self._setup_progress)
        else:
            worker = lambda: check_and_download_upscaling_tools(self._setup_progress, family if family != "all" else None)
        self.pool.submit(worker, on_result=lambda ok: self._models_done(bool(ok)), on_error=self._dependency_error)

    @Slot()
    def importUpscaylModel(self):
        path, _ = QFileDialog.getOpenFileName(None, "Modelo NCNN de Upscayl", "", "Modelos NCNN (*.bin *.param)")
        if not path:
            return
        nickname, accepted = QInputDialog.getText(None, "Nombre del modelo", "Nombre visible:", text=Path(path).stem)
        if not accepted:
            return
        custom = dict(self.settings.get("upscayl_custom_models", {}))
        try:
            _real_name, visible_name = install_custom_upscayl_model(
                path, nickname, custom, lambda values: self.settings.set("upscayl_custom_models", values)
            )
            self.refreshModels()
            self.notificationRequested.emit("success", "Modelo instalado", visible_name)
        except Exception as error:
            self.notificationRequested.emit("error", "Modelo no válido", str(error))

    @Slot()
    def refreshModels(self):
        roots = [
            ("rembg", self.project_root / "bin" / "models" / "rembg", {".onnx"}),
            ("upscaling", self.project_root / "bin" / "models" / "upscaling", {".param", ".bin"}),
        ]
        rows = []
        for family, root, extensions in roots:
            if not root.exists():
                continue
            for path in root.rglob("*"):
                if path.is_file() and path.suffix.lower() in extensions:
                    rows.append({
                        "key": str(path), "name": path.name, "family": family,
                        "path": str(path), "installed": True,
                        "size": f"{path.stat().st_size / 1024 / 1024:.1f} MB",
                    })
        self.models.replace(rows)

    def _models_done(self, ok):
        self.refreshModels()
        self._set_state(busy=False, progress=1.0 if ok else 0.0, status="Modelos listos." if ok else "No se pudieron preparar los modelos.")

    @Slot(str)
    def deleteModel(self, model_path):
        path = Path(model_path).resolve()
        allowed = (self.project_root / "bin" / "models").resolve()
        try:
            path.relative_to(allowed)
        except ValueError:
            return
        if path.is_file():
            try:
                path.unlink()
                if path.suffix.lower() in {".bin", ".param"}:
                    partner = path.with_suffix(".param" if path.suffix.lower() == ".bin" else ".bin")
                    partner.unlink(missing_ok=True)
                    custom = dict(self.settings.get("upscayl_custom_models", {}))
                    if path.stem in custom:
                        custom.pop(path.stem, None)
                        self.settings.set("upscayl_custom_models", custom)
                self.refreshModels()
                self.notificationRequested.emit("success", "Modelo eliminado", path.name)
            except OSError as error:
                self.notificationRequested.emit("error", "No se pudo eliminar", str(error))

    @Slot(str)
    def openFolder(self, key):
        folders = {
            "settings": self.settings.directory,
            "themes": self.settings.themes_dir,
            "models": self.project_root / "bin" / "models",
            "bin": self.project_root / "bin",
            "project": self.project_root,
        }
        folder = folders.get(key, self.project_root)
        folder.mkdir(parents=True, exist_ok=True)
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(folder)))

    @Slot()
    def importTheme(self):
        path, _ = QFileDialog.getOpenFileName(None, "Importar tema de Xomacito", "", "Tema JSON (*.json)")
        if not path:
            return
        try:
            raw = json.loads(Path(path).read_text(encoding="utf-8-sig"))
            if not isinstance(raw, dict):
                raise ValueError("El tema no contiene un objeto JSON.")
            self.settings.themes_dir.mkdir(parents=True, exist_ok=True)
            destination = self.settings.themes_dir / Path(path).name
            shutil.copy2(path, destination)
            self.theme.availableThemesChanged.emit()
            self.theme.setTheme(destination.stem)
            self._set_state(theme=destination.stem)
        except Exception as error:
            self.notificationRequested.emit("error", "Tema no válido", str(error))

    @Slot(str)
    def deleteTheme(self, name):
        path = self.settings.themes_dir / f"{Path(name).stem}.json"
        if path.is_file():
            path.unlink()
            self.theme.availableThemesChanged.emit()
            self.theme.setTheme("midnight_ocean")
            self._set_state(theme="midnight_ocean")

    @Slot(str)
    def executeConsole(self, command):
        if not command.strip() or self._state["consoleBusy"]:
            return
        self._set_state(consoleBusy=True)
        self.console.execute_command(command)

    @Slot()
    def cancelConsole(self):
        self.console.cancel_process()

    @Slot()
    def clearConsole(self):
        self._console_text = "Xomacito Console\n"
        self.consoleTextChanged.emit()

    @Slot(str)
    def openUrl(self, url):
        QDesktopServices.openUrl(QUrl(url))

    @Slot(str)
    def _append_console(self, text):
        self._console_text += text
        if len(self._console_text) > 250_000:
            self._console_text = self._console_text[-200_000:]
        self.consoleTextChanged.emit()

    @Slot(float, str)
    def _apply_progress(self, value, message):
        self._set_state(progress=value, status=message)

    def shutdown(self):
        self.console.cancel_process()
