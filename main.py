from __future__ import annotations

import os
import shutil
import sys
import traceback
from pathlib import Path


APP_NAME = "Xomacito"
# La versión visible forma parte de la edición pública.  UPDATE_VERSION se
# mantiene numérica para que el instalador de Windows y el actualizador puedan
# comparar correctamente esta entrega con las instalaciones 3.x anteriores.
APP_VERSION = "1.1"
UPDATE_VERSION = "4.0.17"

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
FFMPEG_BIN_DIR = os.environ.get("XOMACITO_FFMPEG_BIN_DIR", str(BIN_PATH / "ffmpeg"))
DENO_BIN_DIR = str(BIN_PATH / "deno")
POPPLER_BIN_DIR = str(BIN_PATH / "poppler")


def _persistent_models_path() -> Path:
    """Return a model store that survives replacing the installed application."""
    override = str(os.environ.get("XOMACITO_MODELS_DIR") or "").strip()
    if override:
        return Path(override).expanduser().resolve()
    if not FROZEN:
        return BIN_PATH / "models"
    local_data = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
    return local_data / APP_NAME / "models"


def migrate_legacy_models(source: Path, destination: Path) -> int:
    """Copy missing downloaded models from an older install without overwriting user data."""
    source = Path(source)
    destination = Path(destination)
    if not source.is_dir() or source.resolve() == destination.resolve():
        return 0
    copied = 0
    for old_path in source.rglob("*"):
        relative = old_path.relative_to(source)
        new_path = destination / relative
        if old_path.is_dir():
            new_path.mkdir(parents=True, exist_ok=True)
            continue
        if not old_path.is_file():
            continue
        try:
            if new_path.is_file() and new_path.stat().st_size > 0:
                continue
            new_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(old_path, new_path)
            copied += 1
        except OSError as error:
            print(f"ADVERTENCIA: No se pudo conservar el modelo {old_path.name}: {error}")
    return copied


MODEL_CATALOG_REVISION = "curated-2026-08-30"
OBSOLETE_REMBG_MODELS = {
    "u2netp.onnx",
    "u2net.onnx",
    "u2net_human_seg.onnx",
    "isnet-general-use.onnx",
    "isnet-anime.onnx",
    "birefnet-cod.onnx",
    "birefnet-hrsod.onnx",
    "birefnet-massive.onnx",
    "birefnet-hr-general.onnx",
    "birefnet-hr-matting.onnx",
}
OBSOLETE_UPSCALE_MODELS = {
    "realesr-animevideov3-x2",
    "realesr-animevideov3-x3",
    "RealESRGAN_General_x4_v3",
    "RealESRGAN_General_WDN_x4_v3",
    "4xHFA2k",
    "4xLSDIR",
    "4xLSDIRCompactC3",
    "4xLSDIRplusC",
    "4xNomos8kSC",
    "4x_NMKD-Siax_200k",
    "4x_NMKD-Superscale-SP_178000_G",
    "uniscale_restore",
    "unknown-2.0.1",
    "DF2K_x4",
    "DF2K_JPEG_x4",
}


def prune_obsolete_models(models_root: Path) -> int:
    """Retira sólo modelos integrados antiguos; nunca borra modelos personalizados."""
    root = Path(models_root)
    marker = root / f".{MODEL_CATALOG_REVISION}"
    if marker.is_file():
        return 0

    removed = 0
    rembg = root / "rembg"
    for filename in OBSOLETE_REMBG_MODELS:
        path = rembg / filename
        if path.is_file():
            try:
                path.unlink()
                removed += 1
            except OSError as error:
                print(f"ADVERTENCIA: No se pudo retirar el modelo antiguo {path.name}: {error}")

    upscayl = root / "upscaling" / "upscayl" / "models"
    for basename in OBSOLETE_UPSCALE_MODELS:
        for suffix in (".bin", ".param"):
            path = upscayl / f"{basename}{suffix}"
            if path.is_file():
                try:
                    path.unlink()
                    removed += 1
                except OSError as error:
                    print(f"ADVERTENCIA: No se pudo retirar el modelo antiguo {path.name}: {error}")

    # Estas familias experimentales nunca admitieron una descarga mantenible.
    for obsolete_family in (root / "rmbg2", root / "inspyrenet"):
        if obsolete_family.is_dir():
            try:
                shutil.rmtree(obsolete_family)
                removed += 1
            except OSError as error:
                print(f"ADVERTENCIA: No se pudo retirar {obsolete_family.name}: {error}")

    try:
        root.mkdir(parents=True, exist_ok=True)
        marker.write_text("Catálogo curado de Xomacito\n", encoding="utf-8")
    except OSError as error:
        print(f"ADVERTENCIA: No se pudo registrar la limpieza de modelos: {error}")
    return removed


MODELS_PATH = _persistent_models_path()
if FROZEN:
    # Versiones anteriores descargaban los modelos dentro de la instalación.
    # Copiarlos antes de usarlos permite actualizar Xomacito sin descargarlos otra vez.
    for legacy_models in (INTERNAL_DIR / "bin" / "models", PROJECT_ROOT / "bin" / "models"):
        migrate_legacy_models(legacy_models, MODELS_PATH)
    prune_obsolete_models(MODELS_PATH)

MODELS_DIR = str(MODELS_PATH)
REMBG_MODELS_DIR = str(MODELS_PATH / "rembg")
UPSCALING_DIR = str(MODELS_PATH / "upscaling")
os.environ.setdefault("U2NET_HOME", REMBG_MODELS_DIR)


def _recommended_ui_scale(width: int, height: int, dpi: int) -> float:
    """Escala adicional conservadora para pantallas grandes que siguen al 100 %."""
    if dpi > 110:
        return 1.0
    if width >= 3800 and height >= 2000:
        return 1.5
    if width >= 2500 and height >= 1350:
        return 1.25
    return 1.0


def _native_primary_resolution(user32) -> tuple[int, int]:
    """Lee la resolución nativa, evitando la virtualización de DPI de GetSystemMetrics."""
    class DevModeW(__import__("ctypes").Structure):
        _fields_ = [
            ("dmDeviceName", __import__("ctypes").c_wchar * 32),
            ("dmSpecVersion", __import__("ctypes").c_ushort),
            ("dmDriverVersion", __import__("ctypes").c_ushort),
            ("dmSize", __import__("ctypes").c_ushort),
            ("dmDriverExtra", __import__("ctypes").c_ushort),
            ("dmFields", __import__("ctypes").c_ulong),
            ("dmPositionX", __import__("ctypes").c_long),
            ("dmPositionY", __import__("ctypes").c_long),
            ("dmDisplayOrientation", __import__("ctypes").c_ulong),
            ("dmDisplayFixedOutput", __import__("ctypes").c_ulong),
            ("dmColor", __import__("ctypes").c_short),
            ("dmDuplex", __import__("ctypes").c_short),
            ("dmYResolution", __import__("ctypes").c_short),
            ("dmTTOption", __import__("ctypes").c_short),
            ("dmCollate", __import__("ctypes").c_short),
            ("dmFormName", __import__("ctypes").c_wchar * 32),
            ("dmLogPixels", __import__("ctypes").c_ushort),
            ("dmBitsPerPel", __import__("ctypes").c_ulong),
            ("dmPelsWidth", __import__("ctypes").c_ulong),
            ("dmPelsHeight", __import__("ctypes").c_ulong),
            ("dmDisplayFlags", __import__("ctypes").c_ulong),
            ("dmDisplayFrequency", __import__("ctypes").c_ulong),
            ("dmICMMethod", __import__("ctypes").c_ulong),
            ("dmICMIntent", __import__("ctypes").c_ulong),
            ("dmMediaType", __import__("ctypes").c_ulong),
            ("dmDitherType", __import__("ctypes").c_ulong),
            ("dmReserved1", __import__("ctypes").c_ulong),
            ("dmReserved2", __import__("ctypes").c_ulong),
            ("dmPanningWidth", __import__("ctypes").c_ulong),
            ("dmPanningHeight", __import__("ctypes").c_ulong),
        ]

    mode = DevModeW()
    mode.dmSize = __import__("ctypes").sizeof(DevModeW)
    if user32.EnumDisplaySettingsW(None, -1, __import__("ctypes").byref(mode)):
        return int(mode.dmPelsWidth), int(mode.dmPelsHeight)
    return int(user32.GetSystemMetrics(0)), int(user32.GetSystemMetrics(1))


def _configure_responsive_qt_scale() -> None:
    """Adapta Qt a la resolución nativa sin duplicar el escalado de Windows."""
    os.environ.setdefault("QT_ENABLE_HIGHDPI_SCALING", "1")
    os.environ.setdefault("QT_SCALE_FACTOR_ROUNDING_POLICY", "PassThrough")
    if os.environ.get("QT_SCALE_FACTOR"):
        return
    requested = str(os.environ.get("XOMACITO_UI_SCALE") or "").strip()
    if requested:
        try:
            if float(requested) > 0:
                os.environ["QT_SCALE_FACTOR"] = requested
        except ValueError:
            pass
        return
    if os.name != "nt":
        return
    try:
        import ctypes

        user32 = ctypes.windll.user32
        width, height = _native_primary_resolution(user32)
        get_dpi = getattr(user32, "GetDpiForSystem", None)
        dpi = int(get_dpi()) if get_dpi else 96
        # Qt ya respeta el escalado configurado en Windows. Sólo compensamos
        # pantallas 2K/4K que siguen al 100 %, que eran las que quedaban diminutas.
        scale = _recommended_ui_scale(width, height, dpi)
        if scale > 1:
            os.environ["QT_SCALE_FACTOR"] = f"{scale:g}"
    except (AttributeError, OSError, TypeError, ValueError):
        return


def _run_self_test() -> int:
    """Comprueba el runtime instalado sin crear una ventana gráfica."""
    if not FROZEN:
        return 0
    try:
        from PySide6.QtCore import qVersion

        if not qVersion():
            return 1
    except (ImportError, OSError):
        return 1
    required_runtime_files = (
        INTERNAL_DIR / "src" / "ui" / "qml" / "Main.qml",
        INTERNAL_DIR / "bin" / "ffmpeg" / ("ffmpeg.exe" if os.name == "nt" else "ffmpeg"),
        INTERNAL_DIR / "bin" / "ytdlp" / "yt-dlp.zip",
    )
    return 0 if all(path.is_file() for path in required_runtime_files) else 1


def _run_main_window() -> int:
    _configure_responsive_qt_scale()
    from src.ui import run_qt_app

    return run_qt_app(
        project_root=PROJECT_ROOT,
        app_version=APP_VERSION,
        update_version=UPDATE_VERSION,
    )


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
