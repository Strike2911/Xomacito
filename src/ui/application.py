from __future__ import annotations

import os
import subprocess
import sys
import ctypes
from pathlib import Path
from urllib.parse import urlsplit

from PySide6.QtCore import QObject, Property, QTimer, QUrl, Signal, Slot, Qt
from PySide6.QtGui import QDesktopServices, QIcon
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtWidgets import QApplication

from src.core.app_updater import (
    RELEASES_URL,
    check_for_app_update,
    deferred_installer_command,
    download_installer,
    release_notice_for_version,
)
from src.core.daily_icon import daily_cat_assets
from src.core.notification_sound import play_completion_sound, play_gacha_reveal_sound

from .batch_controller import BatchController
from .cat_gacha_controller import CatGachaController
from .dialog_broker import DialogBroker
from .download_controller import DownloadController
from .image_controller import ImageController
from .presets import PresetStore
from .settings_controller import SettingsController
from .settings_store import SettingsStore
from .theme import ThemeController
from .workers import TaskPool


def normalize_clipboard_url(value: object) -> str:
    """Devuelve una URL web pegable o una cadena vacía."""
    candidate = str(value or "").strip()
    if not candidate or len(candidate) > 8192 or any(char.isspace() for char in candidate):
        return ""
    try:
        parsed = urlsplit(candidate)
    except ValueError:
        return ""
    if parsed.scheme.lower() not in {"http", "https"} or not parsed.netloc:
        return ""
    return candidate


class AppController(QObject):
    pageChanged = Signal()
    catChanged = Signal()
    updateStateChanged = Signal()
    toastRequested = Signal(str, str, str)
    updatePromptRequested = Signal("QVariantMap")
    releaseNoticeRequested = Signal("QVariantMap")
    closeRequested = Signal()
    updateProgressReported = Signal(float, str)

    PAGES = ["Descargar", "Cola", "Estudio de Imagen", "Personalización", "Configuración"]

    def __init__(self, app: QApplication, project_root: str | Path, app_version: str, parent=None):
        super().__init__(parent)
        self.app = app
        self.project_root = Path(project_root)
        self.app_version = app_version
        self.settings = SettingsStore(parent=self)
        self.pool = TaskPool(self, max_threads=max(4, min(12, os.cpu_count() or 4)))
        self.dialogs = DialogBroker(self)
        self.theme = ThemeController(self.project_root, self.settings, self)
        self.presets = PresetStore(self.settings, self)
        self.download = DownloadController(self.project_root, self.settings, self.pool, self.dialogs, self.presets, app_version, self)
        self.batch = BatchController(self.project_root, self.settings, self.pool, self.presets, app_version, self)
        self.image_studio = ImageController(self.project_root, self.settings, self.pool, app_version, self)
        self.config = SettingsController(self.project_root, self.settings, self.theme, self.pool, self)
        self.cats = CatGachaController(self.project_root, self.settings, self)
        self._page = 0
        self._update_state = {
            "checking": False, "downloading": False, "progress": 0.0,
            "status": "", "latestVersion": "", "releaseNotes": "",
        }
        self._pending_update: dict = {}
        self._closing = False
        self._last_clipboard_check = ""
        self._clipboard_timer = QTimer(self)
        self._clipboard_timer.setSingleShot(True)
        self._clipboard_timer.timeout.connect(self._check_clipboard_and_paste)
        self._clipboard = self.app.clipboard()
        self._clipboard.dataChanged.connect(self._schedule_clipboard_check)
        self.app.applicationStateChanged.connect(self._on_application_state_changed)
        self.cats.stateChanged.connect(self.catChanged)
        self.updateProgressReported.connect(lambda value, status: self._set_update(progress=value, status=status))
        self._connect_routes()

    def _connect_routes(self):
        for controller in (self.download, self.batch, self.image_studio, self.config, self.cats):
            controller.notificationRequested.connect(self.toastRequested)
        self.download.successfulDownload.connect(self.cats.recordSuccessfulDownloads)
        self.batch.successfulDownload.connect(self.cats.recordSuccessfulDownloads)
        self.download.successfulDownload.connect(self._play_download_completion)
        self.batch.successfulDownload.connect(self._play_download_completion)
        self.cats.revealRequested.connect(self._play_cat_reveal)
        self.download.navigateRequested.connect(self.navigate)
        self.download.queueRequested.connect(self._send_url_to_queue)
        self.batch.imageFilesRequested.connect(self._send_files_to_image)

    @Slot(int)
    def _play_download_completion(self, _completed_items=1):
        play_completion_sound()

    @Slot("QVariantMap")
    def _play_cat_reveal(self, result):
        play_gacha_reveal_sound(int(dict(result or {}).get("rarity", 1)))

    @Slot()
    def _schedule_clipboard_check(self):
        """Agrupa cambios repetidos del portapapeles sin bloquear la interfaz."""
        self._clipboard_timer.start(140)

    def _on_application_state_changed(self, state):
        if state == Qt.ApplicationState.ApplicationActive:
            self._schedule_clipboard_check()

    @Slot()
    def _check_clipboard_and_paste(self):
        """Restaura el pegado automático de enlaces de la interfaz anterior."""
        try:
            clipboard_content = self._clipboard.text()
        except (OSError, RuntimeError):
            return

        if not clipboard_content or clipboard_content == self._last_clipboard_check:
            return

        url = normalize_clipboard_url(clipboard_content)
        if not url:
            self._last_clipboard_check = clipboard_content
            return

        target = None
        blocked = False
        if self._page == 0:
            target = self.download
            blocked = bool(self.download.state.get("busy") or self.download.state.get("localFile"))
        elif self._page == 1:
            target = self.batch
            blocked = bool(self.batch.state.get("analyzing") or self.batch.state.get("running"))
        elif self._page == 2:
            target = self.image_studio
            blocked = bool(self.image_studio.state.get("busy"))

        if target is None:
            self._last_clipboard_check = clipboard_content
            return
        if blocked:
            return

        self._last_clipboard_check = clipboard_content
        if str(target.state.get("url") or "") != url:
            target.setValue("url", url)

    @Property(int, notify=pageChanged)
    def page(self):
        return self._page

    @Property("QStringList", constant=True)
    def pages(self):
        return self.PAGES

    @Property(str, constant=True)
    def version(self):
        return self.app_version

    @Property(str, notify=catChanged)
    def catSource(self):
        return str(self.cats.state.get("equippedSource", ""))

    @Property(int, notify=catChanged)
    def catNumber(self):
        equipped = str(self.cats.state.get("equippedId", ""))
        return next((index + 1 for index, cat in enumerate(self.cats.catalog) if cat.id == equipped), 1)

    @Property(int, notify=catChanged)
    def catCount(self):
        return len(self.cats.catalog)

    @Property(str, notify=catChanged)
    def catName(self):
        return str(self.cats.state.get("equippedName", ""))

    @Property(int, notify=catChanged)
    def catRarity(self):
        return int(self.cats.state.get("equippedRarity", 1))

    @Property(str, notify=catChanged)
    def catRarityColor(self):
        return str(self.cats.state.get("equippedColor", "#A8B0BC"))

    @Property("QVariantMap", notify=updateStateChanged)
    def updateState(self):
        return self._update_state

    @Slot(int)
    def setPage(self, page):
        page = max(0, min(len(self.PAGES) - 1, int(page)))
        if page != self._page:
            self._page = page
            self.pageChanged.emit()

    @Slot(str)
    def navigate(self, name):
        aliases = {
            "download": 0,
            "batch": 1,
            "queue": 1,
            "image": 2,
            "cats": 3,
            "gatitos": 3,
            "personalizacion": 3,
            "personalización": 3,
            "settings": 4,
            "configuracion": 4,
            "configuración": 4,
        }
        index = aliases.get(str(name).lower())
        if index is None:
            try:
                index = self.PAGES.index(name)
            except ValueError:
                return
        self.setPage(index)

    @Slot(str)
    def openUrl(self, url):
        QDesktopServices.openUrl(QUrl(url))

    @Slot()
    def openReleases(self):
        self.openUrl(RELEASES_URL)

    @Slot(bool)
    def checkUpdates(self, userInitiated=False):
        if self._update_state["checking"] or self._update_state["downloading"]:
            return
        self._set_update(checking=True, status="Buscando una versión nueva…", progress=-1.0)
        self.pool.submit(
            check_for_app_update,
            self.app_version,
            on_result=lambda info: self._update_checked(info, bool(userInitiated)),
            on_error=lambda message, detail: self._update_failed(message, detail, bool(userInitiated)),
        )

    def _update_checked(self, info, user_initiated):
        info = info if isinstance(info, dict) else {}
        installer_url = str(info.get("installer_url") or "").strip()
        if info.get("update_available") and installer_url:
            self._pending_update = info
            self._set_update(
                checking=False, progress=0.0, status=f"Xomacito {info.get('latest_version')} disponible",
                latestVersion=str(info.get("latest_version") or ""),
                releaseNotes=str(info.get("release_notes") or ""),
            )
            self.updatePromptRequested.emit(info)
        else:
            error = str(info.get("error") or "")
            if info.get("update_available") and not installer_url and not error:
                error = "La nueva versión todavía no tiene un instalador compatible."
            status = error or "Ya tienes la versión más reciente."
            self._set_update(checking=False, progress=1.0, status=status)
            if user_initiated:
                self.toastRequested.emit("error" if error else "success", "Actualizaciones", status)

    def _update_failed(self, message, detail, user_initiated):
        print(detail)
        self._set_update(checking=False, progress=0.0, status=str(message))
        if user_initiated:
            self.toastRequested.emit("error", "No se pudo buscar actualizaciones", str(message))

    @Slot()
    def acceptUpdate(self):
        if not self._pending_update or self._update_state["downloading"]:
            return
        self._set_update(downloading=True, progress=0.0, status="Descargando instalador verificado…")
        self.pool.submit(
            download_installer,
            dict(self._pending_update),
            progress_callback=self._update_progress,
            on_result=self._installer_ready,
            on_error=lambda message, detail: self._update_failed_download(message, detail),
        )

    @Slot()
    def declineUpdate(self):
        self._set_update(status="Actualización pospuesta.")

    def _update_progress(self, current, total):
        value = float(current) / float(total) if total else -1.0
        self.updateProgressReported.emit(value, f"Descargando actualización… {value * 100:.0f}%")

    def _installer_ready(self, path):
        try:
            command = deferred_installer_command(path, os.getpid())
            subprocess.Popen(command, creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0)
        except Exception as error:
            self._update_failed_download(str(error), "")
            return
        self._set_update(progress=1.0, status="Instalador listo. Xomacito se cerrará para actualizar.")
        self.toastRequested.emit("success", "Actualización lista", "El instalador verificado se abrirá al cerrar Xomacito.")
        QTimer.singleShot(650, self.app.quit)

    def _update_failed_download(self, message, detail):
        print(detail)
        self._set_update(downloading=False, progress=0.0, status=str(message))
        self.toastRequested.emit("error", "No se pudo actualizar Xomacito", str(message))

    def _set_update(self, **values):
        changed = False
        for key, value in values.items():
            if self._update_state.get(key) != value:
                self._update_state[key] = value
                changed = True
        if changed:
            self.updateStateChanged.emit()

    def _send_url_to_queue(self, url):
        self.batch.setValue("url", url)
        self.setPage(1)
        self.batch.analyze()

    def _send_files_to_image(self, paths):
        self.image_studio.addPaths(list(paths))
        self.setPage(2)

    @Slot()
    def showStartupMessages(self):
        self._schedule_clipboard_check()
        notice = release_notice_for_version(self.app_version)
        seen = str(self.settings.get("release_notice_seen_version", ""))
        if notice and seen != self.app_version:
            self.settings.set("release_notice_seen_version", self.app_version)
            self.releaseNoticeRequested.emit(notice)
        QTimer.singleShot(450, lambda: self.checkUpdates(False))
        QTimer.singleShot(900, lambda: self.config.refreshDependencies(False))

    @Slot()
    def requestClose(self):
        self.closeRequested.emit()

    def shutdown(self):
        if self._closing:
            return
        self._closing = True
        self.dialogs.close_all()
        self.download.shutdown()
        self.batch.shutdown()
        self.image_studio.shutdown()
        self.config.shutdown()
        self.settings.save()
        self.pool.wait_for_done(2000)


def _qml_root(project_root: Path) -> Path:
    candidates = [
        project_root / "src" / "ui" / "qml",
        Path(getattr(sys, "_MEIPASS", project_root)) / "src" / "ui" / "qml",
        Path(__file__).resolve().parent / "qml",
    ]
    return next((path for path in candidates if (path / "Main.qml").is_file()), candidates[-1])


def run_qt_app(project_root: str | Path, app_version: str) -> int:
    root = Path(project_root)
    resource_root = Path(getattr(sys, "_MEIPASS", root))
    QApplication.setApplicationName("Xomacito")
    QApplication.setOrganizationName("Strike2911")
    if os.name == "nt":
        try:
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("Xomacito.App")
        except (AttributeError, OSError):
            pass
    app = QApplication.instance() or QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(True)
    cat = daily_cat_assets(resource_root)
    if cat.ico_path.is_file():
        app.setWindowIcon(QIcon(str(cat.ico_path)))

    controller = AppController(app, resource_root, app_version)
    engine = QQmlApplicationEngine()
    context = engine.rootContext()
    context.setContextProperty("appController", controller)
    context.setContextProperty("theme", controller.theme)
    context.setContextProperty("downloadController", controller.download)
    context.setContextProperty("batchController", controller.batch)
    context.setContextProperty("imageController", controller.image_studio)
    context.setContextProperty("settingsController", controller.config)
    context.setContextProperty("catController", controller.cats)
    context.setContextProperty("presetStore", controller.presets)
    context.setContextProperty("dialogBroker", controller.dialogs)
    qml = _qml_root(resource_root) / "Main.qml"
    engine.addImportPath(str(qml.parent))
    engine.load(QUrl.fromLocalFile(str(qml)))
    if not engine.rootObjects():
        raise RuntimeError(f"No se pudo cargar la interfaz Qt Quick: {qml}")
    app.aboutToQuit.connect(controller.shutdown, Qt.ConnectionType.DirectConnection)
    QTimer.singleShot(0, controller.showStartupMessages)
    return app.exec()
