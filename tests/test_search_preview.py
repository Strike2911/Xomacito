import unittest
from unittest.mock import Mock, patch

from src.ui.search_preview_controller import SearchPreviewController, choose_preview_format
from tests.test_quick_workflow import APP, DeferredPool, Settings


def stream(**values):
    return dict(url='https://example.com/stream.mp4', headers={}, kind='Video',
                hasAudio=True, duration=10, detail='360p', **values)


class SearchPreviewTests(unittest.TestCase):
    def setUp(self):
        self.pool = DeferredPool()
        self.preview = SearchPreviewController(Mock(), self.pool)
        self.preview.proxy = Mock()
        self.preview.proxy.url_for.return_value = 'http://localhost/preview'

    def tearDown(self):
        self.preview.shutdown()

    def complete(self, index=0):
        self.pool.calls[index][2]['on_result'](stream())

    def test_late_result_cannot_reopen_closed_preview(self):
        self.preview.show({'url': 'https://example.com/first'})
        self.preview.close()
        self.complete()
        self.assertFalse(self.preview.state['open'])
        self.assertFalse(self.preview.state['source'])
        self.preview.proxy.url_for.assert_not_called()

    def test_fast_switch_discards_old_result_and_error(self):
        self.preview.show({'url': 'https://example.com/first'})
        self.preview.show({'url': 'https://example.com/second', 'title': 'Second'})
        self.complete()
        self.pool.calls[0][2]['on_error']('Old error', '')
        self.assertTrue(self.preview.state['busy'])
        self.assertFalse(self.preview.state['error'])
        self.complete(1)
        self.assertEqual(self.preview.state['title'], 'Second')
        self.assertFalse(self.preview.state['busy'])

    def test_cache_reuses_stream_and_retry_refreshes_it(self):
        row = {'url': 'https://example.com/first'}
        self.preview.show(row)
        self.complete()
        self.preview.close()
        self.preview.show(row)
        self.assertEqual(len(self.pool.calls), 1)
        self.assertTrue(self.preview.state['source'])
        self.preview.retry()
        self.assertEqual(len(self.pool.calls), 2)
        self.assertFalse(self.preview.state['source'])

    def test_invalid_source_never_reaches_extractor(self):
        for url in ('file:///private', 'https://', 'https://[bad', 'javascript:alert(1)'):
            self.preview.show({'url': url})
        self.assertFalse(self.pool.calls)

    def test_preview_uses_combined_modest_stream_without_mutating_formats(self):
        formats = [
            dict(url='https://example.com/1080', vcodec='h264', acodec='none', height=1080),
            dict(url='https://example.com/360', vcodec='h264', acodec='aac', height=360),
            dict(url='https://example.com/4k', vcodec='h264', acodec='aac', height=2160),
            dict(url='https://example.com/unknown', vcodec=None, acodec=None, height=480),
        ]
        self.assertEqual(choose_preview_format({'formats': formats}), formats[1])
        self.assertEqual(len(formats), 4)

    def test_audio_only_result_is_identified_without_video_codec(self):
        audio = dict(url='https://example.com/audio.mp3', vcodec=None, acodec='mp3')
        with patch('src.ui.search_preview_controller.configure_ytdlp_options', return_value={}), \
             patch('src.core.browser_cookies.cookie_options', return_value={}), \
             patch('src.ui.search_preview_controller.extract_info_resilient', return_value={'formats': [audio]}):
            result = self.preview._resolve('https://example.com/song')
        self.assertEqual(result['kind'], 'Audio')
        self.assertTrue(result['hasAudio'])

    def test_shutdown_ignores_inflight_result(self):
        self.preview.show({'url': 'https://example.com/first'})
        self.preview.shutdown()
        self.complete()
        self.assertFalse(self.preview.state['source'])


class DiscoverySelectionTests(unittest.TestCase):
    def test_preview_does_not_select_or_enqueue_result(self):
        import tempfile
        from pathlib import Path
        from src.ui.quick_controller import QuickController
        from src.ui.presets import PresetStore
        with tempfile.TemporaryDirectory() as directory:
            settings = Settings(Path(directory))
            quick = QuickController(Path(__file__).resolve().parents[1], settings, DeferredPool(), object(), PresetStore(settings), 'test')
            try:
                quick._discovery_done([dict(url='https://example.com/a', title='A', chosen=False)])
                quick.preview.show = Mock()
                quick.previewDiscovery(0)
                quick.preview.show.assert_called_once()
                self.assertEqual(quick.state['discoverySelected'], 0)
                self.assertEqual(quick.jobs.count(), 0)
                quick.chooseAllDiscovery(True)
                self.assertEqual(quick.state['discoverySelected'], 1)
                quick.chooseDiscovery(0, False)
                self.assertEqual(quick.state['discoverySelected'], 0)
            finally:
                quick.shutdown()
                APP.processEvents()
