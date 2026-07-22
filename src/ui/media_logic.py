from __future__ import annotations

import math
from collections import defaultdict
from typing import Any

from src.core.constants import (
    AUDIO_EXTENSIONS,
    DEFAULT_PRIORITY,
    EDITOR_FRIENDLY_CRITERIA,
    LANG_CODE_MAP,
    LANGUAGE_ORDER,
    VIDEO_EXTENSIONS,
)
from src.core.downloader import apply_site_specific_rules


def normalize_info(info: dict | None) -> dict | None:
    if not info:
        return info
    info = apply_site_specific_rules(info)
    if info.get("formats"):
        info["formats"] = [
            fmt for fmt in info["formats"]
            if not str(fmt.get("format_id", "")).startswith("sb")
        ] or info["formats"]
        return info

    url = info.get("url") or info.get("manifest_url") or ""
    ext = str(info.get("ext") or "").lower()
    vcodec = info.get("vcodec") or "none"
    acodec = info.get("acodec")
    extractor = str(info.get("extractor_key") or "").lower()
    audio_only = (
        ext in AUDIO_EXTENSIONS
        or (url and vcodec == "none" and acodec and acodec != "none")
        or extractor in {"applepodcasts", "soundcloud", "audioboom", "spreaker", "libsyn"}
    )
    if audio_only:
        info["formats"] = [{
            "format_id": "0",
            "url": url,
            "ext": ext or "mp3",
            "vcodec": "none",
            "acodec": acodec or ext or "unknown",
            "abr": info.get("abr"),
            "tbr": info.get("tbr"),
            "filesize": info.get("filesize"),
            "filesize_approx": info.get("filesize_approx"),
            "protocol": info.get("protocol", "https"),
            "format_note": "Audio directo",
        }]
    elif info.get("is_live") and url:
        info["formats"] = [{
            "format_id": "live", "url": url, "ext": ext or "mp4",
            "protocol": "m3u8_native", "format_note": "Livestream",
            "vcodec": info.get("vcodec", "unknown"),
            "acodec": info.get("acodec", "unknown"),
        }]
    return info


def classify_format(fmt: dict) -> str:
    ext = str(fmt.get("ext") or "").lower()
    vcodec = str(fmt.get("vcodec") or "").lower()
    acodec = str(fmt.get("acodec") or "").lower()
    note = str(fmt.get("format_note") or "").lower()
    if "audio directo" in note:
        return "audio"
    if vcodec in {"none", "audio only"} and acodec not in {"", "none"}:
        return "audio"
    if ext in AUDIO_EXTENSIONS and vcodec in {"", "none", "unknown"}:
        return "audio"
    if vcodec not in {"", "none", "unknown", "images"}:
        return "video"
    if ext in VIDEO_EXTENSIONS or "livestream" in note:
        return "video"
    return "unknown"


def _size(fmt: dict) -> float:
    value = fmt.get("filesize") or fmt.get("filesize_approx")
    try:
        return float(value or 0)
    except (TypeError, ValueError):
        return 0.0


def _size_label(value: float) -> str:
    if value <= 0:
        return "tamaño variable"
    if value >= 1024 ** 3:
        return f"{value / 1024 ** 3:.2f} GB"
    return f"{value / 1024 ** 2:.1f} MB"


def _codec_base(codec: str) -> str:
    return str(codec or "unknown").split(".")[0].lower()


def preferred_merge_container(video: dict, audio: dict) -> str:
    """Elige un contenedor de fusión predecible sin recodificar los streams."""
    if not video or video.get("combined"):
        return ""
    video_ext = str(video.get("ext") or "").lower()
    audio_ext = str(audio.get("ext") or "").lower()
    video_codec = _codec_base(video.get("vcodec", ""))
    audio_codec = _codec_base(audio.get("acodec", ""))
    if (
        video_ext == "mp4"
        and video_codec in {"h264", "avc1", "hevc", "h265"}
        and audio_ext in {"m4a", "mp4"}
        and audio_codec in {"aac", "mp4a"}
    ):
        return "mp4"
    if video_ext == "webm" and audio_ext in {"webm", "opus", "ogg"}:
        return "webm"
    return ""


def build_media_choices(info: dict) -> dict[str, Any]:
    video: list[dict] = []
    audio: list[dict] = []
    for fmt in info.get("formats") or []:
        kind = classify_format(fmt)
        ext = str(fmt.get("ext") or "?")
        vcodec = str(fmt.get("vcodec") or "none")
        acodec = str(fmt.get("acodec") or "none")
        size = _size(fmt)
        language = str(fmt.get("language") or "")
        language_key = language.replace("_", "-").lower()
        language_name = LANG_CODE_MAP.get(language_key, LANG_CODE_MAP.get(language_key.split("-")[0], language))
        if kind == "audio":
            compatible = (
                _codec_base(acodec) in EDITOR_FRIENDLY_CRITERIA["compatible_acodecs"]
                and ext in {"m4a", "mp4", "aac", "mp3", "wav", "ac3"}
            )
        else:
            compatible = (
                (_codec_base(vcodec) in EDITOR_FRIENDLY_CRITERIA["compatible_vcodecs"] or vcodec == "none")
                and (_codec_base(acodec) in EDITOR_FRIENDLY_CRITERIA["compatible_acodecs"] or acodec == "none")
                and ext in EDITOR_FRIENDLY_CRITERIA["compatible_exts"]
            )
        marker = "✨" if compatible else "⚠"
        common = {
            "formatId": str(fmt.get("format_id") or ""),
            "ext": ext,
            "vcodec": vcodec,
            "acodec": acodec,
            "width": int(fmt.get("width") or 0),
            "height": int(fmt.get("height") or 0),
            "fps": float(fmt.get("fps") or 0),
            "abr": float(fmt.get("abr") or 0),
            "tbr": float(fmt.get("tbr") or 0),
            "filesize": size,
            "language": language,
            "combined": acodec not in {"", "none"} and vcodec not in {"", "none"},
            "compatible": compatible,
            "raw": fmt,
        }
        if kind == "video":
            height = common["height"]
            resolution = f"{height}p" if height else str(fmt.get("resolution") or "Video")
            fps = f" · {common['fps']:.0f} fps" if common["fps"] else ""
            codecs = f"{vcodec}+{acodec}" if common["combined"] else vcodec
            audio_tag = f" · {language_name}" if language_name else ""
            common["label"] = f"{resolution}{fps} · {ext.upper()} · {codecs}{audio_tag} · {_size_label(size)} {marker}"
            video.append(common)
        elif kind == "audio":
            bitrate = common["abr"] or common["tbr"]
            rate = f"{bitrate:.0f} kbps" if bitrate else "Audio"
            lang = f"{language_name} · " if language_name else ""
            common["label"] = f"{lang}{rate} · {acodec} · {ext.upper()} · {_size_label(size)} {marker}"
            audio.append(common)

    video.sort(key=lambda item: (-item["height"], -item["fps"], -item["tbr"]))
    audio.sort(key=lambda item: (
        LANGUAGE_ORDER.get(item["language"].replace("_", "-").lower(), DEFAULT_PRIORITY),
        0 if item["compatible"] else 1,
        -(item["abr"] or item["tbr"]),
    ))
    subtitles: dict[str, list[dict]] = defaultdict(list)
    for automatic, source in ((False, info.get("subtitles", {})), (True, info.get("automatic_captions", {}))):
        for language, entries in source.items():
            grouped = {"spa": "es", "eng": "en", "jpn": "ja", "fra": "fr", "deu": "de", "por": "pt", "ita": "it", "kor": "ko", "rus": "ru"}.get(
                language.replace("_", "-").split("-")[0].lower(),
                language.replace("_", "-").split("-")[0].lower(),
            )
            for entry in entries:
                subtitles[grouped].append({**entry, "lang": language, "automatic": automatic})

    subtitle_languages = sorted(subtitles, key=lambda code: (LANGUAGE_ORDER.get(code, DEFAULT_PRIORITY), code))
    return {
        "video": video,
        "audio": audio,
        "subtitles": dict(subtitles),
        "subtitleLanguages": [
            {"code": code, "label": LANG_CODE_MAP.get(code, code)} for code in subtitle_languages
        ],
        "hasVideo": bool(video),
        "hasAudio": bool(audio or any(item["combined"] for item in video)),
    }


def seconds_from_time(value: str | None) -> float:
    if not value:
        return 0.0
    parts = str(value).strip().split(":")
    try:
        numbers = [float(part or 0) for part in parts]
    except ValueError:
        return 0.0
    while len(numbers) < 3:
        numbers.insert(0, 0.0)
    return numbers[-3] * 3600 + numbers[-2] * 60 + numbers[-1]


def safe_filename(value: str) -> str:
    from src.core.text_utils import clean_filename_text

    cleaned = clean_filename_text(value).strip().rstrip(". ")
    return cleaned or "archivo_xomacito"
