from __future__ import annotations

import json
import hashlib
from dataclasses import dataclass
from pathlib import Path

from .daily_icon import CAT_COUNT


RARITY_COLORS = {
    1: "#A8B0BC",
    2: "#65DD91",
    3: "#50BFFF",
    4: "#B06CFF",
    5: "#FFD75E",
    6: "#FF5FE7",
}
ROLL_WEIGHTS = {1: 48, 2: 28, 3: 15, 4: 7, 5: 1.8, 6: 0.2}
RARITY_NAMES = {1: "Común", 2: "Peculiar", 3: "Raro", 4: "Épico", 5: "Legendario", 6: "Mítico"}
DOWNLOAD_REWARD_CENTS = 100
ECONOMY_EPOCH = 1
BOXES = (
    {"id": "daily", "name": "Regalo diario", "priceCents": 0, "color": "#65DD91", "weights": ROLL_WEIGHTS},
    {"id": "basic", "name": "Caja callejera", "priceCents": 100, "color": "#50BFFF", "weights": ROLL_WEIGHTS},
    {"id": "rare", "name": "Caja estelar", "priceCents": 500, "color": "#B06CFF", "weights": {2: 15, 3: 35, 4: 30, 5: 17, 6: 3}},
    {"id": "mythic", "name": "Caja celestial", "priceCents": 1500, "color": "#FFD75E", "weights": {3: 10, 4: 25, 5: 45, 6: 20}},
)


def money(cents: int) -> str:
    return f"${cents / 100:.2f}"


def economy_snapshot(state: dict) -> dict:
    """Normalize legacy tickets once, keeping the wallet and inventory atomic."""
    def number(value):
        try:
            return max(0, int(value or 0))
        except (ValueError, TypeError):
            return 0
    modern = isinstance(state.get("inventory"), dict) and "walletCents" in state
    duplicates = state.get("duplicates", {})
    inventory = state["inventory"] if modern else {
        str(cat_id): 1 + number(duplicates.get(cat_id, 0))
        for cat_id in state.get("unlockedIds", [])
    }
    return {
        "economyEpoch": number(state.get("economyEpoch")),
        "resetCreditCents": number(state.get("resetCreditCents")),
        "liquidatedInventory": dict(state.get("liquidatedInventory") or {}),
        "walletCents": number(state.get("walletCents")) if modern else number(state.get("earnedRolls")) * DOWNLOAD_REWARD_CENTS,
        "inventory": {str(key): number(value) for key, value in inventory.items()},
        "economyRevision": number(state.get("economyRevision", state.get("rollBalanceRevision", number(state.get("totalDownloads")) + number(state.get("totalRolls"))))),
        "economyUpdatedAt": number(state.get("economyUpdatedAt")),
    }


def merge_economy(local: dict, remote: dict) -> dict:
    """An older collection must never resurrect spent money or sold copies."""
    snapshots = [economy_snapshot(local), economy_snapshot(remote)]
    def rank(value):
        # Stable tie break makes the merge commutative across devices.
        digest = hashlib.sha256(json.dumps(value, sort_keys=True).encode()).hexdigest()
        return value["economyEpoch"], value["economyRevision"], value["economyUpdatedAt"], digest
    return max(snapshots, key=rank)


def reset_economy(state: dict, catalog: list) -> dict:
    """Sell the pre-season stock once; retain download history and existing cash."""
    current = economy_snapshot(state)
    if current["economyEpoch"] >= ECONOMY_EPOCH:
        return dict(state)
    prices = {cat.id: cat.price_cents for cat in catalog}
    sold = {key: quantity for key, quantity in current["inventory"].items()
            if key in prices and quantity > 0}
    credit = sum(prices[key] * quantity for key, quantity in sold.items())
    starter = starter_cat(catalog)
    stock = {cat.id: 0 for cat in catalog}
    stock[starter.id] = 1  # A free base companion after liquidating every old copy.
    return {**state, **current, "schema": 7, "economyEpoch": ECONOMY_EPOCH,
            "resetCreditCents": credit, "liquidatedInventory": sold,
            "walletCents": current["walletCents"] + credit,
            "inventory": stock, "equippedId": starter.id,
            "economyRevision": current["economyRevision"] + 1}


@dataclass(frozen=True, slots=True)
class CatDefinition:
    id: str
    name: str
    rarity: int
    image_path: Path
    avatar_path: Path
    original_file: str = ""
    animation_style: str = "standard"
    exclusive: bool = False

    @property
    def rarity_color(self) -> str:
        return RARITY_COLORS[self.rarity]

    @property
    def price_cents(self) -> int:
        # Stable individual valuations within disjoint rarity bands.
        low, high = {1: (10, 25), 2: (30, 55), 3: (70, 140),
                     4: (200, 400), 5: (600, 1000), 6: (2000, 3500)}[self.rarity]
        return low + int(hashlib.sha256(self.id.encode()).hexdigest()[:8], 16) % (high - low + 1)


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
            rarity = max(1, min(6, int(item.get("rarity", 1))))
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
                animation_style=str(item.get("animationStyle") or "standard"),
                exclusive=bool(item.get("exclusive", False)),
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
                    rarity=min(6, 1 + (number - 1) // 2),
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
        (cat for cat in catalog if not cat.exclusive and cat.name.casefold() == "gatito pensativo"),
        None,
    )
    rollable = [cat for cat in catalog if not cat.exclusive]
    return preferred or min(rollable or catalog, key=lambda cat: (cat.rarity, cat.name.casefold()))
