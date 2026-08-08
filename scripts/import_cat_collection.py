from __future__ import annotations

import argparse
import hashlib
import json
import random
import shutil
from pathlib import Path

from PIL import Image, ImageDraw, ImageOps


SUPPORTED_SUFFIXES = {".jpg", ".jpeg", ".png", ".webp"}
RARITY_QUOTAS = {1: 46, 2: 29, 3: 17, 4: 9, 5: 4}
RARITY_OVERRIDES = {
    "gato dios": 5,
    "gato detective": 5,
    "gato raro": 3,
    "gato pixelart": 5,
    "jorge": 3,
    "gato conductor": 3,
    "gato inteligente": 3,
    "gato mago": 6,
    "gato playera": 6,
    "gato zarking": 6,
    "gato black bull": 6,
}
ANIMATION_OVERRIDES = {
    "gato mago": "arcane-mage",
    "gato playera": "playera-prismatic",
    "gato zarking": "zarking-cyber",
    "gato black bull": "blackbull-noir",
}
NAME_OVERRIDES = {
    "gato black bull": "BLACK BULL",
}
CATALOG_SCHEMA = 2
AVATAR_SIZE = 384


def prepare_avatar(image: Image.Image, normalized_name: str) -> Image.Image:
    """Crea el retrato circular y permite encuadres especiales reproducibles."""
    if normalized_name == "gato black bull":
        # El sombrero es parte esencial de la silueta de BLACK BULL. Un recorte
        # a sangre lo pegaba al borde superior y desplazaba visualmente el rostro.
        inset = 22
        portrait_size = AVATAR_SIZE - (inset * 2)
        portrait = ImageOps.fit(
            image,
            (portrait_size, portrait_size),
            method=Image.Resampling.LANCZOS,
            centering=(0.5, 0.5),
        )
        framed = Image.new("RGBA", (AVATAR_SIZE, AVATAR_SIZE), (0, 0, 0, 0))
        framed.alpha_composite(portrait, (inset, inset + 4))
        image = framed
    else:
        image = ImageOps.fit(
            image,
            (AVATAR_SIZE, AVATAR_SIZE),
            method=Image.Resampling.LANCZOS,
            centering=(0.5, 0.5),
        )

    mask = Image.new("L", image.size, 0)
    ImageDraw.Draw(mask).ellipse((0, 0, AVATAR_SIZE - 1, AVATAR_SIZE - 1), fill=255)
    alpha = image.getchannel("A")
    image.putalpha(Image.composite(alpha, mask, mask))
    return image


def stable_id(filename: str) -> str:
    digest = hashlib.sha1(filename.casefold().encode("utf-8")).hexdigest()[:12]
    return f"cat-{digest}"


def existing_assignments(catalog_path: Path) -> dict[str, dict]:
    try:
        payload = json.loads(catalog_path.read_text(encoding="utf-8"))
    except (OSError, ValueError, TypeError):
        return {}
    return {
        str(item.get("originalFile", "")).casefold(): item
        for item in payload.get("cats", [])
        if isinstance(item, dict) and item.get("originalFile")
    }


def initial_rarities(files: list[Path]) -> dict[str, int]:
    """Baraja una sola vez y reparte una colección equilibrada de 1 a 5 estrellas."""
    shuffled = list(files)
    random.Random("Xomacito Gacha Collection 2026").shuffle(shuffled)
    rarities: list[int] = []
    for rarity, amount in RARITY_QUOTAS.items():
        rarities.extend([rarity] * amount)
    if len(rarities) < len(shuffled):
        rarities.extend([1] * (len(shuffled) - len(rarities)))
    return {path.name.casefold(): rarity for path, rarity in zip(shuffled, rarities)}


def stable_rarity(filename: str) -> int:
    """Asigna una rareza reproducible sin cambiarla en futuras importaciones."""
    roll = int(hashlib.sha256(filename.casefold().encode("utf-8")).hexdigest()[:8], 16) % 1000
    if roll < 480:
        return 1
    if roll < 760:
        return 2
    if roll < 910:
        return 3
    if roll < 980:
        return 4
    return 5


def _normalized_name(value: str) -> str:
    return Path(value).stem.strip().casefold()


def import_collection(source: Path, destination: Path, *, append: bool = False) -> dict:
    files = sorted(
        (path for path in source.iterdir() if path.is_file() and path.suffix.lower() in SUPPORTED_SUFFIXES),
        key=lambda path: path.name.casefold(),
    )
    if not files:
        raise RuntimeError(f"No se encontraron imágenes compatibles en {source}")

    destination.mkdir(parents=True, exist_ok=True)
    catalog_path = destination / "catalog.json"
    previous = existing_assignments(catalog_path)
    first_import = not previous
    assigned = initial_rarities(files)
    cats = []

    if append:
        try:
            current_payload = json.loads(catalog_path.read_text(encoding="utf-8"))
        except (OSError, ValueError, TypeError):
            current_payload = {}
        cats.extend(
            item for item in current_payload.get("cats", [])
            if isinstance(item, dict)
        )
    imported_names = {path.name.casefold() for path in files}
    cats = [
        item for item in cats
        if str(item.get("originalFile", "")).casefold() not in imported_names
    ]

    for source_path in files:
        previous_item = previous.get(source_path.name.casefold(), {})
        cat_id = str(previous_item.get("id") or stable_id(source_path.name))
        normalized_name = _normalized_name(source_path.name)
        rarity = int(
            RARITY_OVERRIDES.get(
                normalized_name,
                previous_item.get("rarity")
                or (assigned[source_path.name.casefold()] if first_import else stable_rarity(source_path.name)),
            )
        )
        output_name = f"{cat_id}{source_path.suffix.lower()}"
        avatar_name = f"{cat_id}-avatar.webp"
        shutil.copy2(source_path, destination / output_name)
        with Image.open(source_path) as opened:
            image = ImageOps.exif_transpose(opened).convert("RGBA")
            image = prepare_avatar(image, normalized_name)
            image.save(destination / avatar_name, "WEBP", quality=88, method=4)
        cats.append(
            {
                "id": cat_id,
                "name": NAME_OVERRIDES.get(normalized_name, source_path.stem.strip().upper()),
                "rarity": max(1, min(6, rarity)),
                "image": output_name,
                "avatar": avatar_name,
                "originalFile": source_path.name,
                "animationStyle": ANIMATION_OVERRIDES.get(normalized_name, "standard"),
            }
        )

    for item in cats:
        normalized_name = _normalized_name(str(item.get("name") or item.get("originalFile") or ""))
        item["name"] = NAME_OVERRIDES.get(
            normalized_name,
            str(
                item.get("name")
                or Path(str(item.get("originalFile") or "")).stem
            ).strip().upper(),
        )
        if normalized_name in RARITY_OVERRIDES:
            item["rarity"] = RARITY_OVERRIDES[normalized_name]
        item["rarity"] = max(1, min(6, int(item.get("rarity", 1))))
        item["animationStyle"] = ANIMATION_OVERRIDES.get(
            normalized_name,
            str(item.get("animationStyle") or "standard"),
        )
    cats.sort(key=lambda item: str(item.get("name", "")).casefold())

    active_names = {item["image"] for item in cats} | {item["avatar"] for item in cats} | {"catalog.json"}
    for path in destination.iterdir():
        if path.is_file() and path.name not in active_names:
            path.unlink()

    payload = {
        "schema": CATALOG_SCHEMA,
        "collection": "Gatos de Xomacito",
        "source": "Colección aportada por Strike2911",
        "firstImportRandomized": first_import,
        "cats": cats,
    }
    catalog_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return payload


def main() -> int:
    parser = argparse.ArgumentParser(description="Importa la colección de gatos de Xomacito.")
    parser.add_argument("source", type=Path)
    parser.add_argument("destination", type=Path)
    parser.add_argument(
        "--append",
        action="store_true",
        help="Conserva el catálogo existente y añade o reemplaza los archivos indicados.",
    )
    args = parser.parse_args()
    payload = import_collection(
        args.source.resolve(),
        args.destination.resolve(),
        append=args.append,
    )
    counts = {rarity: 0 for rarity in range(1, 7)}
    for cat in payload["cats"]:
        counts[cat["rarity"]] += 1
    print(f"Importados: {len(payload['cats'])}")
    print("Rarezas: " + ", ".join(f"{rarity} estrellas={amount}" for rarity, amount in counts.items()))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
