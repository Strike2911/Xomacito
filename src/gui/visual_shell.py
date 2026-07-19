"""Elementos de identidad visual dibujados sin alterar los widgets funcionales."""

from __future__ import annotations

import os
import re
import tkinter as tk
from functools import lru_cache

from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageOps, ImageTk


FONT_FILES = {
    "Segoe UI": ("segoeui.ttf", "segoeuib.ttf"),
    "Segoe UI Variable Text": ("SegUIVar.ttf", "segoeuib.ttf"),
    "Candara": ("Candara.ttf", "Candarab.ttf"),
    "Bahnschrift": ("bahnschrift.ttf", "bahnschrift.ttf"),
}


@lru_cache(maxsize=32)
def _font(size: int, bold: bool = False, family: str = "Segoe UI Variable Text"):
    regular, bold_file = FONT_FILES.get(family, FONT_FILES["Segoe UI"])
    names = (bold_file, "segoeuib.ttf") if bold else (regular, "segoeui.ttf")
    for name in names:
        try:
            font_path = os.path.join(os.environ.get("WINDIR", r"C:\Windows"), "Fonts", name)
            return ImageFont.truetype(font_path, size=size)
        except OSError:
            continue
    return ImageFont.load_default()


def _theme_value(theme_data, key, default):
    try:
        import customtkinter as ctk
        dark_mode = ctk.get_appearance_mode() == "Dark"
    except Exception:
        dark_mode = True
    visual = (theme_data or {}).get("XomacitoVisual", {})
    value = visual.get(key, _derived_visual(theme_data or {}, dark_mode).get(key, default))
    if isinstance(value, list):
        return value[1] if dark_mode else value[0]
    return value


def _rgb(color):
    value = str(color).strip()
    hex_value = value.lstrip("#")
    if re.fullmatch(r"[0-9a-fA-F]{6}", hex_value):
        return tuple(int(hex_value[index:index + 2], 16) for index in (0, 2, 4))

    gray_match = re.fullmatch(r"gr(?:a|e)y(\d{1,3})", value, re.IGNORECASE)
    if gray_match:
        level = max(0, min(100, int(gray_match.group(1))))
        channel = round(255 * level / 100)
        return (channel, channel, channel)

    named = {
        "black": (0, 0, 0),
        "white": (255, 255, 255),
        "gray": (128, 128, 128),
        "grey": (128, 128, 128),
    }
    return named.get(value.lower(), (7, 16, 31))


def _hex(values):
    return "#" + "".join(f"{max(0, min(255, round(value))):02X}" for value in values)


def _blend(first, second, second_weight):
    return _hex(a + (b - a) * second_weight for a, b in zip(_rgb(first), _rgb(second)))


def _select(value, dark_mode, default):
    if isinstance(value, list) and len(value) >= 2:
        return value[1] if dark_mode else value[0]
    return value if isinstance(value, str) and value.startswith("#") else default


def _derived_visual(theme_data, dark_mode):
    canvas_default = "#07111D" if dark_mode else "#F4F8FC"
    surface_default = "#0E1D2D" if dark_mode else "#E8F1FA"
    primary_default = "#187AB8" if dark_mode else "#006EB7"
    canvas = _select(theme_data.get("CTk", {}).get("fg_color"), dark_mode, canvas_default)
    surface = _select(theme_data.get("CTkFrame", {}).get("fg_color"), dark_mode, surface_default)
    primary = _select(theme_data.get("CTkButton", {}).get("fg_color"), dark_mode, primary_default)
    secondary = _select(theme_data.get("CustomColors", {}).get("ANALYZE_BTN"), dark_mode, primary)
    text = _select(theme_data.get("CTkLabel", {}).get("text_color"), dark_mode, "#E8F2FC" if dark_mode else "#122033")
    muted = _blend(text, canvas, 0.42)
    font_data = theme_data.get("CTkFont", {})
    if "Windows" in font_data:
        font_data = font_data["Windows"]
    family = font_data.get("family", "Segoe UI Variable Text")
    header_top = _blend(canvas, primary, 0.24 if dark_mode else 0.72)
    header_bottom = _blend(canvas, secondary, 0.28 if dark_mode else 0.72)
    return {
        "background_top": _blend(canvas, primary, 0.08 if dark_mode else 0.06),
        "background_bottom": _blend(canvas, secondary, 0.14 if dark_mode else 0.11),
        "glow_primary": primary,
        "glow_secondary": secondary,
        "header_top": header_top,
        "header_bottom": header_bottom,
        "header_border": _blend(surface, primary, 0.48),
        "cat_ring": secondary,
        "header_text": text,
        "header_muted": muted,
        "version_bg": _blend(surface, secondary, 0.32),
        "version_text": text,
        "pill_bg": _blend(surface, primary, 0.34),
        "pill_text": text,
        "font_family": family,
    }


def _vertical_gradient(size, top, bottom):
    width, height = size
    denominator = max(height - 1, 1)
    colors = [
        tuple(round(a + (b - a) * (y / denominator)) for a, b in zip(top, bottom))
        for y in range(height)
    ]
    column = Image.new("RGB", (1, height))
    column.putdata(colors)
    return column.resize((width, height), Image.Resampling.BILINEAR)


class GradientBackdrop(tk.Canvas):
    """Fondo azul noche con luces suaves; se redibuja solo al cambiar tamaño."""

    def __init__(self, master, theme_data=None):
        super().__init__(master, highlightthickness=0, bd=0, bg="#07101F")
        self.theme_data = theme_data or {}
        self._image = None
        self._pending = None
        self._last_size = None
        self.bind("<Configure>", self._schedule_render)

    def update_theme(self, theme_data):
        self.theme_data = theme_data or {}
        self._last_size = None
        self.configure(bg=_theme_value(self.theme_data, "background_top", "#07101F"))
        self._schedule_render()

    def _schedule_render(self, event=None):
        if self._pending:
            self.after_cancel(self._pending)
        self._pending = self.after(90, self._render)

    def _render(self):
        self._pending = None
        width, height = max(self.winfo_width(), 2), max(self.winfo_height(), 2)
        if self._last_size == (width, height):
            return
        self._last_size = (width, height)
        top = _rgb(_theme_value(self.theme_data, "background_top", "#050D1B"))
        bottom = _rgb(_theme_value(self.theme_data, "background_bottom", "#0F162A"))
        primary = _rgb(_theme_value(self.theme_data, "glow_primary", "#7356EB"))
        secondary = _rgb(_theme_value(self.theme_data, "glow_secondary", "#28CCBE"))

        # Las luces son deliberadamente suaves, así que se calculan a 1/4 de
        # resolución y se amplían. El coste del blur cae drásticamente sin una
        # diferencia visual perceptible.
        render_width = max(64, width // 4)
        render_height = max(64, height // 4)
        image = _vertical_gradient((render_width, render_height), top, bottom).convert("RGBA")

        glow = Image.new("RGBA", image.size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(glow)
        radius = max(render_width, render_height) // 2
        draw.ellipse(
            (render_width - radius, -radius // 2, render_width + radius // 2, radius),
            fill=(*primary, 62),
        )
        draw.ellipse(
            (-radius // 2, render_height - radius, radius, render_height + radius // 2),
            fill=(*secondary, 44),
        )
        glow = glow.filter(ImageFilter.GaussianBlur(max(15, radius // 4)))
        image = Image.alpha_composite(image, glow)
        image = image.resize((width, height), Image.Resampling.BILINEAR)

        self._image = ImageTk.PhotoImage(image)
        self.delete("all")
        self.create_image(0, 0, image=self._image, anchor="nw")


class DailyBrandHeader(tk.Canvas):
    """Encabezado de marca con el gatito elegido para el día actual."""

    def __init__(self, master, daily_cat, app_version: str, theme_data=None):
        super().__init__(master, height=78, highlightthickness=0, bd=0, bg="#07101F")
        self.daily_cat = daily_cat
        self.app_version = app_version
        self.theme_data = theme_data or {}
        self._image = None
        self._pending = None
        self._last_size = None
        self._daily_cat_image = None
        self.bind("<Configure>", self._schedule_render)

    def update_theme(self, theme_data):
        self.theme_data = theme_data or {}
        self._last_size = None
        self.configure(bg=_theme_value(self.theme_data, "background_top", "#07101F"))
        self._schedule_render()

    def _schedule_render(self, event=None):
        if self._pending:
            self.after_cancel(self._pending)
        self._pending = self.after(40, self._render)

    def _render(self):
        self._pending = None
        width, height = max(self.winfo_width(), 640), max(self.winfo_height(), 78)
        if self._last_size == (width, height):
            return
        self._last_size = (width, height)
        header_top = _rgb(_theme_value(self.theme_data, "header_top", "#141E36"))
        header_bottom = _rgb(_theme_value(self.theme_data, "header_bottom", "#0F2C37"))
        header_glow = _rgb(_theme_value(self.theme_data, "glow_primary", "#7453E1"))
        border = _rgb(_theme_value(self.theme_data, "header_border", "#445B80"))
        cat_ring = _rgb(_theme_value(self.theme_data, "cat_ring", "#5DE0D2"))
        header_text = _rgb(_theme_value(self.theme_data, "header_text", "#F8FAFC"))
        header_muted = _rgb(_theme_value(self.theme_data, "header_muted", "#B8C7DD"))
        version_bg = _rgb(_theme_value(self.theme_data, "version_bg", "#0F373D"))
        version_text_color = _rgb(_theme_value(self.theme_data, "version_text", "#5EEAD4"))
        pill_bg = _rgb(_theme_value(self.theme_data, "pill_bg", "#33295B"))
        pill_text_color = _rgb(_theme_value(self.theme_data, "pill_text", "#E1D8FF"))
        family = _theme_value(self.theme_data, "font_family", "Segoe UI Variable Text")
        render_width = max(320, width // 2)
        render_height = max(39, height // 2)
        panel = _vertical_gradient((render_width, render_height), header_top, header_bottom).convert("RGBA")
        overlay = Image.new("RGBA", panel.size, (0, 0, 0, 0))
        overlay_draw = ImageDraw.Draw(overlay)
        overlay_draw.ellipse(
            (render_width - 210, -90, render_width + 40, 120),
            fill=(*header_glow, 58),
        )
        overlay = overlay.filter(ImageFilter.GaussianBlur(50))
        panel = Image.alpha_composite(panel, overlay)
        panel = panel.resize((width, height), Image.Resampling.BILINEAR)

        rounded_mask = Image.new("L", panel.size, 0)
        ImageDraw.Draw(rounded_mask).rounded_rectangle((1, 1, width - 2, height - 2), radius=16, fill=255)
        background = Image.new("RGBA", panel.size, (*header_top, 255))
        background.paste(panel, (0, 0), rounded_mask)
        draw = ImageDraw.Draw(background)
        draw.rounded_rectangle((1, 1, width - 2, height - 2), radius=16, outline=(*border, 210), width=1)

        if self.daily_cat.png_path.exists():
            if self._daily_cat_image is None:
                with Image.open(self.daily_cat.png_path) as source:
                    self._daily_cat_image = ImageOps.fit(
                        source.convert("RGB"),
                        (58, 58),
                        method=Image.Resampling.LANCZOS,
                    )
            cat = self._daily_cat_image
            cat_mask = Image.new("L", cat.size, 0)
            ImageDraw.Draw(cat_mask).ellipse((0, 0, 57, 57), fill=255)
            draw.ellipse((12, 8, 74, 70), fill=(*cat_ring, 255))
            background.paste(cat, (14, 10), cat_mask)

        draw.text((88, 14), "XOMACITO", font=_font(21, bold=True, family=family), fill=header_text)
        draw.text(
            (88, 42),
            "Descarga, convierte y prepara contenido",
            font=_font(12, family=family),
            fill=header_muted,
        )

        pill_text = f"GATITO DEL DÍA  {self.daily_cat.number}/8"
        pill_font = _font(11, bold=True, family=family)
        pill_box = draw.textbbox((0, 0), pill_text, font=pill_font)
        pill_width = pill_box[2] - pill_box[0] + 22
        version_text = f"MOTOR {self.app_version}"
        version_font = _font(10, bold=True, family=family)
        version_box = draw.textbbox((0, 0), version_text, font=version_font)
        version_width = version_box[2] - version_box[0] + 20
        right = width - 14
        draw.rounded_rectangle((right - version_width, 13, right, 36), radius=11, fill=(*version_bg, 235))
        draw.text((right - version_width + 10, 18), version_text, font=version_font, fill=version_text_color)
        draw.rounded_rectangle(
            (right - pill_width, 42, right, 66),
            radius=12,
            fill=(*pill_bg, 225),
            outline=(*border, 190),
        )
        draw.text((right - pill_width + 11, 47), pill_text, font=pill_font, fill=pill_text_color)

        self._image = ImageTk.PhotoImage(background)
        self.delete("all")
        self.create_image(0, 0, image=self._image, anchor="nw")
