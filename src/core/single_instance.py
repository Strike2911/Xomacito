"""Bloqueo de instancia única y activación de la ventana existente."""

from __future__ import annotations

import os
import re
import tempfile
import time
from pathlib import Path


def _safe_lock_name(name: str) -> str:
    normalized = re.sub(r"[^A-Za-z0-9_.-]+", "-", str(name)).strip("-.")
    return normalized or "application"


class SingleInstanceGuard:
    """Mantiene un cerrojo que el sistema operativo libera incluso tras un cierre abrupto."""

    def __init__(self, app_name: str, lock_directory: str | os.PathLike | None = None):
        base_directory = Path(lock_directory) if lock_directory else Path(tempfile.gettempdir())
        self.lock_path = base_directory / f"{_safe_lock_name(app_name)}.instance.lock"
        self._stream = None

    @property
    def acquired(self) -> bool:
        return self._stream is not None

    def acquire(self, wait_seconds: float = 0.0, poll_interval: float = 0.1) -> bool:
        """Intenta adquirir el cerrojo; durante un reinicio puede esperar al proceso anterior."""
        if self.acquired:
            return True

        deadline = time.monotonic() + max(0.0, float(wait_seconds))
        while True:
            stream = None
            try:
                self.lock_path.parent.mkdir(parents=True, exist_ok=True)
                stream = self.lock_path.open("a+b")
                stream.seek(0)
                if stream.read(1) != b"1":
                    stream.seek(0)
                    stream.write(b"1")
                    stream.flush()
                stream.seek(0)
                self._lock_stream(stream)
            except (OSError, IOError):
                if stream is not None:
                    stream.close()
                if time.monotonic() >= deadline:
                    return False
                time.sleep(max(0.01, float(poll_interval)))
                continue

            self._stream = stream
            return True

    @staticmethod
    def _lock_stream(stream) -> None:
        if os.name == "nt":
            import msvcrt

            msvcrt.locking(stream.fileno(), msvcrt.LK_NBLCK, 1)
            return

        import fcntl

        fcntl.flock(stream.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)

    @staticmethod
    def _unlock_stream(stream) -> None:
        if os.name == "nt":
            import msvcrt

            stream.seek(0)
            msvcrt.locking(stream.fileno(), msvcrt.LK_UNLCK, 1)
            return

        import fcntl

        fcntl.flock(stream.fileno(), fcntl.LOCK_UN)

    def release(self) -> None:
        stream, self._stream = self._stream, None
        if stream is None:
            return
        try:
            self._unlock_stream(stream)
        except OSError:
            pass
        finally:
            stream.close()

    def __enter__(self):
        if not self.acquire():
            raise RuntimeError("La aplicación ya tiene una instancia activa")
        return self

    def __exit__(self, _exc_type, _exc_value, _traceback):
        self.release()


def focus_existing_window(title_prefix: str) -> bool:
    """Restaura y enfoca la ventana visible cuyo título corresponde a la aplicación."""
    if os.name != "nt":
        return False

    import ctypes
    from ctypes import wintypes

    user32 = ctypes.windll.user32
    matches = []
    prefix = str(title_prefix).casefold()
    enum_callback = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)

    @enum_callback
    def visit_window(hwnd, _lparam):
        if not user32.IsWindowVisible(hwnd):
            return True
        length = user32.GetWindowTextLengthW(hwnd)
        if length <= 0:
            return True
        title = ctypes.create_unicode_buffer(length + 1)
        user32.GetWindowTextW(hwnd, title, length + 1)
        if title.value.casefold().startswith(prefix):
            matches.append(hwnd)
            return False
        return True

    user32.EnumWindows(visit_window, 0)
    if not matches:
        return False

    hwnd = matches[0]
    SW_RESTORE = 9
    user32.ShowWindow(hwnd, SW_RESTORE)
    user32.SetForegroundWindow(hwnd)
    return True
