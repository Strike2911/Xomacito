import pytest
from src.core.video_quality import quality_preserving_selector, validate_download_resolution
from src.core.ytdlp_runtime import load_ytdlp
from src.ui.download_controller import editor_mp4_fallback_options


def stream(identifier, width, height, fps, vcodec="vp9", acodec="none", ext="webm"):
    return dict(format_id=identifier, width=width, height=height, fps=fps,
                vcodec=vcodec, acodec=acodec, ext=ext, url="https://example.test/" + identifier)


def choose(formats, selected):
    with load_ytdlp().YoutubeDL({"quiet": True}) as ydl:
        return list(ydl.build_format_selector(quality_preserving_selector(selected))(
            dict(formats=formats, has_merged_format=False, incomplete_formats=False)))


@pytest.mark.parametrize("width,height", [(1920, 1080), (1080, 1920)])
def test_retry_rejects_low_mp4_and_preserves_hd_vp9(width, height):
    selected = dict(width=width, height=height, fps=60)
    low = stream("low", width//3, height//3, 30, "avc1", "mp4a", "mp4")
    audio = stream("audio", 0, 0, 0, "none", "opus")
    hd = stream("hd", width, height, 60)
    result = choose([audio, low, hd], selected)
    assert result[0]["requested_formats"][0]["format_id"] == "hd"
    assert choose([audio, low], selected) == []
    assert choose([audio, stream("slow", width, height, 30)], selected) == []


@pytest.mark.parametrize("width,height", [(640,360), (360,640), (0,0)])
def test_file_check_rejects_lower_resolution(width, height):
    with pytest.raises(RuntimeError, match="inferior"):
        validate_download_resolution({"streams": [dict(codec_type="video", width=width, height=height)]},
                                     dict(width=1920,height=1080))


def test_file_check_accepts_rotation_and_ignores_cover():
    validate_download_resolution({"streams": [dict(codec_type="video", width=1080,height=1920)]},
                                 dict(width=1920,height=1080))
    with pytest.raises(RuntimeError):
        validate_download_resolution({"streams": [dict(codec_type="video", width=1920,height=1080,
            disposition={"attached_pic": 1})]}, dict(width=1920,height=1080))


def test_editor_conversion_keeps_resolution_and_frame_rate():
    options = editor_mp4_fallback_options({"resolution_change_enabled": True, "res_width": 360,
                                          "fps_force_enabled": True, "fps_value": "24"})
    assert not options["resolution_change_enabled"]
    assert not options["fps_force_enabled"]
    assert options["recode_profile_name"] == "Alta Calidad (CRF 18)"
