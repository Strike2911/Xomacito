"""Exercise real QML geometry, expanded-player exit and reveal timing."""
import os
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]


def test_preview_controls_and_reveal_do_not_leak_prize():
    script = r'''
from pathlib import Path
from PySide6.QtCore import QObject, QMetaObject, QPointF, Qt, QUrl
from PySide6.QtQml import QQmlApplicationEngine, QQmlProperty
from PySide6.QtQuick import QQuickItem
from PySide6.QtQuickControls2 import QQuickStyle
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QFontDatabase, QFont
from src.ui.application import AppController
from src.ui.settings_store import SettingsStore
import os
QQuickStyle.setStyle("Basic")
app = QApplication([])
for font in ("segoeui.ttf", "segoeuib.ttf", "seguisb.ttf"):
    QFontDatabase.addApplicationFont("C:/Windows/Fonts/" + font)
app.setFont(QFont("Segoe UI"))
root = Path.cwd()
settings = SettingsStore()
settings.set("premiere_library_path", str(Path(os.environ["APPDATA"]) / "library"))
c = AppController(app, root, "1.4.1")
e = QQmlApplicationEngine()
for name, obj in {"appController":c,"theme":c.theme,"downloadController":c.download,
 "quickController":c.quick,"premiereController":c.premiere,"batchController":c.batch,
 "imageController":c.image_studio,"mediaLibraryController":c.media_library,
 "settingsController":c.config,"catController":c.cats,"socialController":c.social,
 "presetStore":c.presets,"dialogBroker":c.dialogs}.items():
    e.rootContext().setContextProperty(name,obj)
e.load(QUrl.fromLocalFile(str(root / "src/ui/qml/Main.qml")))
assert e.rootObjects()
w = e.rootObjects()[0]
c.setPage(2)
QTest.qWait(600)
for width in (960,1280):
    c.media_library._set_state(selected={"path":"preview-test.mp4","kind":"Video","name":"Vista de prueba", "thumbnailSource":QUrl.fromLocalFile(str(c.cats.catalog[0].avatar_path)).toString()})
    w.setWidth(width); w.setHeight(720); QTest.qWait(180)
    actions = w.findChild(QQuickItem,"libraryLocalActions")
    assert actions.isVisible()
    bottom = actions.mapToItem(actions.parentItem(),QPointF(0,actions.height())).y()
    assert bottom <= actions.parentItem().height()+1, (width,bottom,actions.parentItem().height())
    if os.getenv("POLISH_CAPTURE"):
        w.grabWindow().save(str(root / (".artifacts/polish-library-%s.png" % width)))
preview = w.findChild(QObject,"libraryInteractivePreview")
speed = preview.findChild(QObject,"previewPlaybackSpeed")
assert speed.property("displayText") == "Vel. 1×"
assert speed.property("width") >= 96
QMetaObject.invokeMethod(preview,"toggleExpand",Qt.DirectConnection)
QTest.qWait(180)
assert preview.property("enlarged")
close = preview.findChild(QObject,"closeExpandedPreview")
assert close.property("visible") and "Esc" in close.property("text")
if os.getenv("POLISH_CAPTURE"):
    w.grabWindow().save(str(root / ".artifacts/polish-expanded.png"))
QTest.keyClick(w,Qt.Key_Escape); QTest.qWait(180)
assert not preview.property("enlarged")
QMetaObject.invokeMethod(preview,"toggleExpand",Qt.DirectConnection); QTest.qWait(180)
QMetaObject.invokeMethod(close,"clicked",Qt.DirectConnection); QTest.qWait(180)
assert not preview.property("enlarged")
c.setPage(4)
popup = w.findChild(QObject,"catRevealPopup")
reel = [{"name":"Prueba","rarityColor":"#B06CFF","price":"$1","source":""}]*40
c.cats.revealRequested.emit({"name":"Prueba","rarity":6,"rarityColor":"#FF5FE7","animationStyle":"strike-apex","reel":reel})
QTest.qWait(150)
assert not popup.property("done")
border = popup.findChild(QObject,"catRevealBorder")
assert QQmlProperty.read(border,"border.color").name().lower() != "#ff5fe7"
effects = popup.findChild(QObject,"revealMythicEffects")
confetti = popup.findChild(QObject,"revealConfetti")
assert not effects.property("visible")
assert not confetti.property("active")
QTest.qWait(2700)
assert effects.property("visible") and confetti.property("active")
assert confetti.property("progress") < 1
assert QQmlProperty.read(border,"border.color").name().lower() == "#ff5fe7"
if os.getenv("POLISH_CAPTURE"):
    QTest.qWait(250)
    w.grabWindow().save(str(root / ".artifacts/polish-reveal.png"))
c.config.setValue("animationsEnabled",False); QTest.qWait(50)
assert not confetti.property("active")
QMetaObject.invokeMethod(popup,"close",Qt.DirectConnection)
QTest.qWait(180)
assert not confetti.property("active")
c.shutdown()
print("preview and reveal verified")
'''
    with tempfile.TemporaryDirectory() as appdata:
        result = subprocess.run([sys.executable, "-c", script], cwd=ROOT,
                                env={**os.environ, "APPDATA": appdata, "QT_QPA_PLATFORM": "offscreen"},
                                capture_output=True, text=True, timeout=45)
    assert result.returncode == 0, result.stderr or result.stdout
