from __future__ import annotations

import json
from pathlib import Path

from PySide6.QtCore import QObject, Property, Signal, Slot
from PySide6.QtGui import QColor, QGuiApplication, QPalette

from .settings_store import SettingsStore


FALLBACK_DARK = {
    "background": "#061522",
    "backgroundAlt": "#082438",
    "surface": "#0D2D43",
    "surfaceRaised": "#123B57",
    "surfaceSoft": "#0B263A",
    "border": "#235D7C",
    "borderStrong": "#2D87AD",
    "primary": "#20C9E8",
    "primaryHover": "#55DCF2",
    "primaryPressed": "#1499BC",
    "accent": "#A6EE4D",
    "text": "#F2F8FC",
    "textMuted": "#A7C5D5",
    "textDim": "#6F99AF",
    "success": "#78DA73",
    "warning": "#F2B84B",
    "error": "#FF746A",
    "shadow": "#8000060A",
    "scrim": "#B0000911",
}

FALLBACK_LIGHT = {
    "background": "#EAF6FC",
    "backgroundAlt": "#D9EEF8",
    "surface": "#F8FCFE",
    "surfaceRaised": "#FFFFFF",
    "surfaceSoft": "#DDEFF7",
    "border": "#A8D2E4",
    "borderStrong": "#4D9EBE",
    "primary": "#087DA3",
    "primaryHover": "#05698A",
    "primaryPressed": "#045673",
    "accent": "#4D8D13",
    "text": "#102B3A",
    "textMuted": "#456B7E",
    "textDim": "#688899",
    "success": "#287A45",
    "warning": "#A96300",
    "error": "#B42318",
    "shadow": "#30072130",
    "scrim": "#660B1D29",
}

LEGACY_THEME_ALIASES = {
    "blue": "midnight_ocean",
    "dark-blue": "midnight_ocean",
    "green": "forest_moss",
}


def _pick(value, dark: bool, fallback: str) -> str:
    if isinstance(value, (list, tuple)) and value:
        value = value[1 if dark and len(value) > 1 else 0]
    if isinstance(value, str) and QColor(value).isValid():
        return QColor(value).name(QColor.HexArgb if QColor(value).alpha() < 255 else QColor.HexRgb)
    return fallback


def _mix(first: str, second: str, amount: float) -> str:
    a, b = QColor(first), QColor(second)
    amount = max(0.0, min(1.0, amount))
    return QColor.fromRgbF(
        a.redF() * (1 - amount) + b.redF() * amount,
        a.greenF() * (1 - amount) + b.greenF() * amount,
        a.blueF() * (1 - amount) + b.blueF() * amount,
        a.alphaF() * (1 - amount) + b.alphaF() * amount,
    ).name(QColor.HexArgb)


class ThemeController(QObject):
    colorsChanged = Signal()
    appearanceChanged = Signal()
    themeNameChanged = Signal()
    availableThemesChanged = Signal()

    def __init__(self, project_root: str | Path, settings: SettingsStore, parent=None):
        super().__init__(parent)
        self.project_root = Path(project_root)
        self.settings = settings
        self.builtin_dir = self.project_root / "src" / "ui" / "themes"
        self._appearance = str(settings.get("appearance_mode", "Dark"))
        requested_theme = str(settings.get("selected_theme_accent", "midnight_ocean"))
        self._theme_name = self._normalized_theme_name(requested_theme)
        if self._theme_name != requested_theme:
            self.settings.set("selected_theme_accent", self._theme_name)
        self._colors: dict[str, str] = {}
        self.reload()

    def _normalized_theme_name(self, name: str) -> str:
        candidate = LEGACY_THEME_ALIASES.get(str(name).strip(), str(name).strip())
        personal = self.settings.themes_dir / f"{candidate}.json"
        builtin = self.builtin_dir / f"{candidate}.json"
        return candidate if personal.is_file() or builtin.is_file() else "midnight_ocean"

    @Property("QVariantMap", notify=colorsChanged)
    def colors(self):
        return self._colors

    @Property(str, notify=appearanceChanged)
    def appearance(self):
        return self._appearance

    @Property(str, notify=themeNameChanged)
    def themeName(self):
        return self._theme_name

    @Property("QStringList", notify=availableThemesChanged)
    def availableThemes(self):
        names = {path.stem for path in self.builtin_dir.glob("*.json")}
        names.update(path.stem for path in self.settings.themes_dir.glob("*.json"))
        return sorted(names, key=str.casefold)

    def _is_dark(self) -> bool:
        if self._appearance == "System":
            return QGuiApplication.palette().color(QPalette.Window).lightness() < 128
        return self._appearance != "Light"

    def _theme_path(self) -> Path:
        personal = self.settings.themes_dir / f"{self._theme_name}.json"
        builtin = self.builtin_dir / f"{self._theme_name}.json"
        fallback = self.builtin_dir / "midnight_ocean.json"
        return personal if personal.is_file() else builtin if builtin.is_file() else fallback

    @Slot()
    def reload(self):
        dark = self._is_dark()
        fallback = FALLBACK_DARK if dark else FALLBACK_LIGHT
        try:
            raw = json.loads(self._theme_path().read_text(encoding="utf-8-sig"))
        except (OSError, ValueError):
            raw = {}
        visual = raw.get("XomacitoVisual", {}) if isinstance(raw, dict) else {}
        custom = raw.get("CustomColors", {}) if isinstance(raw, dict) else {}
        button = raw.get("CTkButton", {}) if isinstance(raw, dict) else {}
        frame = raw.get("CTkFrame", {}) if isinstance(raw, dict) else {}
        entry = raw.get("CTkEntry", {}) if isinstance(raw, dict) else {}

        background = _pick(visual.get("background_top"), dark, fallback["background"])
        background_alt = _pick(visual.get("background_bottom"), dark, fallback["backgroundAlt"])
        surface = _pick(visual.get("header_top") or frame.get("fg_color"), dark, fallback["surface"])
        raised = _pick(visual.get("header_bottom"), dark, fallback["surfaceRaised"])
        border = _pick(visual.get("header_border"), dark, fallback["border"])
        primary = _pick(custom.get("DOWNLOAD_BTN") or button.get("fg_color"), dark, fallback["primary"])
        hover = _pick(custom.get("DOWNLOAD_BTN_HOVER") or button.get("hover_color"), dark, fallback["primaryHover"])
        field = _pick(entry.get("fg_color"), dark, _mix(background, surface, 0.55))

        self._colors = {
            **fallback,
            "background": background,
            "backgroundAlt": background_alt,
            "surface": surface,
            "surfaceRaised": raised,
            "surfaceSoft": field,
            "border": border,
            "borderStrong": _mix(border, primary, 0.55),
            "primary": primary,
            "primaryHover": hover,
            "primaryPressed": _mix(primary, background, 0.28),
            "accent": _pick(visual.get("glow_secondary"), dark, fallback["accent"]),
            "text": _pick(visual.get("header_text"), dark, fallback["text"]),
            "textMuted": _pick(visual.get("header_muted"), dark, fallback["textMuted"]),
            "textDim": _mix(_pick(visual.get("header_muted"), dark, fallback["textMuted"]), background, 0.28),
            "success": _pick(custom.get("STATUS_SUCCESS"), dark, fallback["success"]),
            "warning": _pick(custom.get("STATUS_WARNING"), dark, fallback["warning"]),
            "error": _pick(custom.get("STATUS_ERROR"), dark, fallback["error"]),
        }
        self.colorsChanged.emit()

    @Slot(str)
    def setAppearance(self, appearance: str):
        if appearance not in {"Dark", "Light", "System"} or appearance == self._appearance:
            return
        self._appearance = appearance
        self.settings.set("appearance_mode", appearance)
        self.appearanceChanged.emit()
        self.reload()

    @Slot(str)
    def setTheme(self, name: str):
        name = self._normalized_theme_name(name)
        if name == self._theme_name:
            return
        self._theme_name = name
        self.settings.update({"selected_theme_accent": name, "theme_selection_explicit": True})
        self.themeNameChanged.emit()
        self.reload()
