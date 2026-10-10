"""Keep Qt's QML collection except unused embedded browser modules."""
from PyInstaller.utils.hooks.qt import add_qt6_dependencies, pyside6_library_info

hiddenimports, binaries, datas = add_qt6_dependencies(__file__)
qml_binaries, qml_datas = pyside6_library_info.collect_qtqml_files()


def used(entry):
    destination = entry[1].replace("\\", "/").split("/")
    return not any(part in {"QtWebEngine", "QtWebView"} for part in destination)


binaries += [entry for entry in qml_binaries if used(entry)]
datas += [entry for entry in qml_datas if used(entry)]
