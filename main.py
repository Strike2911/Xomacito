from __future__ import annotations

import json
import copy
import os
import sys
import traceback
from pathlib import Path


APP_NAME = "Xomacito"
APP_VERSION = "1.5.1"
BUILTIN_THEMES = {"blue", "dark-blue", "green"}

FROZEN = bool(getattr(sys, "frozen", False))
PROJECT_ROOT = Path(sys.executable).resolve().parent if FROZEN else Path(__file__).resolve().parent
INTERNAL_DIR = Path(getattr(sys, "_MEIPASS", PROJECT_ROOT / "_internal")) if FROZEN else PROJECT_ROOT / "_internal"
SRC_DIR = INTERNAL_DIR / "src" if FROZEN else (
    PROJECT_ROOT / "src" if (PROJECT_ROOT / "src").exists() else INTERNAL_DIR / "src"
)

for path in (PROJECT_ROOT,):
    value = str(path)
    if value not in sys.path:
        sys.path.insert(0, value)

# En desarrollo el paquete ``src`` vive dentro de ``_internal``. Se agrega al
# final para que no tape dependencias instaladas con copias antiguas del motor.
if not FROZEN and SRC_DIR.parent == INTERNAL_DIR and str(INTERNAL_DIR) not in sys.path:
    sys.path.append(str(INTERNAL_DIR))

if os.name == "nt" and hasattr(os, "add_dll_directory"):
    _DLL_DIRECTORY_HANDLES = []
    dll_dirs = [INTERNAL_DIR, PROJECT_ROOT / "_internal"]
    for dll_dir in dict.fromkeys(dll_dirs):
        if dll_dir.exists():
            _DLL_DIRECTORY_HANDLES.append(os.add_dll_directory(str(dll_dir)))
            os.environ["PATH"] = str(dll_dir) + os.pathsep + os.environ.get("PATH", "")

if FROZEN and (INTERNAL_DIR / "bin").is_dir():
    BIN_PATH = INTERNAL_DIR / "bin"
else:
    # Compatibilidad con desarrollo y distribuciones anteriores.
    BIN_PATH = PROJECT_ROOT / "bin"

BIN_DIR = str(BIN_PATH)
FFMPEG_BIN_DIR = str(BIN_PATH / "ffmpeg")
DENO_BIN_DIR = str(BIN_PATH / "deno")
POPPLER_BIN_DIR = str(BIN_PATH / "poppler")
MODELS_DIR = str(BIN_PATH / "models")
REMBG_MODELS_DIR = str(BIN_PATH / "models" / "rembg")
UPSCALING_DIR = str(BIN_PATH / "models" / "upscaling")


def _settings() -> dict:
    appdata = Path(os.getenv("APPDATA", str(Path.home() / "AppData" / "Roaming")))
    settings_path = appdata / APP_NAME / "app_settings.json"
    try:
        return json.loads(settings_path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def _theme_path(settings: dict) -> Path | str:
    saved = str(settings.get("selected_theme_accent", "midnight_ocean")).strip()
    normalized = saved.lower()
    if normalized in BUILTIN_THEMES and settings.get("theme_selection_explicit", False):
        return normalized
    legacy_names = BUILTIN_THEMES | {""}
    theme_name = "midnight_ocean" if normalized in legacy_names else saved
    candidates = [
        SRC_DIR / "gui" / "themes" / f"{theme_name}.json",
        SRC_DIR / "gui" / "themes" / "midnight_ocean.json",
    ]
    return next((path for path in candidates if path.exists()), candidates[-1])


def _load_custom_theme(ctk, theme_path: Path | str) -> dict:
    """Carga temas propios incluso si el JSON heredado contiene BOM UTF-8."""
    if isinstance(theme_path, str) and theme_path in BUILTIN_THEMES:
        return _builtin_theme_data(ctk, theme_path)

    theme_path = Path(theme_path)
    theme_data = json.loads(theme_path.read_text(encoding="utf-8-sig"))
    manager = ctk.ThemeManager
    manager.theme = theme_data
    manager._currently_loaded_theme = str(theme_path)

    for key in list(manager.theme):
        value = manager.theme[key]
        if isinstance(value, dict) and any(platform_name in value for platform_name in ("Windows", "macOS", "Linux")):
            if sys.platform == "darwin":
                manager.theme[key] = value.get("macOS", next(iter(value.values())))
            elif sys.platform.startswith("win"):
                manager.theme[key] = value.get("Windows", next(iter(value.values())))
            else:
                manager.theme[key] = value.get("Linux", next(iter(value.values())))

    if "CTkCheckbox" in manager.theme:
        manager.theme["CTkCheckBox"] = manager.theme.pop("CTkCheckbox")
    if "CTkRadiobutton" in manager.theme:
        manager.theme["CTkRadioButton"] = manager.theme.pop("CTkRadiobutton")
    return theme_data


def _builtin_theme_data(ctk, theme_name: str) -> dict:
    """Convierte un tema integrado de CTk en una paleta completa de Xomacito."""
    ctk.set_default_color_theme(theme_name)
    data = copy.deepcopy(ctk.ThemeManager.theme)

    button = data.get("CTkButton", {})
    frame = data.get("CTkFrame", {})
    label = data.get("CTkLabel", {})
    entry = data.get("CTkEntry", {})
    primary = button.get("fg_color", ["#3B8ED0", "#1F6AA5"])
    primary_hover = button.get("hover_color", ["#36719F", "#144870"])
    text = label.get("text_color", ["#17212B", "#DCE4EE"])
    surface = frame.get("fg_color", ["#E4EDF5", "#242A30"])
    surface_border = frame.get("border_color", ["#A9B8C5", "#3B4854"])
    field = entry.get("fg_color", ["#F9F9FA", "#252C33"])

    visual_palettes = {
        "blue": {
            "background_top": ["#EDF6FC", "#071828"],
            "background_bottom": ["#D9ECF8", "#0A2A43"],
            "glow_primary": ["#3B8ED0", "#2E8BCB"],
            "glow_secondary": ["#67B7E1", "#1D6E9E"],
            "header_top": ["#DCEFFB", "#102B43"],
            "header_bottom": ["#C7E4F6", "#0D3957"],
            "header_border": ["#75B7DC", "#316B91"],
            "cat_ring": ["#2E8BCB", "#56B7E9"],
            "header_text": ["#102A3B", "#F3F9FD"],
            "header_muted": ["#456A82", "#B9D5E7"],
            "version_bg": ["#B9DCF0", "#123C58"],
            "version_text": ["#155B85", "#79D2FF"],
            "pill_bg": ["#C5E2F3", "#183D56"],
            "pill_text": ["#174B6B", "#D8F1FF"],
        },
        "dark-blue": {
            "background_top": ["#EAF1F8", "#050E1B"],
            "background_bottom": ["#D4E2F0", "#0B1E35"],
            "glow_primary": ["#3A7EBF", "#2C6AA3"],
            "glow_secondary": ["#527DA8", "#184C78"],
            "header_top": ["#D7E5F2", "#0C2037"],
            "header_bottom": ["#C4D9EA", "#102B49"],
            "header_border": ["#6E96BA", "#294E73"],
            "cat_ring": ["#315F8C", "#4A91CC"],
            "header_text": ["#14283A", "#F2F7FC"],
            "header_muted": ["#526B80", "#B4C7D9"],
            "version_bg": ["#BFD2E3", "#102B48"],
            "version_text": ["#274F75", "#86BFF0"],
            "pill_bg": ["#C8D9E8", "#182E47"],
            "pill_text": ["#294C6B", "#DCEBFA"],
        },
        "green": {
            "background_top": ["#EEF8F1", "#071B13"],
            "background_bottom": ["#DDF0E3", "#0C2B1E"],
            "glow_primary": ["#2FA572", "#2B8C62"],
            "glow_secondary": ["#71BF8F", "#3BAE78"],
            "header_top": ["#DDF2E5", "#123525"],
            "header_bottom": ["#CCE9D7", "#17432F"],
            "header_border": ["#70B78D", "#347557"],
            "cat_ring": ["#2FA572", "#61D49A"],
            "header_text": ["#153426", "#F2FBF6"],
            "header_muted": ["#4E7461", "#B9DCC9"],
            "version_bg": ["#C1E5CF", "#174532"],
            "version_text": ["#246D4A", "#7BE0AA"],
            "pill_bg": ["#CDEAD8", "#1C4936"],
            "pill_text": ["#255F44", "#DDF7E8"],
        },
    }

    data["ThemeName"] = {
        "blue": "Azul (Estándar)",
        "dark-blue": "Azul Profundo",
        "green": "Verde (Estándar)",
    }.get(theme_name, theme_name)
    data["XomacitoVisual"] = visual_palettes.get(theme_name, visual_palettes["blue"])
    data["CustomColors"] = {
        "DOWNLOAD_BTN": primary,
        "DOWNLOAD_BTN_HOVER": primary_hover,
        "DOWNLOAD_BTN_TEXT": button.get("text_color", ["white", "white"]),
        "ANALYZE_BTN": primary,
        "ANALYZE_BTN_HOVER": primary_hover,
        "ANALYZE_BTN_TEXT": button.get("text_color", ["white", "white"]),
        "PROCESS_BTN": primary,
        "PROCESS_BTN_HOVER": primary_hover,
        "PROCESS_BTN_TEXT": button.get("text_color", ["white", "white"]),
        "CANCEL_BTN": ["#DC4C5B", "#B82F3E"],
        "CANCEL_BTN_HOVER": ["#BF3545", "#8E2330"],
        "CANCEL_BTN_TEXT": ["white", "white"],
        "SECONDARY_BTN": ["#6E8496", "#40576A"],
        "SECONDARY_BTN_HOVER": ["#5B7183", "#33495B"],
        "SECONDARY_BTN_TEXT": ["white", "#F1F6FA"],
        "TERTIARY_BTN": primary,
        "TERTIARY_BTN_HOVER": primary_hover,
        "TERTIARY_BTN_TEXT": ["white", "white"],
        "QUATERNARY_BTN": surface,
        "QUATERNARY_BTN_HOVER": surface_border,
        "QUATERNARY_BTN_TEXT": text,
        "DND_BORDER": primary,
        "DND_BG": field,
        "DND_TEXT": primary,
        "SECTION_SUBTITLE": primary,
        "CONFIG_CARD_BG": surface,
        "CONFIG_CARD_BORDER": surface_border,
        "SCROLL_SURFACE": surface,
        "LISTBOX_BG": field,
        "LISTBOX_TEXT": text,
        "LISTBOX_SELECTED_BG": primary,
        "LISTBOX_SELECTED_TEXT": ["white", "white"],
        "CONSOLE_BG": field,
        "CONSOLE_TEXT": text,
        "STATUS_SUCCESS": ["#2E9B67", "#38A975"],
        "STATUS_ERROR": ["#D64555", "#C53A49"],
        "STATUS_WARNING": ["#D98A22", "#E3A13B"],
        "STATUS_PENDING": ["#6D7F8D", "#647685"],
        "SEPARATOR_COLOR": surface_border,
        "DISABLED_TEXT": ["#788896", "#8B9AA6"],
        "DISABLED_FG": surface_border,
    }
    return data


def _run_self_test() -> int:
    """Comprueba el runtime instalado sin crear una ventana de Tk."""
    if not FROZEN:
        return 0

    required_runtime_files = (
        INTERNAL_DIR / "_tcl_data" / "init.tcl",
        INTERNAL_DIR / "_tk_data" / "tk.tcl",
        INTERNAL_DIR / "bin" / "ffmpeg" / ("ffmpeg.exe" if os.name == "nt" else "ffmpeg"),
        INTERNAL_DIR / "bin" / "ytdlp" / "yt-dlp.zip",
    )
    return 0 if all(path.is_file() for path in required_runtime_files) else 1


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


def _run_main_window() -> int:
    import customtkinter as ctk

    settings = _settings()
    appearance = str(settings.get("appearance_mode", "Dark"))
    if appearance not in {"Dark", "Light", "System"}:
        appearance = "Dark"

    theme_path = _theme_path(settings)
    ctk.set_appearance_mode(appearance)
    theme_data = _load_custom_theme(ctk, theme_path)

    from src.gui.main_window import MainWindow

    window = MainWindow(
        project_root=str(PROJECT_ROOT),
        poppler_path=POPPLER_BIN_DIR,
        inkscape_path=str(PROJECT_ROOT / "bin" / "inkscape"),
        app_version=APP_VERSION,
        theme_data=theme_data,
        theme_warnings=[],
    )
    window.mainloop()
    return 0


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
