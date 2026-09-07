import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]

def test_comparison_progress_and_box_controls_with_real_qt_events(tmp_path):
    script = r"""
from pathlib import Path
import os
from PySide6.QtCore import QObject, QPoint, QPointF, Qt, QUrl, QMetaObject
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtQuick import QQuickItem, QQuickWindow
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication
from src.ui.settings_store import SettingsStore
from src.ui.application import AppController

app = QApplication([])
root = Path.cwd()
SettingsStore().set("premiere_library_path", str(Path(os.environ["APPDATA"]) / "library"))
controller = AppController(app, root, "1.1", "4.0.17")
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
window.setWidth(960)
window.setHeight(680)
def find(item, name):
    if item.objectName() == name:
        return item
    for child in item.childItems():
        found = find(child, name)
        if found is not None:
            return found
def point(item, fraction=0.5):
    return item.mapToScene(QPointF(item.width() * fraction, item.height() / 2)).toPoint()
def click(item, fraction=0.5):
    assert item is not None and item.isVisible()
    QTest.mouseClick(window, Qt.LeftButton, Qt.NoModifier, point(item, fraction))
    QTest.qWait(80)

controller.setPage(3)
source = QUrl.fromLocalFile(str(root / "assets/progress/cat-run-1.png")).toString()
controller.image_studio._set_state(previewSource=source, resultPreviewSource=source)
QTest.qWait(250)
slider = find(window.contentItem(), "imageComparisonSlider")
click(slider, 0.2)
assert 0.1 < slider.property("value") < 0.3
click(slider, 0.8)
assert 0.7 < slider.property("value") < 0.9
before = slider.property("value")
QTest.keyClick(window, Qt.Key_Left)
assert slider.property("value") < before
start = find(window.contentItem(), "imageStudioStartButton")
location = start.mapToScene(QPointF(0, 0))
assert 0 <= location.y() and location.y() + start.height() <= 680
assert start.property("enabled") is False

controller.setPage(0)
QTest.qWait(100)
strip = find(window.contentItem(), "downloadProgress")
cat = find(strip, "progressCat")
assert strip and cat
positions = []
for value in (0, 0.5, 1):
    strip.setProperty("value", value)
    QTest.qWait(350)
    positions.append(cat.x())
assert positions[0] == 0 and positions[0] < positions[1] < positions[2]
assert abs(positions[1] * 2 - positions[2]) < 2
assert positions[2] + cat.width() <= strip.width()

controller.setPage(4)
controller.cats.grantBonusRolls(1)
QTest.qWait(200)
click(find(window.contentItem(), "catSkipAnimationToggle"))
assert controller.cats.state["skipAnimation"]
assert SettingsStore().get("skip_cat_animation") is True
click(find(window.contentItem(), "catRollButton"))
popup = window.findChild(QObject, "catRevealPopup")
assert popup.property("opened")
assert popup.property("done")
assert not controller.cats.state["opening"]
click(find(window.contentItem(), "catRevealSkipToggle"))
assert not controller.cats.state["skipAnimation"]
assert SettingsStore().get("skip_cat_animation") is False
assert controller.cats.state["totalRolls"] == 1
QMetaObject.invokeMethod(popup, "close", Qt.DirectConnection)
QTest.qWait(80)
assert not controller.cats.state["opening"]
click(find(window.contentItem(), "catInventoryTab"))
grid = find(window.contentItem(), "catCollectionGrid")
assert grid.isVisible() and grid.property("count") >= 1
controller.shutdown()
"""
    environment = dict(os.environ, QT_QPA_PLATFORM="offscreen", APPDATA=str(tmp_path))
    result = subprocess.run([sys.executable, "-c", script], cwd=ROOT, env=environment,
                            capture_output=True, text=True, timeout=30)
    assert result.returncode == 0, result.stderr + result.stdout
