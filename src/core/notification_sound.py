from __future__ import annotations

import ctypes
import os
import sys
import threading
import time
from pathlib import Path


SOUND_FILENAME = "download-complete.mp3"
PLATINUM_SOUND_FILENAME = "platinum-celebration.mp3"
GACHA_SOUND_FILENAMES = {
    1: "gacha-reveal-1.wav",
    2: "gacha-reveal-2.wav",
    3: "gacha-reveal-3.wav",
    4: "gacha-reveal-4.wav",
    5: "gacha-reveal-5.wav",
    6: "gacha-reveal-6-arcane.wav",
}
GACHA_STYLE_SOUND_FILENAMES = {
    "arcane-mage": "gacha-reveal-6-arcane.wav",
    "playera-prismatic": "gacha-reveal-6-playera.wav",
    "zarking-cyber": "gacha-reveal-6-zarking.wav",
    "blackbull-noir": "gacha-reveal-6-blackbull.wav",
    "strike-apex": "gacha-reveal-6-strike.wav",
}
GACHA_EQUIP_SOUND_FILENAMES = {
    "arcane-mage": "gacha-equip-6-arcane.wav",
    "playera-prismatic": "gacha-equip-6-playera.wav",
    "zarking-cyber": "gacha-equip-6-zarking.wav",
    "blackbull-noir": "gacha-equip-6-blackbull.wav",
    "strike-apex": "gacha-equip-6-strike.wav",
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


def gacha_sound_path(rarity: int, animation_style: str = "") -> Path | None:
    normalized = max(1, min(6, int(rarity or 1)))
    filename = GACHA_STYLE_SOUND_FILENAMES.get(
        str(animation_style or "").strip(),
        GACHA_SOUND_FILENAMES[normalized],
    )
    return _asset_path("sfx", filename)


def gacha_equip_sound_path(animation_style: str) -> Path | None:
    filename = GACHA_EQUIP_SOUND_FILENAMES.get(str(animation_style or "").strip())
    return _asset_path("sfx", filename) if filename else None


def platinum_sound_path() -> Path | None:
    return _asset_path("sfx", PLATINUM_SOUND_FILENAME)


def _play_with_mci(path: Path, volume: int = 1000) -> None:
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


def play_gacha_equip_sound(animation_style: str) -> bool:
    """Da identidad sonora propia a cada gato mítico al equiparlo."""
    return _play_async(gacha_equip_sound_path(animation_style))


def play_platinum_celebration_sound() -> bool:
    """Acompaña la celebración de colección completa sin bloquear Qt."""
    return _play_async(platinum_sound_path())
