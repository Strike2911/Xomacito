from __future__ import annotations

import hashlib
import os
import subprocess
from pathlib import Path
from typing import Mapping


def filmstrip_target(cache_dir: str | Path, cache_key: str) -> Path:
    """Crea una ruta de caché estable sin exponer el nombre ni la URL del video."""
    digest = hashlib.sha256(str(cache_key).encode("utf-8", errors="replace")).hexdigest()[:24]
    return Path(cache_dir) / f"filmstrip-{digest}.png"


def render_filmstrip(
    ffmpeg_path: str,
    source: str,
    target: str | Path,
    duration: float,
    headers: Mapping[str, str] | None = None,
    frame_count: int = 64,
) -> str:
    """Renderiza una tira cronológica uniforme al estilo de una línea de edición."""
    destination = Path(target)
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.is_file() and destination.stat().st_size > 256:
        return str(destination)
    if float(duration or 0) <= 0:
        raise RuntimeError("No se conoce la duración del video.")

    count = max(24, min(64, int(frame_count or 64)))
    temporary = destination.with_name(destination.stem + ".tmp.png")
    temporary.unlink(missing_ok=True)
    command = [
        str(ffmpeg_path), "-y", "-nostdin", "-hide_banner", "-loglevel", "error",
    ]
    safe_headers = {
        str(key): str(value)
        for key, value in dict(headers or {}).items()
        if str(key).strip() and "\r" not in str(value) and "\n" not in str(value)
    }
    user_agent = safe_headers.pop("User-Agent", safe_headers.pop("user-agent", ""))
    if user_agent:
        command += ["-user_agent", user_agent]
    if safe_headers:
        command += ["-headers", "".join(f"{key}: {value}\r\n" for key, value in safe_headers.items())]

    sample_rate = count / max(0.1, float(duration))
    filters = (
        f"fps=fps={sample_rate:.9f}:round=up,"
        "scale=112:112:force_original_aspect_ratio=increase,"
        "crop=112:112,"
        f"tile={count}x1:padding=2:margin=0,format=rgb24"
    )
    command += ["-i", str(source), "-vf", filters, "-frames:v", "1", str(temporary)]
    flags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
    try:
        completed = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=120,
            creationflags=flags,
        )
    except subprocess.TimeoutExpired as exc:
        temporary.unlink(missing_ok=True)
        raise RuntimeError("La previsualización del video tardó demasiado en generarse.") from exc
    if completed.returncode != 0 or not temporary.is_file() or temporary.stat().st_size <= 256:
        temporary.unlink(missing_ok=True)
        detail = (completed.stderr or "No se encontraron fotogramas de video.").strip()
        raise RuntimeError(detail[-700:])
    os.replace(temporary, destination)
    return str(destination)
