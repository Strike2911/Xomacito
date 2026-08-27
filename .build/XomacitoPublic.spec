# -*- mode: python ; coding: utf-8 -*-
"""Build público: analiza la fuente privada y empaqueta sólo módulos protegidos."""

from pathlib import Path

from PyInstaller.utils.hooks import collect_all


PROJECT_ROOT = Path(SPECPATH).resolve().parent
PROTECTED_ROOT = PROJECT_ROOT / ".build" / "public-hardened" / "protected"

datas = [
    (str(PROJECT_ROOT / "src" / "ui" / "qml"), "src/ui/qml"),
    (str(PROJECT_ROOT / "src" / "ui" / "themes"), "src/ui/themes"),
    (str(PROJECT_ROOT / "assets" / "xomacito-logo.png"), "assets"),
    (str(PROJECT_ROOT / "assets" / "cat-icons"), "assets/cat-icons"),
    (str(PROJECT_ROOT / "assets" / "cat-collection"), "assets/cat-collection"),
    (str(PROJECT_ROOT / "assets" / "download-complete.mp3"), "assets"),
    (str(PROJECT_ROOT / "assets" / "sfx"), "assets/sfx"),
    (str(PROJECT_ROOT / "assets" / "release"), "assets/release"),
    (str(PROJECT_ROOT / "assets" / "config"), "assets/config"),
    (str(PROJECT_ROOT / "Xomacito-icon.ico"), "."),
]

for tool_name in ("deno", "ffmpeg", "ghostscript", "poppler", "ytdlp"):
    tool_dir = PROJECT_ROOT / "bin" / tool_name
    if tool_dir.is_dir():
        datas.append((str(tool_dir), f"bin/{tool_name}"))

binaries = []
for dll_name in (
    "cairo-2.dll", "z-1.dll", "png16.dll", "fontconfig-1.dll",
    "freetype-6.dll", "pixman-1-0.dll", "libexpat.dll", "intl-8.dll", "bz2.dll",
):
    binaries.append((str(PROJECT_ROOT / "vendor" / "cairo" / dll_name), "."))

hiddenimports = [
    "rawpy", "cv2", "cairosvg", "pdf2image", "img2pdf", "py7zr",
    "PySide6.QtCore", "PySide6.QtGui", "PySide6.QtWidgets", "PySide6.QtQml",
    "PySide6.QtQuick", "PySide6.QtQuickControls2", "PySide6.QtMultimedia",
    "xomacito_runtime", "pyarmor_runtime_000000",
]
for package in (
    "Cryptodome", "curl_cffi", "rembg", "onnxruntime",
    "pillow_avif", "yt_dlp_ejs", "yt_dlp",
):
    package_datas, package_binaries, package_hiddenimports = collect_all(package)
    datas += package_datas
    binaries += package_binaries
    hiddenimports += package_hiddenimports

a = Analysis(
    [str(PROJECT_ROOT / "main.py")],
    pathex=[str(PROTECTED_ROOT), str(PROJECT_ROOT)],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["tkinter", "customtkinter", "tkinterdnd2", "flask_socketio", "socketio", "engineio", "gevent"],
    noarchive=False,
    optimize=2,
)

# Qt debe cargar su runtime compatible, no la ICU que algunas dependencias de
# imagen exponen en la raíz durante el análisis de PyInstaller. Poppler conserva
# su copia aislada dentro de bin/poppler.
def is_conflicting_top_level_icu(entry):
    destination = str(entry[0]).replace("\\", "/")
    filename = destination.casefold()
    return "/" not in destination and (
        filename == "icuuc.dll" or filename.startswith("icudt") and filename.endswith(".dll")
    )


a.binaries = [entry for entry in a.binaries if not is_conflicting_top_level_icu(entry)]

for index, entry in enumerate(a.pure):
    module_name, source_path, type_code = entry
    if module_name == "src" or module_name.startswith("src."):
        candidate = PROTECTED_ROOT.joinpath(*module_name.split("."))
        protected_path = candidate / "__init__.py" if candidate.is_dir() else candidate.with_suffix(".py")
        if protected_path.is_file():
            a.pure[index] = (module_name, str(protected_path), type_code)

for index, entry in enumerate(a.scripts):
    script_name, source_path, type_code = entry
    if Path(source_path).resolve() == (PROJECT_ROOT / "main.py").resolve():
        a.scripts[index] = (script_name, str(PROTECTED_ROOT / "main.py"), type_code)

pyz = PYZ(a.pure)
exe = EXE(
    pyz, a.scripts, [], exclude_binaries=True, name="Xomacito", debug=False,
    bootloader_ignore_signals=False, strip=False, upx=True, console=False,
    disable_windowed_traceback=False, icon=str(PROJECT_ROOT / "Xomacito-icon.ico"),
    contents_directory="_internal",
)
coll = COLLECT(
    exe, a.binaries, a.datas, strip=False, upx=True, upx_exclude=[], name="Xomacito",
)
