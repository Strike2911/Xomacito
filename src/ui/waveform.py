from __future__ import annotations

import hashlib
import os
import subprocess
from pathlib import Path
from typing import Mapping


def waveform_target(cache_dir: str | Path, cache_key: str) -> Path:
    """Devuelve una ruta estable sin exponer el nombre o URL del medio."""
    digest = hashlib.sha256(str(cache_key).encode("utf-8", errors="replace")).hexdigest()[:24]
    return Path(cache_dir) / f"waveform-{digest}.png"


def render_waveform(
    ffmpeg_path: str,
    source: str,
    target: str | Path,
    headers: Mapping[str, str] | None = None,
) -> str:
    """Renderiza una forma de onda editorial; el negro queda transparente."""
    destination = Path(target)
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.is_file() and destination.stat().st_size > 256:
        return str(destination)

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
        header_blob = "".join(f"{key}: {value}\r\n" for key, value in safe_headers.items())
        command += ["-headers", header_blob]
    command += [
        "-i", str(source),
        "-filter_complex",
        "[0:a:0]aformat=channel_layouts=mono,"
        "showwavespic=s=1400x220:colors=0x7568F4@0.96:draw=full:scale=sqrt,"
        "format=rgba[v]",
        "-map", "[v]", "-frames:v", "1", str(temporary),
    ]
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
        raise RuntimeError("La forma de onda tardó demasiado en generarse.") from exc
    if completed.returncode != 0 or not temporary.is_file() or temporary.stat().st_size <= 256:
        temporary.unlink(missing_ok=True)
        detail = (completed.stderr or "No se encontró una pista de audio.").strip()
        raise RuntimeError(detail[-700:])
    os.replace(temporary, destination)
    return str(destination)
