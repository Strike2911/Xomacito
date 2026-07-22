from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from .daily_icon import CAT_COUNT


RARITY_COLORS = {
    1: "#A8B0BC",
    2: "#65DD91",
    3: "#50BFFF",
    4: "#B06CFF",
    5: "#FFD75E",
}
ROLL_WEIGHTS = {1: 48, 2: 28, 3: 15, 4: 7, 5: 2}


@dataclass(frozen=True, slots=True)
class CatDefinition:
    id: str
    name: str
    rarity: int
    image_path: Path
    avatar_path: Path
    original_file: str = ""

    @property
    def rarity_color(self) -> str:
        return RARITY_COLORS[self.rarity]


def load_cat_catalog(project_root: str | Path) -> list[CatDefinition]:
    root = Path(project_root)
    collection_dir = root / "assets" / "cat-collection"
    try:
        raw = json.loads((collection_dir / "catalog.json").read_text(encoding="utf-8-sig"))
    except (OSError, ValueError, TypeError):
        raw = {}

    cats: list[CatDefinition] = []
    seen: set[str] = set()
    for item in raw.get("cats", []) if isinstance(raw, dict) else []:
        if not isinstance(item, dict):
            continue
        cat_id = str(item.get("id") or "").strip()
        image_path = collection_dir / str(item.get("image") or "")
        avatar_path = collection_dir / str(item.get("avatar") or item.get("image") or "")
        if not cat_id or cat_id in seen or not image_path.is_file() or not avatar_path.is_file():
            continue
        try:
            rarity = max(1, min(5, int(item.get("rarity", 1))))
        except (TypeError, ValueError):
            rarity = 1
        seen.add(cat_id)
        cats.append(
            CatDefinition(
                id=cat_id,
                name=str(item.get("name") or image_path.stem).strip(),
                rarity=rarity,
                image_path=image_path,
                avatar_path=avatar_path,
                original_file=str(item.get("originalFile") or ""),
            )
        )

    if cats:
        return sorted(cats, key=lambda cat: (-cat.rarity, cat.name.casefold()))

    # Respaldo para instalaciones antiguas o una copia de desarrollo incompleta.
    icon_dir = root / "assets" / "cat-icons"
    for number in range(1, CAT_COUNT + 1):
        path = icon_dir / f"cat-{number:02d}-ui.png"
        if path.is_file():
            cats.append(
                CatDefinition(
                    id=f"classic-{number:02d}",
                    name=f"Gatito clásico {number:02d}",
                    rarity=min(5, 1 + (number - 1) // 2),
                    image_path=path,
                    avatar_path=path,
                    original_file=path.name,
                )
            )
    return cats


def starter_cat(catalog: list[CatDefinition]) -> CatDefinition:
    if not catalog:
        raise RuntimeError("Xomacito no encontró imágenes para la colección de gatos.")
    preferred = next(
        (cat for cat in catalog if cat.name.casefold() == "gatito pensativo"),
        None,
    )
    return preferred or min(catalog, key=lambda cat: (cat.rarity, cat.name.casefold()))
