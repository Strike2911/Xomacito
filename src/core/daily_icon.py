"""Selección determinista del gatito diario de Xomacito."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from pathlib import Path
import sys


CAT_COUNT = 8


@dataclass(frozen=True)
class DailyCat:
    number: int
    png_path: Path
    ico_path: Path
    ui_path: Path


def daily_cat_number(day: date | None = None) -> int:
    """Devuelve un número estable del 1 al 8 y avanza uno cada día."""
    selected_day = day or date.today()
    return ((selected_day.toordinal() - 1) % CAT_COUNT) + 1


def _resource_roots(project_root: str | Path | None = None):
    if project_root:
        root = Path(project_root).resolve()
        yield root
        yield root.parent
    bundle_root = getattr(sys, "_MEIPASS", None)
    if bundle_root:
        yield Path(bundle_root)
    if getattr(sys, "frozen", False):
        executable_root = Path(sys.executable).resolve().parent
        yield executable_root
        yield executable_root.parent
    yield Path(__file__).resolve().parents[2]


def daily_cat_assets(
    project_root: str | Path | None = None,
    day: date | None = None,
) -> DailyCat:
    number = daily_cat_number(day)
    for root in dict.fromkeys(_resource_roots(project_root)):
        folder = root / "assets" / "cat-icons"
        png_path = folder / f"cat-{number:02d}.png"
        ico_path = folder / f"cat-{number:02d}.ico"
        ui_path = folder / f"cat-{number:02d}-ui.png"
        if png_path.exists() and ico_path.exists():
            return DailyCat(number, png_path, ico_path, ui_path if ui_path.exists() else png_path)
    fallback_root = Path(project_root or Path.cwd())
    folder = fallback_root / "assets" / "cat-icons"
    png_path = folder / f"cat-{number:02d}.png"
    ui_path = folder / f"cat-{number:02d}-ui.png"
    return DailyCat(number, png_path, folder / f"cat-{number:02d}.ico", ui_path if ui_path.exists() else png_path)
