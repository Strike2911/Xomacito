import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]


class DownloadPreferencesTests(unittest.TestCase):
    def test_destinations_and_runner_survive_restart_and_layout_fits(self):
        script = r'''
import os
from pathlib import Path
from PySide6.QtCore import QObject, QPointF, QUrl
from PySide6.QtGui import QFont, QFontDatabase
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtQuick import QQuickItem
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication
from src.ui.application import AppController
from src.ui.settings_store import SettingsStore

app = QApplication([])
for font in ("segoeui.ttf", "segoeuib.ttf", "seguisb.ttf"):
    font_path = Path(os.environ.get("WINDIR", "/nonexistent")) / "Fonts" / font
    if font_path.is_file():
        QFontDatabase.addApplicationFont(str(font_path))
app.setFont(QFont("Segoe UI", 10))
root = Path.cwd()
home = Path(os.environ["APPDATA"])
store = SettingsStore()
store.update({
    "premiere_library_enabled": True,
    "premiere_library_path": str(home / "Library"),
    "default_download_path": str(home / "Download destination"),
    "batch_download_path": str(home / "Queue destination"),
})
controller = AppController(app, root, "1.2.5")
assert controller.download.state["effectiveOutputPath"] == str(home / "Download destination")
assert controller.batch.state["effectiveOutputPath"] == str(home / "Queue destination")
controller.download.setValue("outputPath", str(home / "Chosen download"))
controller.batch.setValue("outputPath", str(home / "Chosen queue"))
controller.settings.set("progress_cat", "siamese")
controller.media_library.libraryPathChanged.emit(str(home / "Other library"))
assert controller.download.state["effectiveOutputPath"] == str(home / "Chosen download")
assert controller.batch.state["effectiveOutputPath"] == str(home / "Chosen queue")
controller.shutdown()

controller = AppController(app, root, "1.2.5")
assert controller.download.state["effectiveOutputPath"] == str(home / "Chosen download")
assert controller.batch.state["effectiveOutputPath"] == str(home / "Chosen queue")
assert controller.config.state["progressCat"] == "classic"
assert controller.settings.get("progress_cat") == "classic"
controller.settings.update({
    "download_tags": [{"name": "Music", "folder": str(home / "Tagged"), "color": "#84CC16"}],
    "selected_download_tag": "Music",
})
controller.shutdown()
controller = AppController(app, root, "1.2.5")
assert controller.download.state["effectiveOutputPath"] == str(home / "Tagged")
assert controller.batch.state["effectiveOutputPath"] == str(home / "Tagged")
controller.download.selectDownloadTag("Sin etiqueta")
assert controller.download.state["effectiveOutputPath"] == str(home / "Chosen download")
assert controller.batch.state["effectiveOutputPath"] == str(home / "Chosen queue")

engine = QQmlApplicationEngine()
for name, value in (
    ("appController", controller), ("theme", controller.theme),
    ("downloadController", controller.download), ("batchController", controller.batch),
    ("imageController", controller.image_studio), ("mediaLibraryController", controller.media_library),
    ("settingsController", controller.config), ("catController", controller.cats),
    ("socialController", controller.social), ("presetStore", controller.presets),
    ("dialogBroker", controller.dialogs),
):
    engine.rootContext().setContextProperty(name, value)
engine.load(QUrl.fromLocalFile(str(root / "src/ui/qml/Main.qml")))
assert engine.rootObjects()
window = engine.rootObjects()[0]
window.show()
for width, height in ((960, 680), (1280, 720), (1440, 900)):
    window.setWidth(width)
    window.setHeight(height)
    for mode in ("Video+Audio", "Solo Audio"):
        controller.download.setValue("mode", mode)
        QTest.qWait(160)
        fields = window.findChild(QQuickItem, "downloadOutputFields")
        options = window.findChild(QQuickItem, "downloadPresetOptions")
        assert fields and options
        assert fields.y() + fields.height() <= options.y() + 1, (width, height, mode, fields.height(), options.y())
        assert options.y() + options.height() <= options.parentItem().height() + 1, (width, height, mode)
        for item in fields.findChildren(QQuickItem) + options.findChildren(QQuickItem):
            if item.isVisible() and item.inherits("QQuickControl"):
                pos = item.mapToItem(fields.parentItem(), 0, 0)
                assert pos.x() >= -1 and pos.x() + item.width() <= fields.parentItem().width() + 1, (width, item.metaObject().className(), pos.x(), item.width())
        if os.environ.get("XOMACITO_REVIEW_DIR"):
            window.grabWindow().save(str(Path(os.environ["XOMACITO_REVIEW_DIR"]) / f"download-{width}-{mode}.png"))

controller.setPage(4)
QTest.qWait(200)
selector = window.findChild(QObject, "progressCatSelector")
assert selector is not None and selector.property("currentIndex") == 0
controller.config.setValue("progressCat", "classic")
QTest.qWait(50)
assert selector.property("currentIndex") == 0
controller.config.setValue("progressCat", "orange")
QTest.qWait(50)
assert selector.property("currentIndex") == 1
controller.config.setValue("progressCat", "siamese")
controller.config.setValue("progressCat", "invalid")
assert controller.config.state["progressCat"] == "orange"
if os.environ.get("XOMACITO_REVIEW_DIR"):
    window.grabWindow().save(str(Path(os.environ["XOMACITO_REVIEW_DIR"]) / "personalization.png"))
window.setWidth(960)
window.setHeight(680)
QTest.qWait(160)
runner_card = window.findChild(QQuickItem, "progressCatSettings")
assert runner_card.isVisible() and runner_card.height() >= 60
assert runner_card.mapToScene(QPointF(0, 0)).y() + runner_card.height() < window.height()
if os.environ.get("XOMACITO_REVIEW_DIR"):
    window.grabWindow().save(str(Path(os.environ["XOMACITO_REVIEW_DIR"]) / "personalization-small.png"))
controller.shutdown()
'''
        with tempfile.TemporaryDirectory() as appdata:
            environment = dict(os.environ, QT_QPA_PLATFORM="offscreen", APPDATA=appdata)
            result = subprocess.run(
                [sys.executable, "-c", script], cwd=ROOT, env=environment,
                capture_output=True, text=True, timeout=60,
            )
        self.assertEqual(result.returncode, 0, result.stderr or result.stdout)
