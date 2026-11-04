"""Exercise patched QML against the Python theme shipped in the 1.4.7 EXE.

Run from the repository with PySide6, Pillow and PyInstaller installed:
python patches/1.4.7/verify_hotfix.py D:/Xomacito [screenshot-directory]
All preferences and wallpaper copies go into a temporary directory.
"""
import os
import sys
import tempfile
import types
from pathlib import Path

os.environ['QT_QPA_PLATFORM'] = 'offscreen'
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from PyInstaller.archive.readers import CArchiveReader
from PySide6.QtCore import QObject, Property, Slot, QUrl, QMetaObject, Q_ARG, Qt, QPointF
from PySide6.QtGui import QImage, QColor, QFont, QFontDatabase
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtQuick import QQuickItem
from PySide6.QtQuickControls2 import QQuickStyle
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication
from src.ui.settings_store import SettingsStore

installation = Path(sys.argv[1]).resolve()
screenshots = Path(sys.argv[2]).resolve() if len(sys.argv) > 2 else None
archive = CArchiveReader(str(installation / 'Xomacito.exe')).open_embedded_archive('PYZ.pyz')
module = types.ModuleType('src.ui.theme_147')
module.__package__ = 'src.ui'
exec(archive.extract('src.ui.theme'), module.__dict__)

QQuickStyle.setStyle('Basic')
app = QApplication([])
app.setOrganizationName('XomacitoHotfixTests')
app.setApplicationName('IsolatedVerification')
for font in ('segoeui.ttf', 'segoeuib.ttf', 'seguisb.ttf'):
    path = Path(os.environ.get('WINDIR', 'C:/Windows')) / 'Fonts' / font
    if path.is_file(): QFontDatabase.addApplicationFont(str(path))
app.setFont(QFont('Segoe UI', 10))

with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as temporary:
    os.environ['APPDATA'] = temporary
    store = SettingsStore()
    theme = module.ThemeController(installation / '_internal', store)
    theme.setCatThemeUnlocks(10)

    class Config(QObject):
        @Property('QVariantMap', constant=True)
        def state(self): return {'animationsEnabled': False}

        @Slot(str, str)
        def setValue(self, key, value):
            if key == 'theme': theme.setTheme(value)

    config = Config()
    image = QImage(1600, 900, QImage.Format_RGB32)
    image.fill(QColor('#5588aa'))
    source = Path(temporary) / 'sample.png'
    assert image.save(str(source))
    theme.setWallpaper(str(source))
    theme.setWallpaperOpacity(0.17)
    original = theme.backgroundImage

    engine = QQmlApplicationEngine()
    messages = []
    engine.warnings.connect(lambda errors: messages.extend(e.toString() for e in errors))
    engine.rootContext().setContextProperty('theme', theme)
    engine.rootContext().setContextProperty('settingsController', config)
    pages = QUrl.fromLocalFile(str(installation / '_internal/src/ui/qml/pages')).toString()
    wallpaper = QUrl.fromLocalFile(str(installation / '_internal/src/ui/qml/wallpaper')).toString()
    wrapper = f'''import QtQuick
import QtQuick.Controls
import "{pages}"
import "{wallpaper}"
ApplicationWindow {{
    visible: true; width: 1280; height: 720; color: theme.colors.background
    CustomThemePage {{ anchors.fill: parent; anchors.margins: 20 }}
    Component.onCompleted: WallpaperLayout.reset()
}}'''
    engine.loadData(wrapper.encode(), QUrl.fromLocalFile(str(Path(temporary) / 'Test.qml')))
    assert engine.rootObjects(), messages
    window = engine.rootObjects()[0]
    QTest.qWait(300)
    combo = window.findChild(QObject, 'themeCombo')
    index = theme.availableThemes.index('pink_diamond')
    combo.setProperty('currentIndex', index)
    QMetaObject.invokeMethod(combo, 'activated', Qt.DirectConnection, Q_ARG(int, index))
    QTest.qWait(100)
    assert theme.themeName == 'pink_diamond'
    assert theme.backgroundImage, 'Palette change lost the wallpaper'
    assert QImage(QUrl(theme.backgroundImage).toLocalFile()) == QImage(QUrl(original).toLocalFile())
    assert abs(theme.backgroundOpacity - 0.17) < 0.001

    # Use the real image-picker slot, replacing only the native file dialog.
    module.QFileDialog.getOpenFileName = lambda *a, **k: (str(source), '')
    chooser = window.findChild(QObject, 'chooseWallpaperButton')
    QMetaObject.invokeMethod(chooser, 'clicked', Qt.DirectConnection)
    QTest.qWait(150)
    assert theme.backgroundOpacity == 0.5, 'New image must start at 50%'
    before_cancel = theme.backgroundImage
    theme.setWallpaperOpacity(0.3)
    module.QFileDialog.getOpenFileName = lambda *a, **k: ('', '')
    QMetaObject.invokeMethod(chooser, 'clicked', Qt.DirectConnection)
    assert theme.backgroundImage == before_cancel and theme.backgroundOpacity == 0.3

    for width, height in ((960, 680), (1280, 720), (1600, 900)):
        window.setWidth(width)
        window.setHeight(height)
        QTest.qWait(200)
        for name in ('chooseWallpaperButton', 'wallpaperOpacitySlider', 'wallpaperZoomSlider', 'wallpaperPositionX', 'wallpaperPositionY'):
            item = window.findChild(QQuickItem, name)
            assert item is not None
            point = item.mapToScene(QPointF(0, 0))
            assert point.x() >= 0 and point.x() + item.width() <= width, (width, name, point.x(), item.width())
        if screenshots:
            screenshots.mkdir(parents=True, exist_ok=True)
            assert window.grabWindow().save(str(screenshots / f'themes-{width}.png'))

    # Slider changes must reach the same shared renderer settings.
    zoom = window.findChild(QObject, 'wallpaperZoomSlider')
    zoom.setProperty('value', 1.7)
    QMetaObject.invokeMethod(zoom, 'moved', Qt.DirectConnection)
    preview = window.findChild(QObject, 'wallpaperPreview')
    QTest.qWait(100)
    assert preview.property('imageWidth') > preview.property('width') * 1.5
    horizontal = window.findChild(QObject, 'wallpaperPositionX')
    horizontal.setProperty('value', 0.2)
    QMetaObject.invokeMethod(horizontal, 'moved', Qt.DirectConnection)
    index = theme.availableThemes.index('Strike')
    combo.setProperty('currentIndex', index)
    QMetaObject.invokeMethod(combo, 'activated', Qt.DirectConnection, Q_ARG(int, index))
    assert theme.backgroundImage
    assert QImage(QUrl(theme.backgroundImage).toLocalFile()) == QImage(QUrl(before_cancel).toLocalFile())
    QTest.qWait(100)
    assert abs(zoom.property('value') - 1.7) < 0.001
    assert abs(horizontal.property('value') - 0.2) < 0.001
    assert not messages, messages
    window.close()
    del engine
    print('PASS: real 1.4.7 theme, palette persistence, 50% for new images, cancel, zoom, position, 960/1280/1600 px; no QML warnings.')
