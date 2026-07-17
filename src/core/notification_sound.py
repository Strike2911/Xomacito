from __future__ import annotations

import ctypes
import os
import sys
import threading
import time
from pathlib import Path


SOUND_FILENAME = "download-complete.mp3"


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


def completion_sound_path() -> Path | None:
    for root in _roots():
        candidate = root / "assets" / SOUND_FILENAME
        if candidate.is_file():
            return candidate
    return None


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


def play_completion_sound() -> bool:
    path = completion_sound_path()
    if path is None:
        return False
    threading.Thread(target=_play_with_mci, args=(path,), daemon=True).start()
    return True
