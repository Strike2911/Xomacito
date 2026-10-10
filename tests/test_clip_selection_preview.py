"""A real media player must stop at the selected out point, not at file end."""
import os
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]


def test_playback_is_limited_to_selection_and_changes_pause_it():
    with tempfile.TemporaryDirectory() as directory:
        media = Path(directory) / "preview.mp4"
        subprocess.run([str(ROOT / "bin/ffmpeg/ffmpeg.exe"), "-v", "error", "-f", "lavfi", "-i",
                        "testsrc2=size=320x180:rate=30", "-t", "4", "-c:v", "libx264", "-pix_fmt", "yuv420p",
                        str(media)], check=True, capture_output=True, timeout=20)
        script = r'''
import sys
from pathlib import Path
from PySide6.QtCore import QObject,QMetaObject,Qt,QUrl
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtMultimedia import QVideoSink
from PySide6.QtQuickControls2 import QQuickStyle
from PySide6.QtWidgets import QApplication
from PySide6.QtTest import QTest
from src.ui.theme import ThemeController
from src.ui.settings_store import SettingsStore
QQuickStyle.setStyle("Basic")
app=QApplication([]); root=Path.cwd(); engine=QQmlApplicationEngine()
settings=SettingsStore(); theme=ThemeController(root,settings)
engine.rootContext().setContextProperty("theme",theme)
engine.loadData(b'import QtQuick\nimport QtQuick.Controls\nimport "src/ui/qml/components"\nApplicationWindow { visible: true; width: 700; height: 400; ClipPreview { objectName: "preview"; anchors.fill: parent; inPoint: 0.7; outPoint: 1.4 } }',QUrl.fromLocalFile(str(root)+"/"))
assert engine.rootObjects()
window=engine.rootObjects()[0]; preview=window.findChild(QObject,"preview")
player=preview.findChild(QObject,"clipSelectionPlayer")
preview.setProperty("source",QUrl.fromLocalFile(sys.argv[1]))
for _ in range(80):
    QTest.qWait(50)
    if player.property("duration") >= 3900: break
assert player.property("duration") >= 3900
QMetaObject.invokeMethod(preview,"playSelection",Qt.DirectConnection)
QTest.qWait(150)
assert preview.property("playing")
assert 700 <= player.property("position") < 1400
assert player.property("videoOutput").property("videoSink").videoFrame().isValid()
QTest.qWait(1100)
assert not preview.property("playing")
assert player.property("position") == 1400
QMetaObject.invokeMethod(preview,"playSelection",Qt.DirectConnection)
QTest.qWait(100)
assert 700 <= player.property("position") < 1000, player.property("position")
preview.setProperty("outPoint",2.0)
assert not preview.property("playing")
preview.setProperty("inPoint",1.5)
QMetaObject.invokeMethod(preview,"playSelection",Qt.DirectConnection)
QTest.qWait(100)
assert 1500 <= player.property("position") < 1800
preview.setProperty("visible",False)
QTest.qWait(100)
assert not preview.property("playing")
'''
        result = subprocess.run([sys.executable, "-c", script, str(media)], cwd=ROOT,
                                env={**os.environ, "APPDATA": directory, "QT_QPA_PLATFORM": "offscreen",
                                     "QT_QUICK_BACKEND": "software"}, capture_output=True, text=True, timeout=25)
        assert result.returncode == 0, result.stderr or result.stdout
