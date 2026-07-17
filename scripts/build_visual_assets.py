"""Construye los recursos visuales de Xomacito desde las fotos del usuario.

Las fotos no se reinterpretan ni se regeneran: solo se recortan, redimensionan
y enmarcan de forma determinista para que funcionen bien como iconos de Windows.
"""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageOps


ROOT = Path(__file__).resolve().parents[1]
SOURCE_IMAGES = tuple(
    ROOT / "assets" / "cat-icons" / f"cat-{number:02d}.png"
    for number in range(1, 9)
)
ICON_COPIES = (ROOT / "Xomacito-icon.ico",)


def _framed_cat(source: Path) -> Image.Image:
    photo = Image.open(source).convert("RGB")
    photo = ImageOps.fit(photo, (444, 444), method=Image.Resampling.LANCZOS)

    canvas = Image.new("RGBA", (512, 512), (0, 0, 0, 0))
    shadow = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    ImageDraw.Draw(shadow).ellipse((32, 38, 480, 486), fill=(0, 0, 0, 125))
    shadow = shadow.filter(ImageFilter.GaussianBlur(14))
    canvas.alpha_composite(shadow)

    ring = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    ring_draw = ImageDraw.Draw(ring)
    ring_draw.ellipse((22, 22, 490, 490), fill=(108, 92, 231, 255))
    ring_draw.ellipse((30, 30, 482, 482), fill=(75, 219, 205, 255))
    canvas.alpha_composite(ring)

    mask = Image.new("L", (444, 444), 0)
    ImageDraw.Draw(mask).ellipse((0, 0, 443, 443), fill=255)
    canvas.paste(photo, (34, 34), mask)
    return canvas


def main() -> None:
    missing = [str(path) for path in SOURCE_IMAGES if not path.exists()]
    if missing:
        raise FileNotFoundError("Faltan fotos fuente:\n" + "\n".join(missing))

    output = ROOT / "assets" / "cat-icons"
    output.mkdir(parents=True, exist_ok=True)

    for number, source in enumerate(SOURCE_IMAGES, start=1):
        stem = f"cat-{number:02d}"
        photo = ImageOps.fit(
            Image.open(source).convert("RGB"),
            (768, 768),
            method=Image.Resampling.LANCZOS,
        )
        photo.save(output / f"{stem}.png", optimize=True)

        icon = _framed_cat(source)
        icon.save(
            output / f"{stem}.ico",
            format="ICO",
            sizes=((16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)),
        )

    primary = (output / "cat-01.ico").read_bytes()
    for destination in ICON_COPIES:
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(primary)

    print(f"Creados 8 gatitos diarios en {output}")
    print("El gatito 01 quedó como icono fijo del ejecutable y de respaldo.")


if __name__ == "__main__":
    main()
