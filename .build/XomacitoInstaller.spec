# -*- mode: python ; coding: utf-8 -*-
"""Build instalado de Xomacito en modo one-folder."""

from pathlib import Path

from PyInstaller.utils.hooks import collect_all


PROJECT_ROOT = Path(SPECPATH).resolve().parent

datas = [
    (str(PROJECT_ROOT / "src" / "gui" / "themes"), "src/gui/themes"),
    (str(PROJECT_ROOT / "assets" / "xomacito-logo.png"), "assets"),
    (str(PROJECT_ROOT / "assets" / "cat-icons"), "assets/cat-icons"),
    (str(PROJECT_ROOT / "assets" / "download-complete.mp3"), "assets"),
    (str(PROJECT_ROOT / "Xomacito-icon.ico"), "."),
]

# Componentes de ejecución: forman parte de Xomacito y nunca deben descargarse
# automáticamente al iniciar. Los modelos de IA permanecen bajo demanda.
for tool_name in ("deno", "ffmpeg", "ghostscript", "poppler", "ytdlp"):
    tool_dir = PROJECT_ROOT / "bin" / tool_name
    if tool_dir.is_dir():
        datas.append((str(tool_dir), f"bin/{tool_name}"))

binaries = []

# CairoSVG carga Cairo mediante ctypes, por lo que PyInstaller no detecta
# automáticamente estas DLL nativas. Se toman del runtime portable validado.
for dll_name in (
    "cairo-2.dll",
    "z-1.dll",
    "png16.dll",
    "fontconfig-1.dll",
    "freetype-6.dll",
    "pixman-1-0.dll",
    "libexpat.dll",
    "intl-8.dll",
    "bz2.dll",
):
    binaries.append((str(PROJECT_ROOT / "vendor" / "cairo" / dll_name), "."))
hiddenimports = [
    "rawpy", "cv2", "cairosvg", "pdf2image", "img2pdf", "py7zr",
]

# Conserva el mismo conjunto funcional validado por el build portable.
for package in (
    "customtkinter", "tkinterdnd2", "Cryptodome", "curl_cffi",
    "rembg", "onnxruntime", "pillow_avif", "yt_dlp_ejs", "yt_dlp",
):
    package_datas, package_binaries, package_hiddenimports = collect_all(package)
    datas += package_datas
    binaries += package_binaries
    hiddenimports += package_hiddenimports

a = Analysis(
    [str(PROJECT_ROOT / "main.py")],
    pathex=[str(PROJECT_ROOT)],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["flask_socketio", "socketio", "engineio", "gevent"],
    noarchive=False,
    optimize=1,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="Xomacito",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    icon=str(PROJECT_ROOT / "Xomacito-icon.ico"),
    contents_directory="_internal",
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="Xomacito",
)
