from __future__ import annotations

import ctypes
import os
import sys
import threading
import time
from pathlib import Path


SOUND_FILENAME = "download-complete.mp3"
GACHA_SOUND_FILENAMES = {
    1: "gacha-reveal-1.mp3",
    2: "gacha-reveal-2.mp3",
    3: "gacha-reveal-3.mp3",
    4: "gacha-reveal-4.mp3",
    5: "gacha-reveal-5.mp3",
}


def _roots() -> list[Path]:
    roots: list[Path] = []
    if getattr(sys, "frozen", False):
        executable_root = Path(sys.executable).resolve().parent
        roots.extend((executable_root, executable_root.parent))
    try:
        roots.extend(Path(__file__).resolve().parents)
    except OSError:
        pass
    return list(dict.fromkeys(roots))


def _asset_path(*parts: str) -> Path | None:
    for root in _roots():
        candidate = root / "assets" / Path(*parts)
        if candidate.is_file():
            return candidate
    return None


def completion_sound_path() -> Path | None:
    return _asset_path(SOUND_FILENAME)


def gacha_sound_path(rarity: int) -> Path | None:
    normalized = max(1, min(5, int(rarity or 1)))
    return _asset_path("sfx", GACHA_SOUND_FILENAMES[normalized])


def _play_with_mci(path: Path) -> None:
    if os.name != "nt":
        return
    alias = f"xomacito_complete_{os.getpid()}_{threading.get_ident()}_{time.time_ns()}"
    send = ctypes.windll.winmm.mciSendStringW
    quoted = str(path).replace('"', '')
    if send(f'open "{quoted}" type mpegvideo alias {alias}', None, 0, None) != 0:
        return
    try:
        send(f"play {alias} wait", None, 0, None)
    finally:
        send(f"close {alias}", None, 0, None)


def _play_async(path: Path | None) -> bool:
    if path is None:
        return False
    threading.Thread(target=_play_with_mci, args=(path,), daemon=True).start()
    return True


def play_completion_sound() -> bool:
    """Reproduce el maullido de descarga sin bloquear la interfaz."""
    return _play_async(completion_sound_path())


def play_gacha_reveal_sound(rarity: int) -> bool:
    """Reproduce el efecto sincronizado con la revelación de la rareza."""
    return _play_async(gacha_sound_path(rarity))
