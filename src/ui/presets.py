from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path

from PySide6.QtCore import QObject, Property, Signal, Slot

from src.core.processor import CODEC_PROFILES

from .settings_store import SettingsStore


ALPHA_PRESET = "Edición - ProRes 4444 Liviano (Transparencia)"


def _video(name, codec, profile, container, audio="AAC", audio_profile="Buena Calidad (~192kbps)"):
    return {
        "mode_compatibility": "Video+Audio",
        "recode_video_enabled": True,
        "recode_audio_enabled": bool(audio and audio != "-"),
        "keep_original_file": True,
        "recode_proc": "CPU",
        "recode_codec_name": codec,
        "recode_profile_name": profile,
        "recode_audio_codec_name": audio or "-",
        "recode_audio_profile_name": audio_profile if audio else "-",
        "recode_container": container,
    }


def _audio(codec, profile, container):
    return {
        "mode_compatibility": "Solo Audio",
        "recode_video_enabled": False,
        "recode_audio_enabled": True,
        "keep_original_file": True,
        "recode_audio_codec_name": codec,
        "recode_audio_profile_name": profile,
        "recode_container": container,
    }


BUILT_IN_PRESETS = {
    "Archivo - H.265 Normal": _video("", "H.265 (x265)", "Calidad Equilibrada (CRF 20)", ".mp4"),
    "Archivo - H.265 Máxima": _video("", "H.265 (x265)", "Calidad Máxima (CRF 16)", ".mp4", "AAC", "Máxima Calidad (~320kbps)"),
    "Web/Móvil - H.264 Liviano": _video("", "H.264 (x264)", "Calidad Rápida (CRF 28)", ".mp4", "AAC", "Calidad Baja (~128kbps)"),
    "Web/Móvil - H.264 Normal": _video("", "H.264 (x264)", "Calidad Media (CRF 23)", ".mp4", "AAC", "Alta Calidad (~256kbps)"),
    "Web/Móvil - H.264 Máxima": _video("", "H.264 (x264)", "Alta Calidad (CRF 18)", ".mp4", "AAC", "Máxima Calidad (~320kbps)"),
    "Edición - ProRes 422 Proxy": _video("", "Apple ProRes (prores_aw) (Velocidad)", "422 Proxy", ".mov", "WAV (Sin Comprimir)", "PCM 16-bit"),
    "Edición - ProRes 422": _video("", "Apple ProRes (prores_ks) (Precisión)", "422 HQ", ".mov", "WAV (Sin Comprimir)", "PCM 16-bit"),
    "Edición - ProRes 422 LT": _video("", "Apple ProRes (prores_aw) (Velocidad)", "422 LT", ".mov", "WAV (Sin Comprimir)", "PCM 16-bit"),
    ALPHA_PRESET: _video("", "Apple ProRes (prores_ks) (Precisión)", "4444 Liviano (Alpha 8-bit)", ".mov", "WAV (Sin Comprimir)", "PCM 16-bit"),
    "GIF Rápido (Baja Calidad)": _video("", "GIF (animado)", "Baja Calidad (Rápido)", ".gif", "", ""),
    "GIF (Media Calidad)": _video("", "GIF (animado)", "Calidad Media (540p, 24fps)", ".gif", "", ""),
    "GIF (Alta Calidad)": _video("", "GIF (animado)", "Calidad Alta (720p, 30fps)", ".gif", "", ""),
    "Audio - MP3 128kbps": _audio("MP3 (libmp3lame)", "128kbps (CBR)", ".mp3"),
    "Audio - MP3 192kbps": _audio("MP3 (libmp3lame)", "192kbps (CBR)", ".mp3"),
    "Audio - MP3 320kbps": _audio("MP3 (libmp3lame)", "320kbps (CBR)", ".mp3"),
    "Audio - AAC 192kbps": _audio("AAC", "Buena Calidad (~192kbps)", ".m4a"),
    "Audio - WAV 16-bit (Sin pérdida)": _audio("WAV (Sin Comprimir)", "PCM 16-bit", ".wav"),
}


def _codec_record(category: str, codec_name: str) -> tuple[str, dict, str]:
    codec_data = CODEC_PROFILES[category][codec_name]
    encoder = next(key for key in codec_data if key != "container")
    return encoder, codec_data[encoder], codec_data.get("container", "")


def resolve_recode_parameters(options: dict) -> tuple[list[str], str]:
    """Convierte las elecciones legibles de la UI en argumentos validados de FFmpeg."""
    mode = options.get("mode", "Video+Audio")
    params: list[str] = []
    output_container = options.get("recode_container") or ""
    if mode == "Video+Audio" and options.get("recode_video_enabled"):
        name = options.get("recode_codec_name")
        profile = options.get("recode_profile_name")
        _encoder, profiles, default_container = _codec_record("Video", name)
        selected = profiles[profile]
        if selected == "CUSTOM_BITRATE_VBR":
            bitrate = str(options.get("custom_bitrate_value") or "8")
            selected = ["-c:v", _encoder, "-b:v", f"{bitrate}M"]
        elif selected == "CUSTOM_BITRATE_CBR":
            bitrate = str(options.get("custom_bitrate_value") or "8")
            selected = ["-c:v", _encoder, "-b:v", f"{bitrate}M", "-minrate", f"{bitrate}M", "-maxrate", f"{bitrate}M"]
        elif selected == "CUSTOM_GIF":
            fps = str(options.get("custom_gif_fps") or "15")
            width = str(options.get("custom_gif_width") or "480")
            selected = ["-filter_complex", f"[0:v] fps={fps},scale={width}:-1,split [a][b];[a] palettegen [p];[b][p] paletteuse"]
        params.extend(selected)
        output_container = output_container or default_container
    elif mode == "Solo Audio":
        params.extend(["-vn"])

    if options.get("recode_audio_enabled"):
        name = options.get("recode_audio_codec_name")
        profile = options.get("recode_audio_profile_name")
        _encoder, profiles, default_container = _codec_record("Audio", name)
        params.extend(profiles[profile])
        output_container = output_container or default_container
    elif mode == "Video+Audio":
        params.extend(["-an"])

    if options.get("fps_force_enabled") and options.get("fps_value"):
        params.extend(["-r", str(options["fps_value"])])
    if options.get("resolution_change_enabled"):
        width = str(options.get("res_width") or "-2")
        height = str(options.get("res_height") or "-2")
        force_original = ":force_original_aspect_ratio=decrease" if options.get("maintain_aspect", True) else ""
        params.extend(["-vf", f"scale={width}:{height}{force_original}"])
    params.extend(["-map_metadata", "0", "-map_chapters", "0"])
    if output_container == ".mp4":
        params.extend(["-movflags", "+faststart"])
    return params, output_container


class PresetStore(QObject):
    presetsChanged = Signal()

    def __init__(self, settings: SettingsStore, parent=None):
        super().__init__(parent)
        self.settings = settings
        self.built_in = deepcopy(BUILT_IN_PRESETS)
        self.custom: list[dict] = []
        self._load()

    def _load(self):
        try:
            payload = json.loads(self.settings.presets_path.read_text(encoding="utf-8-sig"))
        except (OSError, ValueError):
            payload = {}
        custom = payload.get("custom_presets", [])
        if isinstance(custom, list):
            self.custom = [item for item in custom if isinstance(item, dict) and item.get("name") and isinstance(item.get("data"), dict)]
        self._save()

    def _save(self):
        self.settings.directory.mkdir(parents=True, exist_ok=True)
        payload = {"built_in_presets": self.built_in, "custom_presets": self.custom}
        self.settings.presets_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")

    @Property("QStringList", notify=presetsChanged)
    def videoPresets(self):
        return self.names("Video+Audio")

    @Property("QStringList", notify=presetsChanged)
    def audioPresets(self):
        return self.names("Solo Audio")

    @Property("QStringList", constant=True)
    def videoCodecs(self):
        return list(CODEC_PROFILES["Video"])

    @Property("QStringList", constant=True)
    def audioCodecs(self):
        return list(CODEC_PROFILES["Audio"])

    def names(self, mode: str) -> list[str]:
        names = [name for name, data in self.built_in.items() if data.get("mode_compatibility") == mode]
        names.extend(item["name"] for item in self.custom if item["data"].get("mode_compatibility") == mode)
        return names

    def find(self, name: str) -> dict:
        for item in self.custom:
            if item["name"] == name:
                return deepcopy(item["data"])
        return deepcopy(self.built_in.get(name, {}))

    @Slot(str, result="QVariantMap")
    def preset(self, name: str):
        return self.find(name)

    @Slot(str, str, result="QStringList")
    def profiles(self, category: str, codec_name: str):
        if category not in CODEC_PROFILES or codec_name not in CODEC_PROFILES[category]:
            return []
        _encoder, profiles, _container = _codec_record(category, codec_name)
        return list(profiles)

    @Slot(str, str, "QVariantMap", result=bool)
    def saveCustom(self, name: str, mode: str, data: dict):
        name = name.strip()
        if not name:
            return False
        record = deepcopy(data)
        record["mode_compatibility"] = mode
        self.custom = [item for item in self.custom if item["name"] != name]
        self.custom.append({"name": name, "data": record})
        self._save()
        self.presetsChanged.emit()
        return True

    @Slot(str, result=bool)
    def deleteCustom(self, name: str):
        before = len(self.custom)
        self.custom = [item for item in self.custom if item["name"] != name]
        if len(self.custom) == before:
            return False
        self._save()
        self.presetsChanged.emit()
        return True

    def export_to(self, name: str, destination: str | Path):
        data = next((item["data"] for item in self.custom if item["name"] == name), None)
        if data is None:
            raise ValueError("Sólo se pueden exportar presets personales.")
        payload = {"xomacito_preset_version": 1, "preset_name": name, "data": data}
        Path(destination).write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")

    def import_from(self, source: str | Path) -> str:
        payload = json.loads(Path(source).read_text(encoding="utf-8-sig"))
        name, data = payload.get("preset_name"), payload.get("data")
        if not isinstance(name, str) or not isinstance(data, dict) or data.get("mode_compatibility") not in {"Video+Audio", "Solo Audio"}:
            raise ValueError("El archivo no contiene un preset válido de Xomacito.")
        self.custom = [item for item in self.custom if item["name"] != name]
        self.custom.append({"name": name, "data": data})
        self._save()
        self.presetsChanged.emit()
        return name
