"""Refina las paletas integradas de Xomacito usando roles y contraste WCAG."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
THEMES_DIR = ROOT / "src" / "ui" / "themes"


@dataclass(frozen=True)
class ModePalette:
    canvas: str
    surface: str
    elevated: str
    border: str
    text: str
    muted: str
    primary: str
    primary_hover: str
    secondary: str
    tertiary: str


@dataclass(frozen=True)
class ThemePalette:
    name: str
    font: str
    light: ModePalette
    dark: ModePalette


def mode(*colors):
    return ModePalette(*colors)


THEMES = {
    "coffee_noir": ThemePalette("Coffee Noir", "Candara", mode("#FAF7F4", "#F1E9E3", "#FFFDFC", "#D5C1B5", "#2B211D", "#705D53", "#87503F", "#6D3E31", "#A85838", "#66544C"), mode("#120D0B", "#1E1512", "#2A1D18", "#593C32", "#F5EAE4", "#C8AEA2", "#C8795F", "#DB9276", "#D89B54", "#9C8278")),
    "dorado": ThemePalette("Dorado", "Segoe UI Variable Text", mode("#FAF8F1", "#F0ECDF", "#FFFEF8", "#D8C995", "#29271E", "#6B6550", "#806500", "#695200", "#416A63", "#67598A"), mode("#0F0F0D", "#1C1B16", "#29271E", "#5E5430", "#F7F3DF", "#C8BFA0", "#B29123", "#C9A93A", "#579486", "#8E78B0")),
    "forest_moss": ThemePalette("Forest Moss", "Candara", mode("#F6F8F2", "#E9EFE2", "#FDFEF9", "#BDCCAD", "#1F2A1A", "#5B6E50", "#466B36", "#35542A", "#7C5D22", "#506878"), mode("#0C100A", "#151C12", "#1E291A", "#405839", "#E9F2E4", "#AABE9F", "#5F8E4C", "#76A961", "#9B7A35", "#66889E")),
    "green": ThemePalette("Green", "Segoe UI Variable Text", mode("#F3F8F5", "#E4F0E9", "#FFFFFF", "#ACD0BB", "#173023", "#51705E", "#087A50", "#066440", "#1976A8", "#6555A9"), mode("#07110C", "#0D1E16", "#142A1F", "#295740", "#E5F5EC", "#A4C5B1", "#17865B", "#239E6D", "#247DA8", "#7564BA")),
    "midnight_ocean": ThemePalette("Midnight Ocean", "Segoe UI Variable Text", mode("#F4F8FC", "#E8F1FA", "#FFFFFF", "#B8CAE0", "#122033", "#50657C", "#006EB7", "#005B99", "#007F73", "#6155AE"), mode("#07111D", "#0E1D2D", "#14273B", "#2A4663", "#E8F2FC", "#A7BCD0", "#187AB8", "#2492D1", "#168B7C", "#7568C7")),
    "pink_diamond": ThemePalette("Pink Diamond", "Segoe UI Variable Text", mode("#FFF7FA", "#FBE9F0", "#FFFFFF", "#E8B9CA", "#3A1B27", "#7E5262", "#A52D62", "#87234F", "#7442A1", "#287384"), mode("#160B12", "#25101C", "#351628", "#71304D", "#FCEBF2", "#D3A2B5", "#B43D6D", "#CC4F82", "#8454AD", "#347F89")),
    "red": ThemePalette("Red", "Segoe UI Variable Text", mode("#FCF7F7", "#F5E6E6", "#FFFFFF", "#DDB8B8", "#351B1B", "#765353", "#A62B32", "#842128", "#925126", "#555B8A"), mode("#130A0B", "#211012", "#30171A", "#6A3035", "#FBEAEC", "#D2A4A8", "#B9363E", "#D14952", "#9C612E", "#6E73A8")),
    "shrek": ThemePalette("Shrek", "Segoe UI Variable Text", mode("#F8F8EE", "#ECECDA", "#FFFFF8", "#C8C79B", "#292A17", "#666744", "#5D700E", "#465600", "#815719", "#42695A"), mode("#0F1108", "#1A1E0D", "#252B13", "#4C5726", "#F1F4D8", "#C0C795", "#718D13", "#88A91E", "#996A25", "#4D8069")),
    "sunset_lavender": ThemePalette("Sunset Lavender", "Segoe UI Variable Text", mode("#F9F7FC", "#EFE8F7", "#FFFFFF", "#CDBCE1", "#2A2038", "#665673", "#6D4CB3", "#583B96", "#A94470", "#B65A2C"), mode("#110D18", "#1C1628", "#281F38", "#53416E", "#F3ECFC", "#BCA9D0", "#7955B7", "#916CCA", "#AD4E78", "#B85F35")),
    "tokyo": ThemePalette("Tokyo", "Bahnschrift", mode("#F5F6FA", "#E9EBF3", "#FFFFFF", "#BCC3D8", "#20263D", "#59617C", "#3B67B3", "#2F5595", "#70479A", "#1F747B"), mode("#151621", "#1E2030", "#282B40", "#414967", "#E8ECFF", "#A8B0D0", "#496FAF", "#5D83C4", "#7955A8", "#267D76")),
}


def rgb(color: str):
    value = color.lstrip("#")
    return tuple(int(value[index:index + 2], 16) for index in (0, 2, 4))


def hex_color(values):
    return "#" + "".join(f"{max(0, min(255, round(value))):02X}" for value in values)


def mix(first: str, second: str, second_weight: float):
    a, b = rgb(first), rgb(second)
    return hex_color(x + (y - x) * second_weight for x, y in zip(a, b))


def luminance(color: str):
    channels = []
    for channel in rgb(color):
        value = channel / 255
        channels.append(value / 12.92 if value <= 0.04045 else ((value + 0.055) / 1.055) ** 2.4)
    return 0.2126 * channels[0] + 0.7152 * channels[1] + 0.0722 * channels[2]


def contrast(first: str, second: str):
    light, dark = sorted((luminance(first), luminance(second)), reverse=True)
    return (light + 0.05) / (dark + 0.05)


def on_color(background: str):
    return max(("#FFFFFF", "#101418"), key=lambda candidate: contrast(candidate, background))


def ensure_contrast(foreground: str, background: str, minimum: float = 4.5):
    if contrast(foreground, background) >= minimum:
        return foreground
    target = max(("#FFFFFF", "#101418"), key=lambda candidate: contrast(candidate, background))
    for step in range(1, 21):
        candidate = mix(foreground, target, step / 20)
        if contrast(candidate, background) >= minimum:
            return candidate
    return target


def pairs(light: ModePalette, dark: ModePalette, attribute: str):
    return [getattr(light, attribute), getattr(dark, attribute)]


def set_role(data, section, key, values):
    data.setdefault(section, {})[key] = values


def refine(path: Path, palette: ThemePalette):
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    light, dark = palette.light, palette.dark
    dual = lambda attribute: pairs(light, dark, attribute)
    on_primary = [on_color(light.primary), on_color(dark.primary)]
    on_secondary = [on_color(light.secondary), on_color(dark.secondary)]
    on_tertiary = [on_color(light.tertiary), on_color(dark.tertiary)]
    neutral = [mix(light.surface, light.border, 0.46), mix(dark.surface, dark.border, 0.46)]
    neutral_hover = [mix(light.surface, light.border, 0.66), mix(dark.surface, dark.border, 0.66)]
    errors = ["#B4232C", "#ED6971"]
    successes = ["#257A47", "#63C98A"]
    warnings = ["#855800", "#E6B94F"]
    on_error = [on_color(value) for value in errors]
    on_warning = [on_color(value) for value in warnings]
    readable_primary = [ensure_contrast(light.primary, light.elevated), ensure_contrast(dark.primary, dark.surface)]

    instructions = data.setdefault("_INSTRUCCIONES_XOMACITO", {})
    instructions["VERSION"] = "5.2"
    instructions["ThemeName"] = palette.name
    data["ThemeName"] = palette.name

    custom = data.setdefault("CustomColors", {})
    custom.update({
        "DOWNLOAD_BTN": dual("primary"), "DOWNLOAD_BTN_HOVER": dual("primary_hover"), "DOWNLOAD_BTN_TEXT": on_primary,
        "ANALYZE_BTN": dual("secondary"), "ANALYZE_BTN_HOVER": [mix(light.secondary, "#000000", 0.16), mix(dark.secondary, "#FFFFFF", 0.14)], "ANALYZE_BTN_TEXT": on_secondary,
        "CANCEL_BTN": errors, "CANCEL_BTN_HOVER": [mix(errors[0], "#000000", 0.18), mix(errors[1], "#FFFFFF", 0.12)], "CANCEL_BTN_TEXT": on_error,
        "PROCESS_BTN": dual("tertiary"), "PROCESS_BTN_HOVER": [mix(light.tertiary, "#000000", 0.16), mix(dark.tertiary, "#FFFFFF", 0.14)], "PROCESS_BTN_TEXT": on_tertiary,
        "SECONDARY_BTN": neutral, "SECONDARY_BTN_HOVER": neutral_hover, "SECONDARY_BTN_TEXT": dual("text"),
        "TERTIARY_BTN": warnings, "TERTIARY_BTN_HOVER": [mix(warnings[0], "#000000", 0.16), mix(warnings[1], "#FFFFFF", 0.12)], "TERTIARY_BTN_TEXT": on_warning,
        "QUATERNARY_BTN": dual("elevated"), "QUATERNARY_BTN_HOVER": [mix(light.elevated, light.primary, 0.12), mix(dark.elevated, dark.primary, 0.18)], "QUATERNARY_BTN_TEXT": readable_primary,
        "DND_BORDER": dual("primary"), "DND_BG": dual("elevated"), "DND_TEXT": readable_primary,
        "STATUS_SUCCESS": successes, "STATUS_ERROR": errors, "STATUS_WARNING": warnings, "UPDATE_ALERT": warnings,
        "STATUS_PENDING": dual("muted"), "JOB_ACTION_ICON_COLOR": dual("text"), "JOB_CANCEL_ICON_COLOR": errors,
        "LISTBOX_BG": dual("elevated"), "LISTBOX_TEXT": dual("text"), "LISTBOX_SELECTED_BG": dual("primary"), "LISTBOX_SELECTED_TEXT": on_primary,
        "VIEWER_BG": dual("canvas"), "VIEWER_BORDER": dual("primary"), "SECTION_SUBTITLE": readable_primary,
        "CONFIG_CARD_BG": dual("surface"), "CONFIG_CARD_BORDER": dual("border"), "HUD_BG": dual("elevated"), "HUD_TEXT": dual("text"),
        "SEPARATOR_COLOR": dual("border"), "OPTIONS_PANEL_BG": dual("surface"), "TRANSPARENCY_GRID_1": dual("surface"), "TRANSPARENCY_GRID_2": dual("elevated"),
        "CONSOLE_BG": ["#FFFFFF", mix(dark.canvas, "#000000", 0.35)], "CONSOLE_TEXT": dual("text"),
    })

    set_role(data, "CTk", "fg_color", dual("canvas")); set_role(data, "CTkToplevel", "fg_color", dual("canvas"))
    for key, values in {"fg_color": dual("surface"), "top_fg_color": dual("elevated"), "border_color": dual("border")}.items(): set_role(data, "CTkFrame", key, values)
    for key, values in {"fg_color": dual("primary"), "hover_color": dual("primary_hover"), "text_color": on_primary, "border_color": dual("border")}.items(): set_role(data, "CTkButton", key, values)
    set_role(data, "CTkLabel", "text_color", dual("text"))
    for section in ("CTkEntry", "CTkComboBox"):
        set_role(data, section, "fg_color", dual("elevated")); set_role(data, section, "border_color", dual("border")); set_role(data, section, "text_color", dual("text")); set_role(data, section, "placeholder_text_color", dual("muted"))
    for section in ("CTkCheckBox", "CTkRadioButton"):
        set_role(data, section, "fg_color", dual("primary")); set_role(data, section, "border_color", dual("primary")); set_role(data, section, "hover_color", dual("primary_hover")); set_role(data, section, "text_color", dual("text"))
    set_role(data, "CTkCheckBox", "checkmark_color", on_primary)
    for key, values in {"fg_color": neutral, "progress_color": dual("primary"), "button_color": dual("elevated"), "button_hover_color": dual("primary_hover"), "text_color": dual("text")}.items(): set_role(data, "CTkSwitch", key, values)
    for section in ("CTkProgressBar", "CTkSlider"):
        set_role(data, section, "fg_color", neutral); set_role(data, section, "progress_color", dual("primary"))
    set_role(data, "CTkSlider", "button_color", dual("primary")); set_role(data, "CTkSlider", "button_hover_color", dual("primary_hover"))
    for key, values in {"fg_color": dual("primary"), "button_color": dual("primary_hover"), "button_hover_color": [mix(light.primary_hover, "#000000", 0.1), mix(dark.primary_hover, "#FFFFFF", 0.1)], "text_color": on_primary}.items(): set_role(data, "CTkOptionMenu", key, values)
    set_role(data, "CTkComboBox", "button_color", dual("primary")); set_role(data, "CTkComboBox", "button_hover_color", dual("primary_hover"))
    set_role(data, "CTkScrollbar", "button_color", dual("border")); set_role(data, "CTkScrollbar", "button_hover_color", dual("primary"))

    segment_selected = [mix(light.elevated, light.primary, 0.34), mix(dark.surface, dark.primary, 0.55)]
    segment_unselected = [mix(light.elevated, light.primary, 0.08), dark.surface]
    for key, values in {"fg_color": segment_unselected, "selected_color": segment_selected, "selected_hover_color": [mix(segment_selected[0], light.primary, 0.12), mix(segment_selected[1], dark.primary_hover, 0.15)], "unselected_color": segment_unselected, "unselected_hover_color": [mix(segment_unselected[0], light.primary, 0.1), mix(segment_unselected[1], dark.primary, 0.15)], "text_color": [light.text, dark.text]}.items(): set_role(data, "CTkSegmentedButton", key, values)
    for key, values in {"fg_color": dual("elevated"), "border_color": dual("border"), "text_color": dual("text"), "scrollbar_button_color": dual("border"), "scrollbar_button_hover_color": dual("primary")}.items(): set_role(data, "CTkTextbox", key, values)
    set_role(data, "CTkScrollableFrame", "label_fg_color", dual("surface"))
    for key, values in {"fg_color": dual("elevated"), "hover_color": [mix(light.elevated, light.primary, 0.12), mix(dark.elevated, dark.primary, 0.18)], "text_color": dual("text")}.items(): set_role(data, "DropdownMenu", key, values)

    data["CTkFont"] = {"Windows": {"family": palette.font, "size": 14, "weight": "normal"}}
    header_color = lambda item, accent, dark_mode: mix(item.canvas, accent, 0.24 if dark_mode else 0.72)
    light_header_top, light_header_bottom = header_color(light, light.primary, False), header_color(light, light.secondary, False)
    dark_header_top, dark_header_bottom = header_color(dark, dark.primary, True), header_color(dark, dark.secondary, True)
    light_version_bg, dark_version_bg = mix(light_header_top, "#000000", 0.22), mix(dark.surface, dark.secondary, 0.34)
    light_pill_bg, dark_pill_bg = mix(light_header_bottom, "#000000", 0.18), mix(dark.surface, dark.primary, 0.36)
    data["XomacitoVisual"] = {
        "background_top": [mix(light.canvas, light.primary, 0.06), mix(dark.canvas, dark.primary, 0.08)],
        "background_bottom": [mix(light.canvas, light.secondary, 0.11), mix(dark.canvas, dark.secondary, 0.14)],
        "glow_primary": dual("primary"), "glow_secondary": dual("secondary"),
        "header_top": [light_header_top, dark_header_top], "header_bottom": [light_header_bottom, dark_header_bottom],
        "header_border": dual("border"), "cat_ring": dual("secondary"),
        "header_text": [on_color(light_header_top), dark.text], "header_muted": [on_color(light_header_bottom), dark.muted],
        "version_bg": [light_version_bg, dark_version_bg], "version_text": [on_color(light_version_bg), on_color(dark_version_bg)],
        "pill_bg": [light_pill_bg, dark_pill_bg], "pill_text": [on_color(light_pill_bg), on_color(dark_pill_bg)],
        "font_family": palette.font,
    }
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def main():
    for stem, palette in THEMES.items():
        path = THEMES_DIR / f"{stem}.json"
        if not path.exists(): raise FileNotFoundError(path)
        refine(path, palette)
        print(f"Refinado: {palette.name}")


if __name__ == "__main__":
    main()
