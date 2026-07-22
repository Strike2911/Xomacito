from __future__ import annotations

import os
import sys
import traceback
from pathlib import Path


APP_NAME = "Xomacito"
APP_VERSION = "2.2"

FROZEN = bool(getattr(sys, "frozen", False))
PROJECT_ROOT = Path(sys.executable).resolve().parent if FROZEN else Path(__file__).resolve().parent
INTERNAL_DIR = Path(getattr(sys, "_MEIPASS", PROJECT_ROOT / "_internal")) if FROZEN else PROJECT_ROOT / "_internal"
SRC_DIR = INTERNAL_DIR / "src" if FROZEN else (
    PROJECT_ROOT / "src" if (PROJECT_ROOT / "src").exists() else INTERNAL_DIR / "src"
)

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
if not FROZEN and SRC_DIR.parent == INTERNAL_DIR and str(INTERNAL_DIR) not in sys.path:
    sys.path.append(str(INTERNAL_DIR))

if os.name == "nt" and hasattr(os, "add_dll_directory"):
    _DLL_DIRECTORY_HANDLES = []
    for dll_dir in dict.fromkeys((INTERNAL_DIR, PROJECT_ROOT / "_internal")):
        if dll_dir.exists():
            _DLL_DIRECTORY_HANDLES.append(os.add_dll_directory(str(dll_dir)))
            os.environ["PATH"] = str(dll_dir) + os.pathsep + os.environ.get("PATH", "")

BIN_PATH = INTERNAL_DIR / "bin" if FROZEN and (INTERNAL_DIR / "bin").is_dir() else PROJECT_ROOT / "bin"
BIN_DIR = str(BIN_PATH)
FFMPEG_BIN_DIR = str(BIN_PATH / "ffmpeg")
DENO_BIN_DIR = str(BIN_PATH / "deno")
POPPLER_BIN_DIR = str(BIN_PATH / "poppler")
MODELS_DIR = str(BIN_PATH / "models")
REMBG_MODELS_DIR = str(BIN_PATH / "models" / "rembg")
UPSCALING_DIR = str(BIN_PATH / "models" / "upscaling")


def _run_self_test() -> int:
    """Comprueba el runtime instalado sin crear una ventana gráfica."""
    if not FROZEN:
        return 0
    required_runtime_files = (
        INTERNAL_DIR / "src" / "ui" / "qml" / "Main.qml",
        INTERNAL_DIR / "bin" / "ffmpeg" / ("ffmpeg.exe" if os.name == "nt" else "ffmpeg"),
        INTERNAL_DIR / "bin" / "ytdlp" / "yt-dlp.zip",
    )
    return 0 if all(path.is_file() for path in required_runtime_files) else 1


def _run_main_window() -> int:
    from src.ui import run_qt_app

    return run_qt_app(project_root=PROJECT_ROOT, app_version=APP_VERSION)


def main() -> int:
    if "--self-test" in sys.argv:
        return _run_self_test()

    from src.core.restart import restart_wait_requested
    from src.core.single_instance import SingleInstanceGuard, focus_existing_window

    instance_guard = SingleInstanceGuard(APP_NAME)
    restart_wait = 15.0 if restart_wait_requested() else 0.0
    if not instance_guard.acquire(wait_seconds=restart_wait):
        focus_existing_window(APP_NAME)
        return 0
    try:
        return _run_main_window()
    finally:
        instance_guard.release()


def _run_safely() -> int:
    try:
        return main()
    except Exception:
        error_log = PROJECT_ROOT / "Xomacito-startup-error.log"
        details = traceback.format_exc()
        try:
            error_log.write_text(details, encoding="utf-8")
        except OSError:
            pass
        if FROZEN and os.name == "nt":
            import ctypes

            ctypes.windll.user32.MessageBoxW(
                None,
                f"Xomacito no pudo iniciar. Se guardó el diagnóstico en:\n{error_log}",
                "Xomacito",
                0x10,
            )
            return 1
        raise


if __name__ == "__main__":
    raise SystemExit(_run_safely())
