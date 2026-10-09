import unittest
from unittest.mock import patch

from tests.test_quick_workflow import QuickTests


def rows(count=20, offset=0):
    return [dict(url=f'https://example.com/{index}', title=str(index), chosen=False)
            for index in range(offset, offset + count)]


class DiscoveryTests(unittest.TestCase):
    setUp = QuickTests.setUp
    tearDown = QuickTests.tearDown

    def complete(self, index, result):
        self.pool.calls[index][2]['on_result'](result)

    def test_cache_reuses_results_without_selection_leaking(self):
        self.quick.discover('gatos', 'YouTube')
        self.complete(0, rows())
        self.quick.chooseDiscovery(0, True)
        self.quick.discover('gatos', 'YouTube')
        self.assertEqual(len(self.pool.calls), 1)
        self.assertEqual(self.quick.discovery.count(), 20)
        self.assertEqual(self.quick.state['discoverySelected'], 0)

    def test_late_result_does_not_replace_new_search(self):
        self.quick.discover('antes', 'YouTube')
        self.quick.discover('ahora', 'YouTube')
        self.complete(1, rows(1, 50))
        self.complete(0, rows())
        self.assertEqual(self.quick.discovery.item(0)['title'], '50')
        self.assertEqual(self.quick.state['discoveryQuery'], 'ahora')

    def test_only_two_requests_run_and_pending_search_is_latest(self):
        for query in ('uno', 'dos', 'tres', 'cuatro'):
            self.quick.discover(query, 'YouTube')
        self.assertEqual(len(self.pool.calls), 2)
        self.complete(0, rows())
        self.assertEqual(len(self.pool.calls), 3)
        self.assertIn('cuatro', self.pool.calls[2][1][0])
        self.complete(2, rows(1, 100))
        self.pool.calls[1][2]['on_error']('error antiguo', '')
        self.assertEqual(self.quick.discovery.item(0)['title'], '100')
        self.assertEqual(self.quick.state['discoveryError'], '')

    def test_load_more_preserves_selection_and_deduplicates(self):
        self.quick.discover('gatos', 'YouTube')
        self.complete(0, rows())
        self.quick.chooseDiscovery(2, True)
        self.quick.loadMoreDiscovery()
        self.complete(1, rows(5, 18))
        self.assertEqual(self.quick.discovery.count(), 23)
        self.assertEqual(self.quick.state['discoverySelected'], 1)
        self.assertFalse(self.quick.state['discoveryHasMore'])
        self.assertEqual(self.pool.calls[1][1][1], 2)

    def test_cancel_prevents_late_popup_reopening(self):
        events = []
        self.quick.discoveryReady.connect(lambda: events.append(True))
        self.quick.discover('gatos', 'YouTube')
        self.quick.cancelDiscovery()
        self.complete(0, rows())
        self.assertEqual(events, [])
        self.assertEqual(self.quick.discovery.count(), 0)

    def test_cache_expires_and_cookie_changes_invalidate_it(self):
        with patch('src.ui.quick_controller.time.monotonic', return_value=0):
            self.quick.discover('gatos', 'YouTube')
            self.complete(0, rows())
        with patch('src.ui.quick_controller.time.monotonic', return_value=121):
            self.quick.discover('gatos', 'YouTube')
        self.assertEqual(len(self.pool.calls), 2)
        self.complete(1, rows())
        with patch('src.core.browser_cookies.cookie_options', return_value={'cookiefile': 'changed.txt'}):
            self.quick.discover('gatos', 'YouTube')
        self.assertEqual(len(self.pool.calls), 3)

    def test_flat_page_does_not_read_more_entries_or_large_thumbnails(self):
        consumed = []
        def entries():
            for index in range(100):
                consumed.append(index)
                yield dict(id='abcdefghijk', ie_key='Youtube', url='abcdefghijk', title='Video')
        with patch('src.ui.quick_controller.extract_info_resilient', return_value={'entries': entries()}) as extract:
            result = self.quick._discovery_worker('ytsearch40:gatos', 2, 20, {})
        self.assertEqual(len(consumed), 20)
        self.assertEqual(result[0]['thumbnail'], 'https://i.ytimg.com/vi/abcdefghijk/mqdefault.jpg')
        options = extract.call_args.args[1]
        self.assertEqual(options['playliststart'], 21)
        self.assertEqual(options['playlistend'], 40)
        self.assertTrue(options['skip_download'])
        self.assertEqual(options['extract_flat'], 'in_playlist')


if __name__ == '__main__': unittest.main()
