import pytest
from src.core.video_quality import quality_preserving_selector, validate_download_resolution
from src.core.ytdlp_runtime import load_ytdlp


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


@pytest.mark.parametrize("fps,compatible_size,expected", [(59.94, (1920, 1080), "native"),
    (30, (1920, 1080), "source"), (60, (1280, 720), "source"), (60, (1080, 1920), "source")])
def test_native_editor_preference_never_trades_dimensions_or_frame_rate(fps, compatible_size, expected):
    from src.core.video_quality import prefer_equivalent_editor_stream
    formats = {"source": dict(width=1920, height=1080, fps=60),
               "native": dict(width=compatible_size[0], height=compatible_size[1], fps=fps, compatible=True)}
    assert prefer_equivalent_editor_stream(formats["source"], formats.values()) is formats[expected]


@pytest.mark.parametrize("width,height,label", [(1920, 1080, "1080p"), (1080, 1920, "1080p"),
                                              (2160, 3840, "4K")])
def test_playlist_quality_filters_preserve_landscape_and_portrait(width, height, label):
    from src.core.batch_processor import QueueManager
    options = {}
    QueueManager._apply_playlist_quality(None, options, "Video+Audio", label)
    audio = stream("audio", 0, 0, 0, "none", "opus")
    low = stream("low", width//3, height//3, 30, "avc1", "mp4a", "mp4")
    desired = stream("desired", width, height, 60)
    with load_ytdlp().YoutubeDL({"quiet": True}) as ydl:
        selector = ydl.build_format_selector(options["format_selector"])
        def select(formats):
            return list(selector(dict(formats=formats, has_merged_format=False, incomplete_formats=False)))
        assert select([audio, low, desired])[0]["requested_formats"][0]["format_id"] == "desired"
        assert select([audio, low]) == []
