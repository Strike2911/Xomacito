import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from PIL import Image

from src.core.daily_icon import daily_cat_assets
from src.ui.media_logic import build_media_choices, normalize_info
from src.ui.application import normalize_clipboard_url
from src.ui.presets import ALPHA_PRESET, BUILT_IN_PRESETS, resolve_recode_parameters
from src.ui.settings_store import SettingsStore


ROOT = Path(__file__).resolve().parents[1]


class QtMigrationTests(unittest.TestCase):
    def test_release_20_notice_is_styled_and_fits_1280x720(self):
        script = r'''
from pathlib import Path
from PySide6.QtCore import QObject, QUrl
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication
from src.core.app_updater import release_notice_for_version
from src.ui.application import AppController

app = QApplication([])
root = Path.cwd()
controller = AppController(app, root, "2.1")
engine = QQmlApplicationEngine()
context = engine.rootContext()
for name, value in (
    ("appController", controller), ("theme", controller.theme),
    ("downloadController", controller.download), ("batchController", controller.batch),
    ("imageController", controller.image_studio), ("settingsController", controller.config),
    ("catController", controller.cats),
    ("presetStore", controller.presets), ("dialogBroker", controller.dialogs),
):
    context.setContextProperty(name, value)
engine.load(QUrl.fromLocalFile(str(root / "src/ui/qml/Main.qml")))
window = engine.rootObjects()[0]
window.setProperty("width", 1280)
window.setProperty("height", 720)
controller.releaseNoticeRequested.emit(release_notice_for_version("2.1"))
QTest.qWait(650)
popup = window.findChild(QObject, "releaseNoticePopup")
splash = window.findChild(QObject, "dowpSplash")
assert popup is not None and popup.property("opened") is True
assert popup.property("y") >= 0
assert popup.property("y") + popup.property("height") <= 720
assert splash.property("text") == "LA DowP KILLER UPDATE!!"
controller.shutdown()
'''
        with tempfile.TemporaryDirectory() as appdata:
            environment = dict(os.environ)
            environment.update({"QT_QPA_PLATFORM": "offscreen", "APPDATA": appdata})
            result = subprocess.run(
                [sys.executable, "-c", script], cwd=ROOT, env=environment,
                capture_output=True, text=True, timeout=20, check=False,
            )
        self.assertEqual(result.returncode, 0, result.stderr or result.stdout)

    def test_download_page_fits_1280x720_without_main_scroll(self):
        script = r'''
from pathlib import Path
from PySide6.QtCore import QObject, QPointF, QUrl
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtQuick import QQuickItem
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication
from src.ui.application import AppController

app = QApplication([])
root = Path.cwd()
controller = AppController(app, root, "2.1")
engine = QQmlApplicationEngine()
context = engine.rootContext()
for name, value in (
    ("appController", controller), ("theme", controller.theme),
    ("downloadController", controller.download), ("batchController", controller.batch),
    ("imageController", controller.image_studio), ("settingsController", controller.config),
    ("catController", controller.cats),
    ("presetStore", controller.presets), ("dialogBroker", controller.dialogs),
):
    context.setContextProperty(name, value)
engine.load(QUrl.fromLocalFile(str(root / "src/ui/qml/Main.qml")))
window = engine.rootObjects()[0]
window.setProperty("width", 1280)
window.setProperty("height", 720)
QTest.qWait(220)

def geometry(name):
    item = window.findChild(QObject, name)
    assert item is not None, name
    point = QQuickItem.mapToScene(item, QPointF(0, 0))
    return point.y(), float(item.property("height"))

names = ["downloadSourceCard", "downloadPrimaryGrid", "downloadFooterCard", "downloadProgress"]
blocks = [geometry(name) for name in names]
for index, (y, height) in enumerate(blocks):
    assert y >= 0 and y + height <= 720.5, (names[index], y, height)
for current, following in zip(blocks, blocks[1:]):
    assert current[0] + current[1] <= following[0] + 0.5, (current, following)
assert blocks[1][1] >= 260, blocks
controller.shutdown()
'''
        with tempfile.TemporaryDirectory() as appdata:
            environment = dict(os.environ)
            environment.update({"QT_QPA_PLATFORM": "offscreen", "APPDATA": appdata})
            result = subprocess.run(
                [sys.executable, "-c", script], cwd=ROOT, env=environment,
                capture_output=True, text=True, timeout=20, check=False,
            )
        self.assertEqual(result.returncode, 0, result.stderr or result.stdout)

    def test_clipboard_url_validation_matches_auto_paste_contract(self):
        self.assertEqual(
            normalize_clipboard_url("  https://www.youtube.com/watch?v=xomacito  "),
            "https://www.youtube.com/watch?v=xomacito",
        )
        self.assertEqual(normalize_clipboard_url("ftp://example.test/video"), "")
        self.assertEqual(normalize_clipboard_url("texto https://example.test/video"), "")

    def test_clipboard_links_are_routed_to_the_active_page(self):
        script = r'''
from pathlib import Path
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication
from src.ui.application import AppController

app = QApplication([])
controller = AppController(app, Path.cwd(), "2.1")

app.clipboard().setText("https://example.test/video")
QTest.qWait(220)
assert controller.download.state["url"] == "https://example.test/video"

controller.setPage(1)
app.clipboard().setText("https://example.test/playlist")
QTest.qWait(220)
assert controller.batch.state["url"] == "https://example.test/playlist"

controller.setPage(2)
app.clipboard().setText("https://example.test/image")
QTest.qWait(220)
assert controller.image_studio.state["url"] == "https://example.test/image"

app.clipboard().setText("esto no es un enlace")
QTest.qWait(220)
assert controller.image_studio.state["url"] == "https://example.test/image"
controller.shutdown()
'''
        with tempfile.TemporaryDirectory() as appdata:
            environment = dict(os.environ)
            environment.update({"QT_QPA_PLATFORM": "offscreen", "APPDATA": appdata})
            result = subprocess.run(
                [sys.executable, "-c", script], cwd=ROOT, env=environment,
                capture_output=True, text=True, timeout=20, check=False,
            )
        self.assertEqual(result.returncode, 0, result.stderr or result.stdout)

    def test_qml_application_loads_offscreen(self):
        script = """
from pathlib import Path
from PySide6.QtCore import QTimer
import src.ui.application as application
application.AppController.showStartupMessages = lambda self: QTimer.singleShot(450, self.app.quit)
raise SystemExit(application.run_qt_app(Path.cwd(), '2.1'))
"""
        with tempfile.TemporaryDirectory() as appdata:
            environment = dict(os.environ)
            environment.update({"QT_QPA_PLATFORM": "offscreen", "APPDATA": appdata})
            result = subprocess.run(
                [sys.executable, "-c", script], cwd=ROOT, env=environment,
                capture_output=True, text=True, timeout=20, check=False,
            )
        self.assertEqual(result.returncode, 0, result.stderr or result.stdout)
        self.assertNotIn("QQmlApplicationEngine failed", result.stderr)

    def test_cat_collection_page_and_reveal_fit_1280x720(self):
        script = r'''
from pathlib import Path
from PySide6.QtCore import QObject, QUrl
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtQuick import QQuickItem
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication
from src.ui.application import AppController

app = QApplication([])
root = Path.cwd()
controller = AppController(app, root, "2.1")
engine = QQmlApplicationEngine()
context = engine.rootContext()
for name, value in (
    ("appController", controller), ("theme", controller.theme),
    ("downloadController", controller.download), ("batchController", controller.batch),
    ("imageController", controller.image_studio), ("settingsController", controller.config),
    ("catController", controller.cats), ("presetStore", controller.presets),
    ("dialogBroker", controller.dialogs),
):
    context.setContextProperty(name, value)
engine.load(QUrl.fromLocalFile(str(root / "src/ui/qml/Main.qml")))
window = engine.rootObjects()[0]
window.setProperty("width", 1280)
window.setProperty("height", 720)
QTest.qWait(120)
assert list(controller.pages) == [
    "Descargar", "Cola", "Estudio de Imagen", "Personalización", "Configuración"
]
nav_row = window.findChild(QQuickItem, "navigationBar")
assert nav_row is not None
nav_buttons = sorted(
    [item for item in nav_row.childItems() if item.property("text") in list(controller.pages)],
    key=lambda item: float(item.property("x")),
)
assert len(nav_buttons) == 5
nav_widths = [float(button.property("width")) for button in nav_buttons]
assert max(nav_widths) - min(nav_widths) < 1.5
last_nav = nav_buttons[-1]
assert float(nav_row.property("width")) - (
    float(last_nav.property("x")) + float(last_nav.property("width"))
) < 1.5
controller.setPage(3)
QTest.qWait(650)
assert window.findChild(QObject, "catCollectionGrid") is not None
assert window.findChild(QObject, "catRollButton") is not None
personalization_button = nav_buttons[3]
assert personalization_button.property("showRollBadge") is False
controller.cats.recordSuccessfulDownloads(20)
QTest.qWait(180)
assert personalization_button.property("showRollBadge") is True
assert int(personalization_button.property("pendingCatRolls")) == 2
result = controller.cats.roll()
assert result
QTest.qWait(650)
popup = window.findChild(QObject, "catRevealPopup")
assert popup is not None and popup.property("opened") is True
assert popup.property("y") >= 0
assert popup.property("y") + popup.property("height") <= 720
card = window.findChild(QObject, "catRevealCard")
assert card is not None
assert float(card.property("width")) <= float(popup.property("width"))
assert float(card.property("height")) <= float(popup.property("height"))
QTest.qWait(1600)
assert float(popup.property("revealProgress")) > 0.99
controller.shutdown()
'''
        with tempfile.TemporaryDirectory() as appdata:
            environment = dict(os.environ)
            environment.update({"QT_QPA_PLATFORM": "offscreen", "APPDATA": appdata})
            result = subprocess.run(
                [sys.executable, "-c", script], cwd=ROOT, env=environment,
                capture_output=True, text=True, timeout=25, check=False,
            )
        self.assertEqual(result.returncode, 0, result.stderr or result.stdout)

    def test_real_qml_controls_reach_python_controllers(self):
        script = r'''
from pathlib import Path
from PySide6.QtCore import QObject, QMetaObject, QPoint, QPointF, Qt, QUrl
from PySide6.QtQml import QQmlApplicationEngine, QQmlComponent
from PySide6.QtQuick import QQuickItem
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication
from src.ui.application import AppController

app = QApplication([])
root = Path.cwd()
controller = AppController(app, root, "2.1")
engine = QQmlApplicationEngine()
context = engine.rootContext()
for name, value in (
    ("appController", controller), ("theme", controller.theme),
    ("downloadController", controller.download), ("batchController", controller.batch),
    ("imageController", controller.image_studio), ("settingsController", controller.config),
    ("catController", controller.cats),
    ("presetStore", controller.presets), ("dialogBroker", controller.dialogs),
):
    context.setContextProperty(name, value)
engine.load(QUrl.fromLocalFile(str(root / "src/ui/qml/Main.qml")))
window = engine.rootObjects()[0]
window.setProperty("width", 1380)
window.setProperty("height", 850)
QTest.qWait(180)

def open_combo(item):
    point = QQuickItem.mapToScene(
        item, QPointF(item.property("width") / 2, item.property("height") / 2)
    )
    QTest.mouseClick(
        window, Qt.LeftButton, Qt.NoModifier, QPoint(round(point.x()), round(point.y()))
    )
    QTest.qWait(60)

download_mode = window.findChild(QObject, "downloadModeCombo")
assert download_mode is not None
open_combo(download_mode)
QTest.keyClick(window, Qt.Key_End)
QTest.keyClick(window, Qt.Key_Return)
QTest.qWait(120)
assert controller.download.state["mode"] == "Solo Audio"

advanced_button = window.findChild(QObject, "advancedToolsButton")
advanced_popup = window.findChild(QObject, "advancedToolsPopup")
assert advanced_button is not None and advanced_popup is not None
assert QMetaObject.invokeMethod(advanced_popup, "open", Qt.DirectConnection)
QTest.qWait(220)
assert advanced_popup.property("opened") is True
QTest.keyClick(window, Qt.Key_Escape)
QTest.qWait(180)
assert advanced_popup.property("opened") is False

controller.setPage(4)
QTest.qWait(120)
theme_combo = window.findChild(QObject, "themeCombo")
assert theme_combo is not None
open_combo(theme_combo)
QTest.keyClick(window, Qt.Key_Home)
QTest.keyClick(window, Qt.Key_Down)
QTest.keyClick(window, Qt.Key_Down)
QTest.keyClick(window, Qt.Key_Return)
QTest.qWait(260)
assert controller.theme.themeName == "forest_moss"
assert controller.config.state["theme"] == "forest_moss"
assert controller.theme.colors["primary"].lower() == "#5f8e4c"

probe = QQmlComponent(engine)
probe.setData(b"""import QtQuick
QtObject {
    Component.onCompleted: {
        settingsController.setValue("compactMode", true)
        downloadController.setOption("keepOriginal", false)
        batchController.setValue("fastMode", true)
        imageController.setOption("resizeEnabled", true)
    }
}""", QUrl())
probe_object = probe.create()
assert probe_object is not None, probe.errors()
QTest.qWait(80)
assert controller.config.state["compactMode"] is True
assert controller.download.options["keepOriginal"] is False
assert controller.batch.state["fastMode"] is True
assert controller.image_studio.options["resizeEnabled"] is True
controller.shutdown()
'''
        with tempfile.TemporaryDirectory() as appdata:
            environment = dict(os.environ)
            environment.update({"QT_QPA_PLATFORM": "offscreen", "APPDATA": appdata})
            result = subprocess.run(
                [sys.executable, "-c", script], cwd=ROOT, env=environment,
                capture_output=True, text=True, timeout=25, check=False,
            )
        self.assertEqual(result.returncode, 0, result.stderr or result.stdout)

    def test_daily_avatar_has_a_sharp_circular_ui_asset(self):
        selected = daily_cat_assets(ROOT)
        self.assertTrue(selected.ui_path.is_file())
        with Image.open(selected.ui_path) as image:
            self.assertEqual(image.size, (768, 768))
            self.assertEqual(image.mode, "RGBA")
            self.assertEqual(image.getpixel((0, 0))[3], 0)

    def test_qml_mutation_slots_are_qvariant_compatible(self):
        for relative in (
            "src/ui/settings_controller.py", "src/ui/download_controller.py",
            "src/ui/batch_controller.py", "src/ui/image_controller.py",
        ):
            source = (ROOT / relative).read_text(encoding="utf-8")
            self.assertNotIn("@Slot(str, object)", source)
            self.assertIn('@Slot(str, "QVariant")', source)

    def test_all_five_pages_are_persistent_and_have_tools(self):
        main = (ROOT / "src" / "ui" / "qml" / "Main.qml").read_text(encoding="utf-8")
        self.assertIn("StackLayout", main)
        for page in ("DownloadPage", "QueuePage", "ImageStudioPage", "SettingsPage", "CatGachaPage"):
            self.assertEqual(main.count(page), 1)

        download = (ROOT / "src" / "ui" / "qml" / "pages" / "DownloadPage.qml").read_text(encoding="utf-8")
        self.assertNotIn('objectName: "downloadContentScroll"', download)
        advanced_popup = download.index("id: advanced")
        only_scroll = download.index("contentItem: ScrollView")
        self.assertGreater(only_scroll, advanced_popup, "Sólo las herramientas emergentes pueden desplazarse")
        for label in ("Fragmento", "Subtítulos", "Recodificación", "Fotogramas", "Reescalado"):
            self.assertIn(label, download)
        image = (ROOT / "src" / "ui" / "qml" / "pages" / "ImageStudioPage.qml").read_text(encoding="utf-8")
        for label in ("Tamaño", "Lienzo", "Formato", "I.A.", "Video"):
            self.assertIn(label, image)

    def test_runtime_no_longer_depends_on_tk(self):
        requirements = (ROOT / "requirements.txt").read_text(encoding="utf-8")
        spec = (ROOT / ".build" / "XomacitoInstaller.spec").read_text(encoding="utf-8")
        main = (ROOT / "main.py").read_text(encoding="utf-8")
        self.assertIn("PySide6==", requirements)
        self.assertNotIn("customtkinter", requirements.lower())
        self.assertNotIn("tkinterdnd", requirements.lower())
        self.assertNotIn("import customtkinter", main)
        self.assertIn('"PySide6.QtQuick"', spec)
        self.assertIn('"customtkinter"', spec.split("excludes=", 1)[1])

    def test_settings_are_saved_atomically_and_keep_legacy_values(self):
        with tempfile.TemporaryDirectory() as directory, patch.dict(os.environ, {"APPDATA": directory}):
            store = SettingsStore("XomacitoTest")
            store.update({"appearance_mode": "Light", "legacy_key": {"kept": True}})
            payload = json.loads(store.path.read_text(encoding="utf-8"))
            self.assertEqual(payload["appearance_mode"], "Light")
            self.assertEqual(payload["legacy_key"], {"kept": True})
            self.assertFalse(list(store.directory.glob("*.tmp")))

    def test_media_choices_keep_video_audio_and_subtitles(self):
        info = normalize_info({
            "id": "demo", "title": "Demo", "duration": 12,
            "formats": [
                {"format_id": "v", "ext": "mp4", "vcodec": "avc1", "acodec": "none", "height": 1080, "fps": 60, "filesize": 10_000_000},
                {"format_id": "a", "ext": "m4a", "vcodec": "none", "acodec": "mp4a", "abr": 192, "filesize": 2_000_000},
            ],
            "subtitles": {"es": [{"ext": "vtt", "url": "https://example.test/es.vtt"}]},
        })
        choices = build_media_choices(info)
        self.assertTrue(choices["video"])
        self.assertTrue(choices["audio"])
        self.assertIn("es", choices["subtitles"])

    def test_alpha_preset_is_prores_4444(self):
        params, container = resolve_recode_parameters(BUILT_IN_PRESETS[ALPHA_PRESET])
        joined = " ".join(params)
        self.assertEqual(container, ".mov")
        self.assertIn("prores_ks", joined)
        self.assertIn("yuva444p10le", joined)
        self.assertNotIn("profile:v 0", joined)


if __name__ == "__main__":
    unittest.main()
