from __future__ import annotations

import ctypes
import os
import sys
import subprocess
import threading
import time
from pathlib import Path


SOUND_FILENAME = "download-complete.mp3"
PLATINUM_SOUND_FILENAME = "platinum-celebration.mp3"
GACHA_SOUND_FILENAMES = {rarity: f"cat-jet-{rarity}.mp3" for rarity in range(1, 7)}
# La revelación del secreto tiene sonido propio; el resto usa su rareza.
GACHA_STYLE_SOUND_FILENAMES = {"hola-haunting": "god-violin-reveal.wav"}
GACHA_EQUIP_SOUND_FILENAMES = {}


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


def gacha_sound_path(rarity: int, animation_style: str = "") -> Path | None:
    normalized = max(1, min(6, int(rarity or 1)))
    filename = GACHA_STYLE_SOUND_FILENAMES.get(
        str(animation_style or "").strip(),
        GACHA_SOUND_FILENAMES[normalized],
    )
    return _asset_path("sfx", filename)


def gacha_equip_sound_path(rarity: int) -> Path | None:
    return gacha_sound_path(rarity)


def platinum_sound_path() -> Path | None:
    return _asset_path("sfx", PLATINUM_SOUND_FILENAME)


def _play_with_mci(path: Path, volume: int = 1000) -> None:
    if sys.platform == "darwin":
        try:
            subprocess.run(["/usr/bin/afplay", "-v", str(max(0, min(1000, int(volume))) / 1000), str(path)], check=False)
        except OSError:
            pass
        return
    if os.name != "nt":
        return
    if path.suffix.casefold() == ".wav":
        try:
            import winsound

            winsound.PlaySound(str(path), winsound.SND_FILENAME)
        except (OSError, RuntimeError):
            pass
        return
    alias = f"xomacito_complete_{os.getpid()}_{threading.get_ident()}_{time.time_ns()}"
    send = ctypes.windll.winmm.mciSendStringW
    quoted = str(path).replace('"', '')
    if send(f'open "{quoted}" type mpegvideo alias {alias}', None, 0, None) != 0:
        return
    try:
        send(f"setaudio {alias} volume to {max(0, min(1000, int(volume)))}", None, 0, None)
        send(f"play {alias} wait", None, 0, None)
    finally:
        send(f"close {alias}", None, 0, None)


def _play_async(path: Path | None, volume: int = 1000) -> bool:
    if path is None:
        return False
    threading.Thread(target=_play_with_mci, args=(path, volume), daemon=True).start()
    return True


def play_completion_sound() -> bool:
    """Reproduce el maullido 10 dB más bajo sin bloquear la interfaz."""
    return _play_async(completion_sound_path(), volume=316)


def play_gacha_reveal_sound(rarity: int, animation_style: str = "") -> bool:
    """Reproduce el efecto sincronizado con la revelación de la rareza."""
    return _play_async(gacha_sound_path(rarity, animation_style))


def play_gacha_equip_sound(rarity: int) -> bool:
    return _play_async(gacha_equip_sound_path(rarity))


def play_download_failure_sound() -> bool:
    return _play_async(_asset_path("sfx", "download-cancel.mp3"))


def play_platinum_celebration_sound() -> bool:
    """Acompaña la celebración de colección completa sin bloquear Qt."""
    return _play_async(platinum_sound_path())
