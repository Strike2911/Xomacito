from __future__ import annotations

import os
from io import BytesIO
from pathlib import Path
from uuid import uuid4

from PIL import Image, ImageOps


PREMIERE_THUMBNAIL_FILTER = "Imagen compatible con Premiere (*.jpg *.jpeg *.png)"


def premiere_thumbnail_path(path: str | Path) -> Path:
    """Normaliza la extensión a JPEG o PNG, formatos seguros para Premiere."""
    destination = Path(path)
    suffix = destination.suffix.lower()
    if suffix not in {".jpg", ".jpeg", ".png"}:
        destination = destination.with_suffix(".jpg")
    return destination


def save_premiere_thumbnail(image_data: bytes, path: str | Path) -> Path:
    """Decodifica y vuelve a codificar la imagen; nunca cambia sólo la extensión."""
    destination = premiere_thumbnail_path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_name(f".{destination.stem}-{uuid4().hex}.tmp")
    try:
        with Image.open(BytesIO(image_data)) as source:
            image = ImageOps.exif_transpose(source)
            if destination.suffix.lower() == ".png":
                output = image.convert("RGBA" if "A" in image.getbands() else "RGB")
                output.save(temporary, "PNG", optimize=True)
            else:
                if "A" in image.getbands():
                    rgba = image.convert("RGBA")
                    output = Image.new("RGB", rgba.size, "white")
                    output.paste(rgba, mask=rgba.getchannel("A"))
                else:
                    output = image.convert("RGB")
                output.save(
                    temporary,
                    "JPEG",
                    quality=95,
                    subsampling=0,
                    optimize=True,
                    progressive=False,
                )
        os.replace(temporary, destination)
        return destination
    finally:
        try:
            temporary.unlink(missing_ok=True)
        except OSError:
            pass
