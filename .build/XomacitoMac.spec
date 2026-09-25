# -*- mode: python ; coding: utf-8 -*-
"""Native macOS bundle. Build on the target architecture with Python 3.11."""

import ast
import os
import platform
import subprocess
import sys
from pathlib import Path

from PyInstaller.utils.hooks import collect_all

if sys.platform != "darwin":
    raise SystemExit("XomacitoMac.spec requires macOS.")

ROOT = Path(SPECPATH).resolve().parent


def brew_prefix(formula):
    return Path(subprocess.check_output(["brew", "--prefix", formula], text=True).strip())


datas = [
    (str(ROOT / "assets"), "assets"),
    (str(ROOT / "src/ui/qml"), "src/ui/qml"),
    (str(ROOT / "src/ui/themes"), "src/ui/themes"),
    (str(ROOT / "premiere-panel"), "premiere-panel"),
    (str(ROOT / "Xomacito-icon.ico"), "."),
]
binaries = []
for formula, names in {
    "ffmpeg": ("ffmpeg", "ffprobe"),
    "deno": ("deno",),
    "poppler": ("pdfinfo", "pdftoppm", "pdftocairo"),
    "ghostscript": ("gs",),
}.items():
    prefix = brew_prefix(formula)
    for name in names:
        executable = prefix / "bin" / name
        if not executable.is_file():
            raise SystemExit(f"Missing native tool: {executable}")
        binaries.append((str(executable), f"bin/{formula}"))
    if formula in {"ghostscript", "poppler"}:
        share = prefix / "share" / formula
        if share.is_dir():
            datas.append((str(share), f"share/{formula}"))

# Native libraries must be binaries so PyInstaller rewrites their Mach-O links.
binaries.append((str(brew_prefix("cairo") / "lib/libcairo.2.dylib"), "."))
hiddenimports = [
    "rawpy", "cv2", "cairosvg", "pdf2image", "img2pdf", "py7zr",
    "PySide6.QtCore", "PySide6.QtGui", "PySide6.QtWidgets",
    "PySide6.QtQml", "PySide6.QtQuick", "PySide6.QtQuickControls2",
    "PySide6.QtMultimedia",
]
for package in ("Cryptodome", "curl_cffi", "rembg", "onnxruntime",
                "pillow_avif", "yt_dlp_ejs", "yt_dlp"):
    package_data, package_binaries, package_imports = collect_all(package)
    datas += package_data
    binaries += package_binaries
    hiddenimports += package_imports

versions = {}
for node in ast.parse((ROOT / "main.py").read_text(encoding="utf-8-sig")).body:
    if isinstance(node, ast.Assign):
        for target in node.targets:
            if isinstance(target, ast.Name) and target.id in {"APP_VERSION", "UPDATE_VERSION"}:
                versions[target.id] = ast.literal_eval(node.value)

a = Analysis(
    [str(ROOT / "main.py")], pathex=[str(ROOT)], binaries=binaries,
    datas=datas, hiddenimports=hiddenimports, hookspath=[], hooksconfig={},
    runtime_hooks=[], excludes=["tkinter", "customtkinter", "tkinterdnd2"],
    noarchive=False, optimize=1,
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz, a.scripts, [], exclude_binaries=True, name="Xomacito",
    debug=False, bootloader_ignore_signals=False, strip=False, upx=False,
    console=False, target_arch=platform.machine(),
    codesign_identity=os.environ.get("XOMACITO_CODESIGN_IDENTITY") or None,
)
coll = COLLECT(exe, a.binaries, a.datas, strip=False, upx=False, name="Xomacito")
app = BUNDLE(
    coll, name="Xomacito.app", icon=str(ROOT / "Xomacito-icon.icns"),
    bundle_identifier="com.strike2911.xomacito",
    info_plist={
        "CFBundleName": "Xomacito",
        "CFBundleDisplayName": "Xomacito",
        "CFBundleShortVersionString": versions["APP_VERSION"],
        "CFBundleVersion": versions["UPDATE_VERSION"],
        "NSHighResolutionCapable": True,
        "NSPrincipalClass": "NSApplication",
        "LSMinimumSystemVersion": "14.0",
    },
)
