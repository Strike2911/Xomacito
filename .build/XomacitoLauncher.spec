# -*- mode: python ; coding: utf-8 -*-
"""Lanzador ligero que abre la distribución portable independiente."""

from pathlib import Path
import runpy


PROJECT_ROOT = Path(SPECPATH).resolve().parent

a = Analysis(
    [str(PROJECT_ROOT / "launcher.py")],
    pathex=[str(PROJECT_ROOT)],
    binaries=[],
    datas=[],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=1,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="XomacitoLauncher",
    version=runpy.run_path(str(PROJECT_ROOT / "scripts" / "windows_version_info.py"))["make_version_info"](PROJECT_ROOT, "Xomacito Launcher"),
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    icon=str(PROJECT_ROOT / "Xomacito-icon.ico"),
)
