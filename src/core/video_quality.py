"""Keep retries within the video quality the user selected."""
from fractions import Fraction


def video_dimensions(video):
    return tuple(int(video.get(key) or (video.get("raw") or {}).get(key) or 0)
                 for key in ("width", "height"))


def video_resolution(video):
    """A portrait 1080×1920 stream is 1080p, just like 1920×1080."""
    dimensions = video_dimensions(video)
    return min(dimensions) if all(dimensions) else max(dimensions)


def video_quality_key(video):
    width, height = video_dimensions(video)
    return (video_resolution(video), width * height,
            float(video.get("fps") or (video.get("raw") or {}).get("fps") or 0))


def quality_preserving_selector(video):
    bounds = ""
    for key in ("width", "height"):
        value = int(video.get(key) or (video.get("raw") or {}).get(key) or 0)
        if value:
            bounds += f"[{key}>={value}]"
    fps = float(video.get("fps") or (video.get("raw") or {}).get("fps") or 0)
    if fps:
        bounds += f"[fps>={max(1, fps - 0.5):g}]"
    return f"bestvideo{bounds}+bestaudio/best{bounds}"


def prefer_equivalent_editor_stream(best, formats):
    """Prefer native editing only at the same dimensions and frame-rate class."""
    width, height = video_dimensions(best)
    fps = video_quality_key(best)[2]
    equivalents = [fmt for fmt in formats if fmt.get("compatible")
                   and video_dimensions(fmt) == (width, height)
                   and abs(video_quality_key(fmt)[2] - fps) <= 0.5]
    return max(equivalents, key=lambda fmt: float(fmt.get("tbr") or 0), default=best)


def validate_download_resolution(info, selected):
    expected = sorted(video_dimensions(selected))
    expected_fps = float(selected.get("fps") or (selected.get("raw") or {}).get("fps") or 0)
    if not any(expected) and not expected_fps:
        return
    streams = [s for s in (info or {}).get("streams", []) if s.get("codec_type") == "video"
               and not (s.get("disposition") or {}).get("attached_pic")]
    stream = max(streams, key=video_quality_key, default={})
    actual = sorted(video_dimensions(stream))
    if any(wanted and got < wanted for got, wanted in zip(actual, expected)):
        raise RuntimeError(
            f"El archivo recibido tiene {actual[0]}×{actual[1]}, inferior a la resolución "
            f"seleccionada ({expected[0]}×{expected[1]}). No se dará por completada la descarga. "
            "Vuelve a analizar el enlace para renovar los formatos disponibles."
        )
    if expected_fps:
        actual_fps = 0.0
        for field in ("avg_frame_rate", "r_frame_rate"):
            try:
                actual_fps = float(Fraction(str(stream.get(field) or "0")))
            except (ValueError, ZeroDivisionError):
                continue
            if actual_fps > 0:
                break
        if actual_fps < expected_fps - 0.5:
            raise RuntimeError(
                f"El archivo recibido tiene {actual_fps:g} FPS verificables; se seleccionaron "
                f"{expected_fps:g} FPS. No se dará por completada la descarga. "
                "Vuelve a analizar el enlace para renovar los formatos disponibles."
            )
