from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

from src.core.image_converter import ImageConverter
from src.core.image_intelligence import (
    analyze_image,
    estimate_output,
    performance_recipe,
    resolve_ort_providers,
)
from src.core.video_upscaler import VideoUpscaler


def test_provider_resolution_never_invents_directml():
    assert resolve_ort_providers(["CPUExecutionProvider"], prefer_gpu=True) == [
        "CPUExecutionProvider"
    ]
    assert resolve_ort_providers(
        ["DmlExecutionProvider", "CPUExecutionProvider"], prefer_gpu=True
    ) == ["DmlExecutionProvider", "CPUExecutionProvider"]


def test_local_analysis_is_explainable_and_estimates_output():
    image = Image.new("RGB", (320, 180), "#1b2440")
    draw = ImageDraw.Draw(image)
    draw.rectangle((30, 25, 285, 150), fill="#f05a7e", outline="white", width=5)
    analysis = analyze_image(image)

    assert analysis["width"] == 320
    assert analysis["height"] == 180
    assert analysis["content"]
    assert analysis["upscaleModel"]
    assert analysis["rembgModel"]
    assert "640 × 360" in estimate_output(analysis, "2", "upscaleImage")


def test_performance_profiles_change_real_engine_settings():
    hardware = {"cpuThreads": 16, "availableRamGb": 12}
    quality = performance_recipe("Priorizar calidad", hardware)
    fast = performance_recipe("Priorizar velocidad", hardware)

    assert quality["tta"] is True
    assert quality["encoderCrf"] < fast["encoderCrf"]
    assert fast["threads"] == "2:4:2"


def test_probability_mask_is_not_stretched_per_image():
    class Input:
        name = "input"

    class Session:
        def get_inputs(self):
            return [Input()]

        def run(self, *_args, **_kwargs):
            return [np.full((1, 1, 4, 4), 0.25, dtype=np.float32)]

    converter = ImageConverter.__new__(ImageConverter)
    result = converter._process_onnx_manual(
        Image.new("RGB", (8, 8), "red"), Session(), (4, 4)
    )
    alpha = result.getchannel("A")
    low, high = alpha.getextrema()
    assert 62 <= low <= 65
    assert low == high


def test_image_studio_page_explains_its_empty_state():
    qml = Path("src/ui/qml/pages/ImageStudioPage.qml").read_text(encoding="utf-8")
    assert "Estudio en preparación" in qml
    assert "permanecerá vacío" in qml


def test_long_videos_use_bounded_chunk_pipeline(tmp_path):
    upscaler = VideoUpscaler.__new__(VideoUpscaler)
    upscaler.models_root = str(tmp_path)
    upscaler._check_dependencies = lambda: None
    upscaler._get_video_info = lambda _path: {
        "fps": "30", "ext": ".mp4", "has_audio": True, "duration": 61.0,
        "width": 1920, "height": 1080, "estimated_frames": 1830,
    }
    observed = {}

    def chunked(input_path, output_path, info, options, engine, model, scale, ext_out):
        observed.update({"input": input_path, "output": output_path, "scale": scale, "ext": ext_out})
        return output_path

    upscaler._upscale_video_chunked = chunked
    result = upscaler.upscale_video(
        "long.mp4", str(tmp_path / "result.mp4"),
        {"upscale_engine": "Upscayl", "upscale_model_friendly": "Real-ESRGAN (General / Fotografía)",
         "upscale_scale": "2", "upscale_container": ".mp4"},
    )

    assert result.endswith("result.mp4")
    assert observed["scale"] == "2"
    assert observed["ext"] == ".mp4"


def test_windows_build_requests_directml_runtime():
    requirements = Path("requirements.txt").read_text(encoding="utf-8")
    assert "onnxruntime-directml==1.24.4" in requirements
