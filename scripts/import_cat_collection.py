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
CATALOG_SCHEMA = 1
AVATAR_SIZE = 384


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


def import_collection(source: Path, destination: Path) -> dict:
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

    for source_path in files:
        previous_item = previous.get(source_path.name.casefold(), {})
        cat_id = str(previous_item.get("id") or stable_id(source_path.name))
        rarity = int(previous_item.get("rarity") or assigned[source_path.name.casefold()])
        output_name = f"{cat_id}{source_path.suffix.lower()}"
        avatar_name = f"{cat_id}-avatar.webp"
        shutil.copy2(source_path, destination / output_name)
        with Image.open(source_path) as opened:
            image = ImageOps.exif_transpose(opened).convert("RGBA")
            image = ImageOps.fit(
                image,
                (AVATAR_SIZE, AVATAR_SIZE),
                method=Image.Resampling.LANCZOS,
                centering=(0.5, 0.5),
            )
            mask = Image.new("L", image.size, 0)
            ImageDraw.Draw(mask).ellipse((0, 0, AVATAR_SIZE - 1, AVATAR_SIZE - 1), fill=255)
            image.putalpha(mask)
            image.save(destination / avatar_name, "WEBP", quality=88, method=4)
        cats.append(
            {
                "id": cat_id,
                "name": source_path.stem.strip(),
                "rarity": max(1, min(5, rarity)),
                "image": output_name,
                "avatar": avatar_name,
                "originalFile": source_path.name,
            }
        )

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
    args = parser.parse_args()
    payload = import_collection(args.source.resolve(), args.destination.resolve())
    counts = {rarity: 0 for rarity in range(1, 6)}
    for cat in payload["cats"]:
        counts[cat["rarity"]] += 1
    print(f"Importados: {len(payload['cats'])}")
    print("Rarezas: " + ", ".join(f"{rarity} estrellas={amount}" for rarity, amount in counts.items()))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
