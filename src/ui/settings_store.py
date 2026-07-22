from __future__ import annotations

import json
import os
import tempfile
import threading
from copy import deepcopy
from pathlib import Path
from typing import Any

from PySide6.QtCore import QObject, Signal


DEFAULT_SETTINGS: dict[str, Any] = {
    "default_download_path": str(Path.home() / "Downloads"),
    "batch_download_path": str(Path.home() / "Downloads"),
    "image_output_path": str(Path.home() / "Downloads"),
    "cookies_path": "",
    "cookies_mode": "No usar",
    "selected_browser": "chrome",
    "browser_profile": "",
    "batch_playlist_analysis": True,
    "batch_fast_mode": False,
    "quick_preset_saved": "Archivo - H.265 Normal",
    "recode_settings": {"keep_original": True},
    "apply_quick_preset_enabled": False,
    "keep_original_quick_enabled": True,
    "image_settings": {},
    "upscayl_custom_models": {},
    "console_enabled": False,
    "console_wrap": True,
    "keep_ai_models_in_memory": False,
    "show_onnx_warning": True,
    "vector_dpi": 300,
    "preview_vector_dpi": 96,
    "vector_force_background": False,
    "inkscape_enabled": True,
    "inkscape_path": "",
    "inkscape_version": "",
    "selected_theme_accent": "midnight_ocean",
    "theme_selection_explicit": False,
    "appearance_mode": "Dark",
    "clean_titles": True,
    "release_notice_seen_version": "",
    "cat_gacha": {
        "schema": 1,
        "downloadProgress": 0,
        "earnedRolls": 0,
        "totalDownloads": 0,
        "totalRolls": 0,
        "lastDailyRoll": "",
        "unlockedIds": [],
        "equippedId": "",
        "duplicates": {},
    },
}


class SettingsStore(QObject):
    changed = Signal(str, object)
    saved = Signal()

    def __init__(self, app_name: str = "Xomacito", parent=None):
        super().__init__(parent)
        roaming = Path(os.getenv("APPDATA", Path.home() / "AppData" / "Roaming"))
        self.directory = roaming / app_name
        self.path = self.directory / "app_settings.json"
        self.presets_path = self.directory / "presets.json"
        self.themes_dir = self.directory / "themes"
        self._lock = threading.RLock()
        self._values = deepcopy(DEFAULT_SETTINGS)
        self.load()

    def load(self) -> dict[str, Any]:
        try:
            loaded = json.loads(self.path.read_text(encoding="utf-8-sig"))
        except (OSError, ValueError, TypeError):
            loaded = {}
        if isinstance(loaded, dict):
            self._deep_update(self._values, loaded)
        return self.snapshot()

    @staticmethod
    def _deep_update(target: dict, incoming: dict):
        for key, value in incoming.items():
            if isinstance(value, dict) and isinstance(target.get(key), dict):
                SettingsStore._deep_update(target[key], value)
            else:
                target[key] = value

    def get(self, key: str, default=None):
        with self._lock:
            return deepcopy(self._values.get(key, default))

    def set(self, key: str, value, *, save: bool = True):
        with self._lock:
            if self._values.get(key) == value:
                return
            self._values[key] = deepcopy(value)
        self.changed.emit(key, value)
        if save:
            self.save()

    def update(self, values: dict[str, Any], *, save: bool = True):
        changed: list[tuple[str, Any]] = []
        with self._lock:
            for key, value in values.items():
                if self._values.get(key) != value:
                    self._values[key] = deepcopy(value)
                    changed.append((key, value))
        for key, value in changed:
            self.changed.emit(key, value)
        if changed and save:
            self.save()

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            return deepcopy(self._values)

    def save(self):
        self.directory.mkdir(parents=True, exist_ok=True)
        payload = json.dumps(self.snapshot(), indent=2, ensure_ascii=False)
        fd, temporary = tempfile.mkstemp(
            prefix="app_settings-", suffix=".tmp", dir=self.directory
        )
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as stream:
                stream.write(payload)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary, self.path)
        finally:
            try:
                Path(temporary).unlink(missing_ok=True)
            except OSError:
                pass
        self.saved.emit()
