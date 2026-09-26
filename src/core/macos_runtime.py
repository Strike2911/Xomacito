"""Native macOS paths; imported only by the macOS startup branch."""

import ctypes
import os
import shutil
import subprocess
import sys
import tempfile
import uuid
from pathlib import Path

TOOLS = {
    "ffmpeg": ("ffmpeg", "ffprobe"), "deno": ("deno",),
    "poppler": ("pdfinfo", "pdftoppm", "pdftocairo"),
    "ghostscript": ("gs",), "inkscape": ("inkscape",),
}
_CAIRO = None


def support_path():
    return Path.home() / "Library" / "Application Support" / "Xomacito"


def prepare_runtime(resource_root):
    """Expose native binaries through writable per-user tool directories."""
    global _CAIRO
    resource_root = Path(resource_root)
    target = support_path() / "bin"
    search = os.pathsep.join(("/opt/homebrew/bin", "/usr/local/bin", os.environ.get("PATH", "")))
    for family, names in TOOLS.items():
        folder = target / family
        folder.mkdir(parents=True, exist_ok=True)
        for name in names:
            bundled = resource_root / "bin" / family / name
            source = bundled if bundled.is_file() else shutil.which(name, path=search)
            if not source and name == "inkscape":
                candidate = Path("/Applications/Inkscape.app/Contents/MacOS/inkscape")
                source = candidate if candidate.is_file() else None
            link = folder / name
            if source and (not link.exists() or link.is_symlink()):
                source = Path(source).absolute()
                if link.is_symlink():
                    if link.readlink() == source:
                        continue
                temporary = folder / f".{name}.{uuid.uuid4().hex}"
                try:
                    temporary.symlink_to(source)
                    temporary.replace(link)
                finally:
                    temporary.unlink(missing_ok=True)
    os.environ["PATH"] = os.pathsep.join([str(target / key) for key in TOOLS] + [search])
    os.environ["DYLD_FALLBACK_LIBRARY_PATH"] = os.pathsep.join((
        str(resource_root), "/opt/homebrew/lib", "/usr/local/lib", "/usr/lib",
        os.environ.get("DYLD_FALLBACK_LIBRARY_PATH", ""),
    ))
    # Cairo is loaded dynamically by cairocffi, outside ordinary import hooks.
    for library in (resource_root / "libcairo.2.dylib",
                    Path("/opt/homebrew/lib/libcairo.2.dylib"),
                    Path("/usr/local/lib/libcairo.2.dylib")):
        if library.is_file():
            _CAIRO = ctypes.CDLL(str(library))
            break
    gs_share = resource_root / "share" / "ghostscript"
    if gs_share.is_dir():
        os.environ["GS_LIB"] = os.pathsep.join(
            str(path) for version in gs_share.iterdir()
            for path in (version / "Resource" / "Init", version / "lib", version / "Resource" / "Font")
            if path.is_dir()
        )
    return target


def native_tool_info(family, progress):
    progress(f"macOS: {family} se administra con Homebrew.", 100)
    return None, None


def check_native_tool(family, progress):
    root = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parents[2]))
    target = prepare_runtime(root)
    found = all((target / family / name).is_file() for name in TOOLS[family])
    progress(f"{family}: listo." if found else f"Instala {family} con Homebrew y reinicia Xomacito.", 100 if found else -1)
    return found


def self_test(resource_root):
    """Exercise the native libraries and bundled tools before creating a DMG."""
    import importlib

    from PySide6.QtCore import qVersion
    from PIL import Image
    import cairosvg
    from pdf2image import convert_from_path

    for package in ("rawpy", "cv2", "pillow_avif", "onnxruntime", "rembg", "yt_dlp", "yt_dlp_ejs"):
        importlib.import_module(package)
    if not qVersion():
        raise RuntimeError("Qt no pudo inicializarse.")
    if not (Path(resource_root) / "src/ui/qml/Main.qml").is_file():
        raise RuntimeError("Falta la interfaz src/ui/qml/Main.qml en el paquete.")
    root = support_path() / "bin"
    for family, name, flag in (("ffmpeg", "ffmpeg", "-version"),
                               ("ffmpeg", "ffprobe", "-version"),
                               ("deno", "deno", "--version"),
                               ("ghostscript", "gs", "--version")):
        subprocess.run([str(root / family / name), flag], check=True, capture_output=True, timeout=30)
    with tempfile.TemporaryDirectory(prefix="xomacito-smoke-") as directory:
        pdf = Path(directory) / "sample.pdf"
        cairosvg.svg2pdf(bytestring=b'<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16"><rect width="16" height="16" fill="red"/></svg>', write_to=str(pdf))
        pages = convert_from_path(str(pdf), poppler_path=str(root / "poppler"))
        if len(pages) != 1 or pages[0].width <= 0:
            raise RuntimeError("Poppler no pudo convertir el PDF de prueba.")
        png = Path(directory) / "ghostscript.png"
        subprocess.run([str(root / "ghostscript/gs"), "-dBATCH", "-dNOPAUSE", "-sDEVICE=png16m", f"-sOutputFile={png}", str(pdf)], check=True, capture_output=True, timeout=30)
        with Image.open(png) as result:
            if result.width <= 0:
                raise RuntimeError("Ghostscript no pudo convertir el PDF de prueba.")
    return 0
