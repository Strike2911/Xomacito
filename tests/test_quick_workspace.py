"""Real Qt interactions and layout at the application's supported window sizes."""
import os
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]


def test_quick_workspace_layout_and_search():
    script = r'''
from pathlib import Path
from PySide6.QtCore import QObject, QMetaObject, QPointF, Qt, QUrl
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtQuick import QQuickItem
from PySide6.QtQuickControls2 import QQuickStyle
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QFontDatabase, QFont
from src.ui.application import AppController
from src.ui.settings_store import SettingsStore
from tests.test_quick_workflow import DeferredPool
import os
QQuickStyle.setStyle("Basic")
app = QApplication.instance() or QApplication([])
for font in ("segoeui.ttf", "segoeuib.ttf", "seguisb.ttf"):
    QFontDatabase.addApplicationFont("C:/Windows/Fonts/" + font)
app.setFont(QFont("Segoe UI"))
root = Path.cwd()
settings = SettingsStore()
settings.set("premiere_library_path", str(Path(os.environ["APPDATA"]) / "library"))
c = AppController(app, root, "1.4.2 · revisión")
e = QQmlApplicationEngine()
errors = []
e.warnings.connect(lambda warnings: errors.extend(w.toString() for w in warnings))
for name, obj in {"appController":c,"theme":c.theme,"downloadController":c.download,
 "quickController":c.quick,"premiereController":c.premiere,"batchController":c.batch,
 "imageController":c.image_studio,"mediaLibraryController":c.media_library,
 "settingsController":c.config,"catController":c.cats,"socialController":c.social,
 "presetStore":c.presets,"dialogBroker":c.dialogs}.items():
    e.rootContext().setContextProperty(name,obj)
e.load(QUrl.fromLocalFile(str(root / "src/ui/qml/Main.qml")))
assert e.rootObjects(), errors
w = e.rootObjects()[0]
c.setPage(7)
QTest.qWait(250)
page = w.findChild(QQuickItem,"quickWorkspace")
options = w.findChild(QQuickItem,"quickOptions")
for width in (960,1280,1600):
    w.setWidth(width); w.setHeight(720); QTest.qWait(120)
    assert page.isVisible()
    controls = [item for item in options.childItems() if item.isVisible() and item.width() > 0]
    for item in controls:
        assert item.x() >= 0 and item.x()+item.width() <= options.width()+1, (width,item.objectName())
        assert item.y()+item.height() <= options.height()+1
    for i, a in enumerate(controls):
        for b in controls[i+1:]:
            assert a.x()+a.width() <= b.x()+1 or b.x()+b.width() <= a.x()+1 or a.y()+a.height() <= b.y()+1 or b.y()+b.height() <= a.y()+1
    activity = w.findChild(QQuickItem,"quickActivity")
    assert activity.height() >= 250
    if os.getenv("QUICK_CAPTURE"):
        w.grabWindow().save(str(root / (".artifacts/quick-refactor-%s.png" % width)))
field = w.findChild(QQuickItem,"quickUrls")
submit = w.findChild(QObject,"quickSubmit")
c.quick.pool = DeferredPool()
field.forceActiveFocus()
for char in "gatos bailando": QTest.keyClick(w, char)
QTest.qWait(50)
assert submit.property("text") == "Buscar"
QTest.keyClick(w,Qt.Key_Return)
QTest.qWait(50)
assert c.quick.jobs.count() == 0 and len(c.quick.pool.calls) == 1
popup = w.findChild(QObject,"quickDiscoveryPopup")
assert popup.property("visible")
QMetaObject.invokeMethod(popup,"close",Qt.DirectConnection)
c.quick.pool.calls[0][2]["on_result"]([])
QTest.qWait(50)
assert not popup.property("visible")
c.quick.setValue("thumbnailMode", "Solo miniatura")
QTest.qWait(50)
assert not next(item for item in options.childItems() if item.objectName() == "quickOption_quality").isEnabled()
assert not next(item for item in options.childItems() if item.objectName() == "quickOption_mode").isEnabled()
c.quick.setValue("thumbnailMode", "Sin miniatura")
c.quick.setValue("mode", "Audio")
QTest.qWait(50)
audio = next(item for item in options.childItems() if item.objectName() == "quickOption_audioFormat")
assert audio is not None and audio.property("currentText") == "MP3 192"
c.settings.set("download_tags", [{"name":"Prueba", "folder":"C:/destino-etiqueta"}])
c.quick.setValue("selectedTag", "Prueba")
QTest.qWait(50)
output = w.findChild(QObject,"quickOutput")
assert output.property("text") == "C:/destino-etiqueta" and output.property("readOnly")
c.quick.jobs.append(dict(jobId="preview", url="https://example.com/video", title="Clip de prueba — nombre largo para comprobar el espacio de los controles", detail="Listo", status="Completado", progress=1.0, output="preview.mp4", outputs=["preview.mp4"], mode="Video", quality="1080p", thumbnail=""))
c.quick.history.replace(c.quick.jobs.items())
for history in (False, True):
    page.setProperty("historyOpen", history)
    w.setWidth(960); QTest.qWait(100)
    for row in activity.property("contentItem").childItems():
        if row.width() < 10: continue
        for item in row.childItems():
            assert item.x() >= 0 and item.x()+item.width() <= row.width()+1
    if os.getenv("QUICK_CAPTURE"):
        w.grabWindow().save(str(root / (".artifacts/quick-refactor-%s.png" % ("history" if history else "activity"))))
assert not errors, errors
c.shutdown()
print("Quick workspace verified")
'''
    with tempfile.TemporaryDirectory() as appdata:
        result = subprocess.run([sys.executable, "-c", script], cwd=ROOT,
                                env={**os.environ, "APPDATA": appdata, "QT_QPA_PLATFORM": "offscreen"},
                                capture_output=True, text=True, timeout=45)
    assert result.returncode == 0, result.stderr or result.stdout
