"""Local analysis and hardware-aware recipes for Image Studio.

The analyser is deliberately small: it works on a thumbnail and never uploads the
user's media.  Its recommendations are hints, not semantic classifications.  The
processing engines still run locally through ONNX Runtime and NCNN/Vulkan.
"""

from __future__ import annotations

import ctypes
import math
import os
import platform
from pathlib import Path
from typing import Any

from PIL import Image, ImageFilter, ImageStat


PERFORMANCE_PROFILES = (
    "Automático",
    "Priorizar calidad",
    "Priorizar velocidad",
)


def _available_ram_gb() -> float:
    """Return currently available RAM without adding a psutil dependency."""
    if os.name == "nt":
        class MemoryStatus(ctypes.Structure):
            _fields_ = [
                ("length", ctypes.c_ulong),
                ("memory_load", ctypes.c_ulong),
                ("total_phys", ctypes.c_ulonglong),
                ("avail_phys", ctypes.c_ulonglong),
                ("total_page_file", ctypes.c_ulonglong),
                ("avail_page_file", ctypes.c_ulonglong),
                ("total_virtual", ctypes.c_ulonglong),
                ("avail_virtual", ctypes.c_ulonglong),
                ("avail_extended_virtual", ctypes.c_ulonglong),
            ]

        status = MemoryStatus()
        status.length = ctypes.sizeof(MemoryStatus)
        try:
            if ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(status)):
                return round(status.avail_phys / (1024 ** 3), 1)
        except (AttributeError, OSError):
            pass
    try:
        page_size = os.sysconf("SC_PAGE_SIZE")
        pages = os.sysconf("SC_AVPHYS_PAGES")
        return round((page_size * pages) / (1024 ** 3), 1)
    except (AttributeError, OSError, ValueError):
        return 0.0


def resolve_ort_providers(available: list[str] | tuple[str, ...], prefer_gpu: bool = True) -> list[str]:
    """Choose only providers that ONNX Runtime actually exposes on this machine."""
    available = list(available or [])
    if not available:
        return ["CPUExecutionProvider"]
    if prefer_gpu:
        for provider in (
            "TensorrtExecutionProvider",
            "CUDAExecutionProvider",
            "DmlExecutionProvider",
            "CoreMLExecutionProvider",
        ):
            if provider in available:
                result = [provider]
                if "CPUExecutionProvider" in available:
                    result.append("CPUExecutionProvider")
                return result
    if "CPUExecutionProvider" in available:
        return ["CPUExecutionProvider"]
    return [available[0]]


def detect_hardware(upscayl_exe: str | os.PathLike[str] | None = None) -> dict[str, Any]:
    available_providers: list[str] = []
    try:
        import onnxruntime as ort

        available_providers = list(ort.get_available_providers())
    except Exception:
        pass

    selected = resolve_ort_providers(available_providers, prefer_gpu=True)
    provider = selected[0]
    provider_names = {
        "TensorrtExecutionProvider": "NVIDIA TensorRT",
        "CUDAExecutionProvider": "NVIDIA CUDA",
        "DmlExecutionProvider": "DirectML",
        "CoreMLExecutionProvider": "Apple Core ML",
        "CPUExecutionProvider": "CPU",
    }
    cpu_threads = max(1, os.cpu_count() or 1)
    ram_gb = _available_ram_gb()
    vulkan_ready = bool(upscayl_exe and Path(upscayl_exe).is_file())
    acceleration = provider_names.get(provider, provider.replace("ExecutionProvider", ""))
    label = f"{acceleration} · {cpu_threads} hilos"
    if vulkan_ready:
        label += " · Vulkan listo"
    detail_parts = [f"ONNX: {acceleration}"]
    if ram_gb:
        detail_parts.append(f"RAM libre: {ram_gb:.1f} GB")
    detail_parts.append("Upscayl/Vulkan listo" if vulkan_ready else "Upscayl se instalará al usarlo")
    return {
        "label": label,
        "detail": " · ".join(detail_parts),
        "ortProviders": available_providers,
        "ortProvider": provider,
        "cpuThreads": cpu_threads,
        "availableRamGb": ram_gb,
        "vulkanReady": vulkan_ready,
    }


def performance_recipe(profile: str, hardware: dict[str, Any] | None = None) -> dict[str, Any]:
    hardware = hardware or {}
    cpu_threads = int(hardware.get("cpuThreads") or os.cpu_count() or 1)
    ram_gb = float(hardware.get("availableRamGb") or 0)
    effective = profile if profile in PERFORMANCE_PROFILES else "Automático"
    if effective == "Automático":
        effective = "Equilibrado" if cpu_threads >= 8 and (not ram_gb or ram_gb >= 4) else "Priorizar velocidad"

    if effective == "Priorizar calidad":
        return {
            "effective": effective,
            "concurrency": "Máximo (Potente)" if cpu_threads >= 8 else "Equilibrado",
            "threads": "2:4:2" if cpu_threads >= 8 else "1:2:2",
            "tile": "0",
            "tta": True,
            "rembgQuality": "quality",
            "encoderPreset": "medium",
            "encoderCrf": 16,
        }
    if effective == "Priorizar velocidad":
        return {
            "effective": effective,
            "concurrency": "Máximo (Potente)" if cpu_threads >= 8 else "Equilibrado",
            "threads": "2:4:2" if cpu_threads >= 8 else "1:2:2",
            "tile": "0",
            "tta": False,
            "rembgQuality": "speed",
            "encoderPreset": "veryfast",
            "encoderCrf": 20,
        }
    return {
        "effective": "Equilibrado",
        "concurrency": "Máximo (Potente)" if cpu_threads >= 12 else "Equilibrado",
        "threads": "2:4:2" if cpu_threads >= 12 else "1:2:2",
        "tile": "0",
        "tta": False,
        "rembgQuality": "balanced",
        "encoderPreset": "fast",
        "encoderCrf": 18,
    }


def _face_present(image: Image.Image) -> bool:
    """Best-effort face detection; failure never blocks analysis."""
    try:
        import cv2
        import numpy as np

        cascade_path = Path(cv2.data.haarcascades) / "haarcascade_frontalface_default.xml"
        if not cascade_path.is_file():
            return False
        sample = image.convert("RGB")
        sample.thumbnail((640, 640), Image.Resampling.LANCZOS)
        gray = cv2.cvtColor(np.asarray(sample), cv2.COLOR_RGB2GRAY)
        classifier = cv2.CascadeClassifier(str(cascade_path))
        min_side = max(24, min(gray.shape[:2]) // 10)
        return len(classifier.detectMultiScale(gray, 1.12, 5, minSize=(min_side, min_side))) > 0
    except Exception:
        return False


def analyze_image(image_or_path: Image.Image | str | os.PathLike[str], *, source_path: str = "") -> dict[str, Any]:
    """Analyse a small local sample and return an explainable processing recipe."""
    close_image = not isinstance(image_or_path, Image.Image)
    image = Image.open(image_or_path) if close_image else image_or_path
    try:
        image.load()
        original_w, original_h = image.size
        sample = image.convert("RGB")
        sample.thumbnail((512, 512), Image.Resampling.LANCZOS)

        gray = sample.convert("L")
        edge = gray.filter(ImageFilter.FIND_EDGES)
        sharpness = ImageStat.Stat(edge).mean[0] / 255.0
        contrast = ImageStat.Stat(gray).stddev[0] / 128.0
        saturation = ImageStat.Stat(sample.convert("HSV")).mean[1] / 255.0
        quantized = sample.quantize(colors=64)
        histogram = quantized.histogram()
        active_colors = sum(1 for count in histogram if count > sample.width * sample.height * 0.002)

        has_face = _face_present(sample)
        suffix = Path(source_path or getattr(image, "filename", "")).suffix.lower()
        file_size = 0
        try:
            file_size = Path(source_path).stat().st_size if source_path else 0
        except OSError:
            pass
        bytes_per_pixel = file_size / max(1, original_w * original_h)
        compressed = suffix in {".jpg", ".jpeg"} and bytes_per_pixel and bytes_per_pixel < 0.38

        illustration_score = 0.0
        illustration_score += 0.35 if active_colors <= 28 else 0.0
        illustration_score += 0.25 if saturation >= 0.34 else 0.0
        illustration_score += 0.25 if sharpness >= 0.09 else 0.0
        illustration_score += 0.15 if contrast >= 0.42 else 0.0

        if has_face:
            content = "Retrato o persona"
            kind = "portrait"
        elif illustration_score >= 0.55:
            content = "Ilustración, anime o gráfico"
            kind = "illustration"
        else:
            content = "Fotografía o imagen real"
            kind = "photo"

        if compressed:
            issue = "Compresión JPEG visible"
        elif sharpness < 0.045:
            issue = "Detalle suave"
        else:
            issue = "Detalle estable"

        if kind == "portrait":
            rembg_model = "Personas y retratos"
            rembg_reason = "prioriza cabello, rostro y silueta humana"
        elif kind == "illustration" or sharpness >= 0.12:
            rembg_model = "Cabello y bordes finos"
            rembg_reason = "prioriza contornos finos y formas complejas"
        else:
            rembg_model = "Objetos y productos"
            rembg_reason = "equilibrio de precisión para objetos y fotografía"

        if kind == "illustration":
            upscale_model = "Real-ESRGAN (Anime / Ilustración)"
            upscale_reason = "conserva líneas y colores planos"
        elif compressed:
            upscale_model = "Real-ESRGAN (General / Fotografía)"
            upscale_reason = "recupera textura y suaviza artefactos de compresión"
        else:
            upscale_model = "Real-ESRGAN (General / Fotografía)"
            upscale_reason = "recupera textura con menos aspecto artificial"

        megapixels = original_w * original_h / 1_000_000
        confidence = min(0.94, 0.58 + abs(illustration_score - 0.5) * 0.55 + (0.08 if has_face else 0))
        return {
            "width": original_w,
            "height": original_h,
            "megapixels": round(megapixels, 2),
            "content": content,
            "kind": kind,
            "issue": issue,
            "hasFace": has_face,
            "confidence": round(confidence, 2),
            "rembgModel": rembg_model,
            "rembgReason": rembg_reason,
            "upscaleModel": upscale_model,
            "upscaleReason": upscale_reason,
            "technical": f"{original_w} × {original_h} · {megapixels:.1f} MP",
        }
    finally:
        if close_image:
            image.close()


def estimate_output(analysis: dict[str, Any], scale: int | str = 1, task: str = "convert") -> str:
    try:
        factor = int(str(scale).replace("×", "").replace("x", ""))
    except (TypeError, ValueError):
        factor = 1
    if task not in {"upscaleImage", "upscaleVideo"}:
        factor = 1
    width = int(analysis.get("width") or 0) * factor
    height = int(analysis.get("height") or 0) * factor
    if not width or not height:
        return "Importa un archivo para estimar la salida"
    mp = width * height / 1_000_000
    raw_mb = width * height * 4 / (1024 ** 2)
    return f"Salida estimada: {width} × {height} · {mp:.1f} MP · ~{raw_mb:.0f} MB en memoria"
