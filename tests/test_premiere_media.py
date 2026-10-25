import copy
import threading
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from src.core.exceptions import UserCancelledError
from src.core.premiere_media import compatibility_issue, conversion_plan, prepare_for_premiere, PREMIERE


def media(codec="vp9", audio="aac", **video):
    return {"format": {"duration": "2"}, "streams": [
        {"index": 0, "codec_type": "video", "codec_name": codec, "width": 1080, "height": 1920,
         "avg_frame_rate": "60000/1001", "pix_fmt": "yuv420p", **video},
        {"index": 1, "codec_type": "audio", "codec_name": audio, "channels": 2}]}


@pytest.mark.parametrize("codec", ["vp9", "av1", "vp8"])
def test_mp4_extension_does_not_hide_incompatible_video(codec):
    info = media(codec)
    assert codec.upper() in compatibility_issue(info, "video.mp4")
    plan = conversion_plan(info, "video.mp4")
    assert plan["params"][plan["params"].index("-c:v") + 1] == "libx264"
    assert not any(flag in plan["params"] for flag in ("-r", "-vf", "-s", "-b:v"))
    assert int(plan["params"][plan["params"].index("-threads") + 1]) <= 4


@pytest.mark.parametrize("fields", [{"pix_fmt": "yuv420p10le", "color_transfer": "smpte2084"},
                                  {"pix_fmt": "yuva420p"}, {"width": 1079}])
def test_depth_alpha_and_odd_sizes_use_prores_without_scaling(fields):
    plan = conversion_plan(media(**fields), "video.webm")
    assert plan["container"] == ".mov"
    assert "prores_ks" in plan["params"]
    assert not any("scale=" in arg or "fps=" in arg for arg in plan["params"])


def test_only_audio_is_encoded_when_video_is_compatible():
    plan = conversion_plan(media("h264", "opus"), "video.mkv")
    assert not plan["transcode"]
    assert plan["params"][plan["params"].index("-c:v") + 1] == "copy"
    assert plan["params"][plan["params"].index("-c:a:0") + 1] == "aac"


def fake_processor(source, original, produced, cancel=None, fail=False):
    def run(options, *_):
        Path(options["output_file"]).write_bytes(b"converted")
        if cancel:
            cancel.set()
        if fail:
            raise RuntimeError("disk full")
    return SimpleNamespace(
        get_local_media_info=lambda path: copy.deepcopy(original if str(path) == str(source) else produced),
        execute_recode=Mock(side_effect=run))


@pytest.mark.parametrize("failure", [None, "resolution", "fps", "audio", "codec", "cancel", "encode", "color"])
def test_atomic_copy_validates_media_and_preserves_original(tmp_path, failure):
    source = tmp_path / "original.mp4"
    source.write_bytes(b"original")
    before, after = media(), media("h264")
    event = threading.Event()
    if failure == "resolution": after["streams"][0]["width"] = 360
    if failure == "fps": after["streams"][0]["avg_frame_rate"] = "30/1"
    if failure == "audio": after["streams"].pop()
    if failure == "codec": after = media()
    if failure == "color": before["streams"][0]["color_primaries"] = "bt2020"
    processor = fake_processor(source, before, after, event if failure == "cancel" else None, failure == "encode")
    if failure:
        with pytest.raises((ValueError, RuntimeError, UserCancelledError)):
            prepare_for_premiere(source, tmp_path, processor, event, lambda *a: None)
        assert list(tmp_path.iterdir()) == [source]
    else:
        output = prepare_for_premiere(source, tmp_path, processor, event, lambda *a: None)
        assert Path(output).name == "original_Premiere.mp4"
        assert Path(output).read_bytes() == b"converted"
    assert source.read_bytes() == b"original"


def test_already_compatible_file_is_not_reencoded(tmp_path):
    source = tmp_path / "good.mp4"
    processor = SimpleNamespace(get_local_media_info=lambda p: media("h264"), execute_recode=Mock())
    assert prepare_for_premiere(source, tmp_path, processor, threading.Event(), Mock()) == str(source)
    processor.execute_recode.assert_not_called()


def test_premiere_delivery_checks_actual_downloaded_codec_not_analysis(tmp_path, monkeypatch):
    from src.ui.download_controller import DownloadController
    source = tmp_path / "fallback.mp4"; source.write_bytes(b"vp9")
    output = str(tmp_path / "fallback_Premiere.mp4")
    prepare = Mock(return_value=output)
    monkeypatch.setattr("src.ui.download_controller.prepare_for_premiere", prepare)
    controller = SimpleNamespace(_image_post=False, _video_map={}, cancellation=threading.Event(),
        _download_worker=Mock(return_value=str(source)), ffmpeg=object(), _ffmpeg_progress=Mock())
    options = {"mode": "Video+Audio", "output_path": str(tmp_path), "videoDelivery": PREMIERE}
    assert DownloadController._process_worker(controller, options) == output
    assert prepare.call_args.args[0] == str(source)


@pytest.mark.parametrize("automatic,answer,expected_copies", [(True, "", 0), (False, "Cancelar", 0), (False, "Crear copia y enviar", 1)])
def test_bridge_never_converts_without_explicit_consent(tmp_path, monkeypatch, automatic, answer, expected_copies):
    from tests.test_quick_workflow import APP
    from src.ui.premiere_preparation import PremierePreparation
    dialogs = SimpleNamespace(ask=Mock(return_value=answer))
    prep = PremierePreparation(SimpleNamespace(root=tmp_path), dialogs)
    prep.processor_factory = lambda: SimpleNamespace(get_local_media_info=lambda p: media())
    convert = Mock(return_value=str(tmp_path / "ready.mp4"))
    monkeypatch.setattr("src.ui.premiere_preparation.prepare_for_premiere", convert)
    if not automatic and answer == "Cancelar":
        with pytest.raises(UserCancelledError): prep._worker(["clip.mp4"], {"automatic": automatic})
    else:
        outputs, skipped = prep._worker(["clip.mp4"], {"automatic": automatic})
        assert bool(skipped) == automatic
        assert bool(outputs) != automatic
    assert convert.call_count == expected_copies
    if automatic: dialogs.ask.assert_not_called()


@pytest.mark.parametrize("encoder,container,trim", [("libvpx-vp9", ".mp4", None), ("libaom-av1", ".mp4", None),
                                                  ("libvpx-vp9", ".mp4", (0.2, 0.7)), ("libx264", ".mkv", None)])
def test_real_conversion_preserves_portrait_frames_and_audio(tmp_path, encoder, container, trim):
    import subprocess
    from src.core.processor import FFmpegProcessor
    processor = FFmpegProcessor()
    if not Path(processor.ffmpeg_path).is_file(): pytest.skip("FFmpeg not installed")
    source = tmp_path / ("portrait" + container)
    encoder_options = ["-cpu-used", "6"] if encoder == "libaom-av1" else []
    subprocess.run([processor.ffmpeg_path, "-v", "error", "-f", "lavfi", "-i", "testsrc2=size=320x568:rate=30000/1001",
        "-f", "lavfi", "-i", "sine=frequency=440:sample_rate=48000", "-t", "1", "-c:v", encoder,
        *encoder_options, "-threads", "2", "-c:a", "aac", str(source)], check=True, capture_output=True, timeout=120)
    before = source.read_bytes()
    output = prepare_for_premiere(source, tmp_path, processor, threading.Event(), lambda *a: None, trim=trim)
    actual = processor.get_local_media_info(output)
    video, audio = actual["streams"]
    assert video["codec_name"] == "h264" and audio["codec_name"] == "aac"
    assert (video["width"], video["height"]) == (320, 568)
    assert abs(float(video["nb_frames"]) - (15 if trim else 30)) <= 1
    assert source.read_bytes() == before


def test_real_hdr_conversion_keeps_10bit_color(tmp_path):
    import subprocess
    from src.core.processor import FFmpegProcessor
    processor = FFmpegProcessor()
    if not Path(processor.ffmpeg_path).is_file(): pytest.skip("FFmpeg not installed")
    source = tmp_path / "hdr.webm"
    subprocess.run([processor.ffmpeg_path, "-v", "error", "-f", "lavfi", "-i", "testsrc2=size=160x90:rate=24",
        "-t", "1", "-vf", "setparams=color_primaries=bt2020:color_trc=smpte2084:colorspace=bt2020nc",
        "-c:v", "libvpx-vp9", "-threads", "2", "-pix_fmt", "yuv420p10le", "-color_primaries", "bt2020",
        "-color_trc", "smpte2084", "-colorspace", "bt2020nc", str(source)], check=True, capture_output=True)
    output = prepare_for_premiere(source, tmp_path, processor, threading.Event(), lambda *a: None)
    stream = processor.get_local_media_info(output)["streams"][0]
    assert stream["codec_name"] == "prores" and stream["pix_fmt"] == "yuv422p10le"
    assert stream["color_transfer"] == "smpte2084" and stream["color_primaries"] == "bt2020"


def test_preparation_serializes_work_and_cancel_discards_pending_jobs(tmp_path):
    from tests.test_quick_workflow import APP, DeferredPool
    from src.ui.premiere_preparation import PremierePreparation
    pool = DeferredPool()
    prep = PremierePreparation(SimpleNamespace(root=tmp_path, pool=pool), None)
    delivered, progress = [], []
    prep.ready.connect(lambda *args: delivered.append(args))
    prep.progress.connect(lambda value, message: progress.append(value))
    prep.enqueue(["first.mp4"], {"automatic": True})
    prep.enqueue(["first.mp4"], {"automatic": True})
    prep.enqueue(["second.mp4"], {"prepareOnly": True})
    assert len(pool.calls) == 1 and len(prep.queue) == 1
    prep._progress(1, "working")
    assert progress[-1] == 0.01
    prep.cancel()
    pool.calls[0][2]["on_result"]((["first.mp4"], []))
    assert not delivered and not prep.queue and prep.active is None
    assert len(pool.calls) == 1


def test_manual_send_is_not_swallowed_by_an_automatic_preflight(tmp_path):
    from tests.test_quick_workflow import APP, DeferredPool
    from src.ui.premiere_preparation import PremierePreparation
    prep = PremierePreparation(SimpleNamespace(root=tmp_path, pool=DeferredPool()), None)
    prep.enqueue(["vp9.mp4"], {"automatic": True})
    prep.enqueue(["vp9.mp4"], {"automatic": False})
    assert len(prep.queue) == 1
    prep.shutdown()
