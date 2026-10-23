import threading
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from src.ui.download_controller import DownloadController


@pytest.mark.parametrize('local', [False, True])
@pytest.mark.parametrize('extension,codec', [('webm', 'vp9'), ('mkv', 'av1'), ('mp4', 'av01'), ('mp4', 'avc1')])
def test_video_download_preserves_source_without_implicit_conversion(tmp_path, local, extension, codec):
    source = tmp_path / ('download.' + extension)
    source.write_bytes(b'original downloaded media')
    controller = SimpleNamespace(
        _image_post=False, _video_map={'selected': {'vcodec': codec}}, _audio_map={},
        cancellation=threading.Event(), _download_worker=Mock(return_value=str(source)),
        _recode_file=Mock(side_effect=AssertionError('Unrequested conversion')),
        quick_outputs=[],
    )
    result = DownloadController._process_worker(controller, {'mode': 'Video+Audio', 'video_label': 'selected', 'local_file': str(source) if local else ''})
    assert result == str(source)
    assert source.read_bytes() == b'original downloaded media'
    controller._recode_file.assert_not_called()


def test_explicit_video_conversion_is_still_performed(tmp_path):
    source = str(tmp_path / 'source.webm')
    output = str(tmp_path / 'converted.mp4')
    controller = SimpleNamespace(_image_post=False, _video_map={}, cancellation=threading.Event(),
                                 _download_worker=Mock(return_value=source), _recode_file=Mock(return_value=output))
    options = {'mode': 'Video+Audio', 'recode_video_enabled': True}
    assert DownloadController._process_worker(controller, options) == output
    controller._recode_file.assert_called_once_with(source, options, True)


def test_quick_runner_preserves_webm(tmp_path):
    from tests.test_quick_workflow import Settings, DeferredPool, ROOT, APP
    from src.ui.quick_controller import QuickController
    from src.ui.presets import PresetStore
    settings = Settings(tmp_path)
    quick = QuickController(ROOT, settings, DeferredPool(), object(), PresetStore(settings), 'test')
    source = tmp_path / 'video.webm'
    source.write_bytes(b'original')
    quick.runner._download_worker = Mock(return_value=str(source))
    quick.runner._recode_file = Mock(side_effect=AssertionError('Unrequested conversion'))
    try:
        assert quick.runner._process_worker({'mode': 'Video+Audio'}) == str(source)
        assert quick.runner.quick_outputs == [str(source)]
        quick.runner._recode_file.assert_not_called()
    finally:
        quick.shutdown()
        APP.processEvents()
