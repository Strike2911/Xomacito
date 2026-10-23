"""Regressions for portrait resolution, frame rate and silent quality changes."""
import os
import threading
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from src.core.video_quality import validate_download_resolution
from src.ui.media_logic import build_media_choices
from src.ui.quick_options import preferences
from src.ui.quick_runner import choose_video


def video(width, height, fps=30, compatible=False):
    return dict(width=width, height=height, fps=fps, compatible=compatible,
                format_id=f"{width}-{height}-{fps}", vcodec="avc1" if compatible else "vp9",
                acodec="none", ext="mp4" if compatible else "webm", tbr=1000)


def test_portrait_1080p_is_not_downgraded_to_360p():
    formats = {"360": video(360, 640), "720": video(720, 1280), "1080": video(1080, 1920)}
    assert choose_video(formats, "1080p") == "1080"


def test_quick_mode_does_not_trade_60fps_for_a_compatible_codec():
    formats = {"smooth": video(1920, 1080, 60), "compatible": video(1920, 1080, 30, True)}
    assert choose_video(formats, "1080p") == "smooth"


def test_unknown_dimensions_do_not_beat_a_known_stream():
    assert choose_video({"unknown": {}, "hd": video(1920, 1080)}, "720p") == "hd"


def test_portrait_label_uses_short_edge_and_shows_actual_dimensions():
    choice = build_media_choices({"formats": [video(1080, 1920)]})["video"][0]
    assert choice["label"].startswith("1080p")
    assert "1080×1920" in choice["label"]


def test_new_preferences_use_best_but_keep_explicit_saved_quality():
    assert preferences({}, ".")["quality"] == "Mejor disponible"
    assert preferences({"quality": "720p"}, ".")["quality"] == "720p"


@pytest.mark.parametrize("rate", ["30/1", "0/0", None])
def test_output_check_rejects_lost_or_unverifiable_fps(rate):
    info = {"streams": [dict(codec_type="video", width=1920, height=1080, avg_frame_rate=rate)]}
    with pytest.raises(RuntimeError, match="FPS"):
        validate_download_resolution(info, video(1920, 1080, 60))


def test_output_check_accepts_fractional_rate_and_rotation():
    info = {"streams": [dict(codec_type="video", width=1080, height=1920, avg_frame_rate="60000/1001")]}
    validate_download_resolution(info, video(1920, 1080, 60))


def test_youtube_analysis_does_not_force_the_360p_embedded_catalog(monkeypatch):
    from src.ui.download_controller import DownloadController
    calls = []
    def extract(url, options, download=False):
        calls.append(options)
        # Regression recorded on K8jWXGm57TU: embedded exposes only 360p.
        embedded = options.get("extractor_args", {}).get("youtube", {}).get("player_client") == ["web_embedded"]
        return {"id": "test", "formats": [video(640, 360) if embedded else video(2560, 1440, 60)]}
    monkeypatch.setattr("src.ui.download_controller.extract_info_resilient", extract)
    controller = SimpleNamespace(cancellation=threading.Event(), _cookie_options=lambda url: ({}, False))
    info = DownloadController._analyze_url_worker(controller, "https://www.youtube.com/watch?v=K8jWXGm57TU")
    assert build_media_choices(info)["video"][0]["height"] == 1440
    assert len(calls) == 1


@pytest.mark.parametrize("flag", ["draft", "prerelease"])
def test_updater_does_not_offer_a_withdrawn_or_unstable_release(flag):
    from src.core.app_updater import check_for_app_update
    session = Mock()
    session.get.return_value.json.return_value = {"tag_name": "v4.0.44", flag: True}
    result = check_for_app_update("4.0.42", session=session)
    assert not result["update_available"]
    assert "installer_url" not in result


def test_quick_job_stops_instead_of_silently_delivering_360p(tmp_path):
    from tests.test_quick_workflow import Settings, DeferredPool, ROOT, APP
    from src.ui.quick_controller import QuickController
    from src.ui.presets import PresetStore
    settings = Settings(tmp_path)
    quick = QuickController(ROOT, settings, DeferredPool(), object(), PresetStore(settings), "test")
    runner = quick.runner
    runner.quick_options = {**preferences({}, str(tmp_path)), "quality": "1080p"}
    runner.start = Mock()
    runner._operation_error = Mock()
    try:
        runner._apply_url_analysis({"id": "x", "title": "test", "duration": 2,
                                    "formats": [video(640, 360)]})
        runner.start.assert_not_called()
        assert "1080p" in runner._operation_error.call_args.args[0]
        assert "360p" in runner._operation_error.call_args.args[0]
    finally:
        quick.shutdown()
        APP.processEvents()
