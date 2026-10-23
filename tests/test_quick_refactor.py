"""Regressions for the simplified input, preferences and queue updates."""
import unittest
from copy import deepcopy
from unittest.mock import Mock, patch

from tests import test_quick_workflow as fixtures
from src.ui.quick_options import preferences


class QuickRefactorTests(unittest.TestCase):
    setUp = fixtures.QuickTests.setUp
    tearDown = fixtures.QuickTests.tearDown

    def test_plain_text_searches_without_enqueuing_a_fake_link(self):
        self.quick.setValue('url', 'gato en la nieve')
        self.assertEqual(self.quick.state['actionLabel'], 'Buscar')
        self.quick.enqueue()
        self.assertEqual(self.quick.jobs.count(), 0)
        self.assertEqual(self.quick.state['discoveryQuery'], 'gato en la nieve')
        self.assertEqual(len(self.pool.calls), 1)

    def test_mixed_or_malformed_links_do_not_start_search_or_download(self):
        notice = Mock()
        self.quick.notificationRequested.connect(notice)
        for value in ('https://[bad', 'https://example.com text', 'file:///private/video.mp4'):
            self.quick.setValue('url', value)
            self.quick.enqueue()
        self.assertEqual(notice.call_count, 3)
        self.assertEqual(self.pool.calls, [])

    def test_typing_does_not_write_preferences_to_disk(self):
        self.settings.set = Mock(wraps=self.settings.set)
        for text in ('g', 'ga', 'gat', 'gato'):
            self.quick.setValue('url', text)
        self.settings.set.assert_not_called()
        self.quick.setValue('quality', '720p')
        self.settings.set.assert_called_once()

    def test_legacy_preferences_migrate_and_round_trip(self):
        saved = {'thumbnail': True, 'thumbnailOnly': True, 'playlist': True, 'quality': 'bad'}
        restored = preferences(saved, 'destination')
        self.assertTrue(restored['thumbnailOnly'])
        self.assertFalse(restored['thumbnail'])
        self.assertTrue(restored['playlist'])
        self.assertEqual(restored['quality'], '1080p')
        self.assertEqual(preferences(restored, 'other'), restored)
        self.assertEqual(saved['quality'], 'bad')

    def test_thumbnail_options_are_exclusive_in_ui_and_saved_settings(self):
        self.quick.setValue('thumbnailMode', 'Solo miniatura')
        self.quick.setValue('thumbnail', True)
        self.assertFalse(self.quick.state['thumbnailOnly'])
        self.assertEqual(self.quick.state['thumbnailMode'], 'Guardar miniatura')
        self.quick.setValue('thumbnailMode', 'Sin miniatura')
        saved = self.settings.get('quick_mode_preferences')
        self.assertFalse(saved['thumbnail'] or saved['thumbnailOnly'])

    def test_tag_destination_matches_job_and_tracks_tag_edits(self):
        self.settings.set('download_tags', [{'name': 'Trabajo', 'folder': '/clips'}])
        self.quick.setValue('selectedTag', 'Trabajo')
        self.assertEqual(self.quick.state['effectiveOutputPath'], '/clips')
        self.quick.setValue('url', 'https://example.com/video')
        self.quick.enqueue()
        self.settings.set('download_tags', [{'name': 'Trabajo', 'folder': '/new'}])
        self.assertEqual(self.quick.runner.quick_options['outputPath'], '/clips')
        self.assertEqual(self.quick.state['effectiveOutputPath'], '/new')
        self.assertNotIn('discoveryQuery', self.quick.runner.quick_options)

    def test_queue_snapshot_does_not_share_mutable_ranges(self):
        self.quick.addRange('00:01', '00:02')
        self.quick.setValue('url', 'https://example.com/video')
        self.quick.enqueue()
        before = deepcopy(self.quick.runner.quick_options['ranges'])
        self.quick.removeRange(0)
        self.assertEqual(self.quick.runner.quick_options['ranges'], before)

    def test_identical_progress_does_not_repaint_or_copy_full_queue(self):
        self.quick.setValue('url', 'https://example.com/video')
        self.quick.enqueue()
        self.quick._progress()
        changed, repaint = Mock(), Mock()
        self.quick.stateChanged.connect(changed)
        self.quick.jobs.dataChanged.connect(repaint)
        with patch.object(self.quick.jobs, 'items', side_effect=AssertionError('Full queue copied')):
            for _ in range(20):
                self.quick._progress()
        changed.assert_not_called()
        repaint.assert_not_called()

    def test_cancel_all_cancels_pending_and_never_starts_them(self):
        self.quick.setValue('url', 'https://example.com/1 https://example.com/2 https://example.com/3')
        self.quick.enqueue()
        self.quick.cancelAll()
        self.assertEqual(self.quick.state['pending'], 0)
        self.assertEqual(self.quick.jobs.item(1)['status'], 'Cancelado')
        self.quick.runner._apply_url_analysis({})
        fixtures.APP.processEvents()
        self.assertEqual(len(self.pool.calls), 1)
        self.assertFalse(self.quick.state['running'])

    def test_playlist_rejects_multiple_urls_and_can_return_to_search(self):
        self.quick.setValue('playlist', True)
        self.quick.setValue('url', 'https://example.com/1 https://example.com/2')
        self.quick.enqueue()
        self.assertEqual(self.pool.calls, [])
        self.quick.discover('https://example.com/playlist', 'playlist')
        self.quick.openSearch()
        self.pool.calls[0][2]['on_result']([{'url': 'https://example.com/1', 'chosen': True}])
        self.assertEqual(self.quick.discovery.count(), 0)
        self.assertEqual(self.quick.state['discoverySource'], 'YouTube')


if __name__ == '__main__':
    unittest.main()
