"""Inspect actual streams and explicitly prepare media for Premiere.

Container suffixes are never evidence of codec support. This service does not
download lower-resolution alternatives or modify the source file.
"""
from fractions import Fraction
from pathlib import Path
import os
import re
import tempfile

from .exceptions import UserCancelledError
from .file_naming import next_available_path
from .processor import pixel_format_has_alpha, validate_recode_result_info
from .video_quality import validate_download_resolution

ORIGINAL = "Original · sin convertir"
PREMIERE = "Premiere · alta calidad"
DELIVERIES = [ORIGINAL, PREMIERE]
VIDEO_CODECS = {"h264", "hevc", "prores", "dnxhd", "mpeg2video", "mjpeg", "dvvideo"}
AUDIO_CODECS = {"aac", "mp3", "ac3", "pcm_s16le", "pcm_s24le", "pcm_s32le", "pcm_f32le"}
CONTAINERS = {".mp4", ".mov", ".m4v", ".mxf", ".avi", ".mts", ".m2ts"}


def video_stream(info):
    return next((s for s in (info or {}).get("streams", []) if s.get("codec_type") == "video"
                 and not (s.get("disposition") or {}).get("attached_pic")), {})


def frame_rate(stream):
    for key in ("avg_frame_rate", "r_frame_rate", "fps"):
        try:
            value = float(Fraction(str(stream.get(key) or 0)))
            if value > 0:
                return value
        except (ValueError, ZeroDivisionError):
            pass
    return 0.0


def compatibility_issue(info, path):
    video = video_stream(info)
    if not video:
        return ""  # Audio and stills have their own import paths.
    codec = video.get("codec_name", "desconocido")
    if codec not in VIDEO_CODECS:
        return f"El video usa {codec.upper()}; Premiere necesita un códec compatible."
    if Path(path).suffix.lower() not in CONTAINERS:
        return "El contenedor necesita prepararse para Premiere."
    audio = [s for s in info.get("streams", []) if s.get("codec_type") == "audio"]
    if any(s.get("codec_name") not in AUDIO_CODECS for s in audio):
        return "El audio necesita convertirse para Premiere; el video se conservará si es compatible."
    return ""


def conversion_plan(info, path, force_video=False):
    video = video_stream(info)
    if not video:
        raise ValueError("No se encontró una pista de video verificable.")
    audio = [s for s in info.get("streams", []) if s.get("codec_type") == "audio"]
    transcode = force_video or video.get("codec_name") not in VIDEO_CODECS
    alpha = pixel_format_has_alpha(video.get("pix_fmt")) or (video.get("tags") or {}).get("alpha_mode") == "1"
    # Do not silently flatten HDR/10-bit or alpha into SDR/8-bit H.264.
    depth_match = re.search(r"p(9|10|12|14|16)(?:le|be)?$", str(video.get("pix_fmt", "")))
    raw_depth = str(video.get("bits_per_raw_sample") or "0")
    depth = max(int(depth_match[1]) if depth_match else 8, int(raw_depth) if raw_depth.isdigit() else 0)
    if transcode and depth > 10:
        raise ValueError("La preparación automática admite hasta 10 bits. Este archivo tiene mayor profundidad; usa un perfil de edición avanzado para conservarla.")
    high_depth = (depth > 8
                  or video.get("color_transfer") in {"smpte2084", "arib-std-b67"})
    odd_size = int(video.get("width") or 0) % 2 or int(video.get("height") or 0) % 2
    prores = transcode and (high_depth or alpha or odd_size)
    container = ".mov" if prores or video.get("codec_name") in {"prores", "dnxhd", "dvvideo"} else ".mp4"
    threads = max(1, min(4, (os.cpu_count() or 2) // 2))
    params = ["-map", f"0:{video['index']}", "-map", "0:a?", "-sn", "-dn"]
    if prores:
        params += ["-c:v", "prores_ks", "-profile:v", "4" if alpha else "3",
                   "-pix_fmt", "yuva444p10le" if alpha else "yuv422p10le"]
    elif transcode:
        params += ["-c:v", "libx264", "-preset", "fast", "-crf", "18", "-pix_fmt", "yuv420p"]
    else:
        params += ["-c:v", "copy"]
    if transcode:
        params += ["-threads", str(threads), "-fps_mode", "passthrough"]
        color_filter = []
        for field, option in (("color_primaries", "-color_primaries"), ("color_transfer", "-color_trc"),
                              ("color_space", "-colorspace"), ("color_range", "-color_range")):
            if video.get(field) not in (None, "unknown", "unspecified"):
                params += [option, video[field]]
                filter_key = {"color_transfer": "color_trc", "color_space": "colorspace", "color_range": "range"}.get(field, field)
                color_filter.append(f"{filter_key}={video[field]}")
        if color_filter:
            params += ["-vf", "setparams=" + ":".join(color_filter)]
    if audio:
        params += ["-c:a", "copy"]
        for i, stream in enumerate(audio):
            if stream.get("codec_name") not in ({"aac", "mp3", "ac3"} if container == ".mp4" else AUDIO_CODECS):
                params += [f"-c:a:{i}", "pcm_s24le" if container == ".mov" else "aac"]
                if container == ".mp4":
                    params += [f"-b:a:{i}", f"{max(192, min(768, int(stream.get('channels') or 2) * 96))}k"]
    params += ["-movflags", "+faststart+write_colr"]
    return {"params": params, "container": container, "transcode": transcode,
            "decoder": "libvpx-vp9" if alpha and video.get("codec_name") == "vp9" else "libvpx" if alpha and video.get("codec_name") == "vp8" else "",
            "label": "ProRes · conserva color y profundidad" if prores else "H.264 · calidad alta" if transcode else "Video original · sin recodificar"}


def prepare_for_premiere(source, folder, processor, cancel, progress, *, trim=None, stem=None):
    """Called only after an explicit delivery choice or conversion confirmation."""
    source = Path(source)
    if cancel.is_set():
        raise UserCancelledError("Preparación cancelada.")
    info = processor.get_local_media_info(str(source))
    if not info or not info.get("streams"):
        raise ValueError("No se pudo verificar el archivo antes de prepararlo para Premiere.")
    if not video_stream(info):
        return str(source)
    if not compatibility_issue(info, source) and trim is None:
        return str(source)
    plan = conversion_plan(info, source, force_video=trim is not None)
    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=True)
    target = next_available_path(folder / ((stem or source.stem + "_Premiere") + plan["container"]))
    duration = float((info.get("format") or {}).get("duration") or 0)
    if trim is not None:
        start, end = trim
        end = end or duration
        if start < 0 or end <= start or (duration and end > duration + 0.5):
            raise ValueError("El recorte está fuera de la duración del archivo.")
        duration = end - start
        plan["params"] += ["-ss", str(start), "-t", str(duration)]
    progress(0, "Preparando para Premiere · " + plan["label"])
    # A private staging directory prevents autoimporters from picking up partial files.
    with tempfile.TemporaryDirectory(prefix=".xomacito-prepare-", dir=folder) as staging:
        temporary = Path(staging) / ("prepared" + plan["container"])
        pre_params = ["-threads", "2", "-noautorotate"]
        if plan["decoder"]:
            pre_params += ["-c:v", plan["decoder"]]
        processor.execute_recode({"input_file": str(source), "output_file": str(temporary),
            "ffmpeg_params": plan["params"], "pre_params": pre_params, "low_priority": True,
            "duration": duration, "mode": "Video+Audio", "output_container": plan["container"]}, progress, cancel)
        if cancel.is_set():
            raise UserCancelledError("Preparación cancelada.")
        output_info = processor.get_local_media_info(str(temporary))
        validate_recode_result_info(output_info, "Video+Audio", duration)
        if duration and abs(float(output_info["format"]["duration"]) - duration) > 0.25:
            raise ValueError("La copia no conservó la duración; el original se conserva.")
        expected = dict(video_stream(info), fps=frame_rate(video_stream(info)))
        validate_download_resolution(output_info, expected)
        output_video = video_stream(output_info)
        if expected.get("sample_aspect_ratio") not in (None, "0:1", "N/A") and expected["sample_aspect_ratio"] != output_video.get("sample_aspect_ratio"):
            raise ValueError("La copia cambió la proporción de los píxeles.")
        before_frames, after_frames = str(expected.get("nb_frames", "")), str(output_video.get("nb_frames", ""))
        if trim is None and before_frames.isdigit() and after_frames.isdigit() and before_frames != after_frames:
            raise ValueError("La copia cambió la cantidad de fotogramas.")
        for field in ("color_primaries", "color_transfer", "color_space", "color_range"):
            wanted = expected.get(field)
            actual = output_video.get(field)
            # H.264 and ProRes may omit the implicit limited-range flag.
            if field == "color_range" and not actual and str(output_video.get("pix_fmt", "")).startswith("yuv"):
                actual = "pc" if str(output_video["pix_fmt"]).startswith("yuvj") else "tv"
            if wanted not in (None, "unknown", "unspecified") and actual != wanted:
                raise ValueError("La copia no conservó los metadatos de color del original.")
        if (pixel_format_has_alpha(expected.get("pix_fmt")) or plan["decoder"]) and not pixel_format_has_alpha(output_video.get("pix_fmt")):
            raise ValueError("La copia no conservó la transparencia.")
        if compatibility_issue(output_info, target):
            raise ValueError("La copia no pasó la comprobación de códecs para Premiere.")
        before = [s for s in info.get("streams", []) if s.get("codec_type") == "audio"]
        after = [s for s in output_info.get("streams", []) if s.get("codec_type") == "audio"]
        if len(before) != len(after) or any(a.get("channels") != b.get("channels") for a, b in zip(before, after)):
            raise ValueError("La copia no conservó todas las pistas y canales de audio.")
        os.replace(temporary, target)
    return str(target)
