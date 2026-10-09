import io
import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

from PIL import Image
from PySide6.QtCore import QUrl

from tests.test_quick_workflow import APP, ROOT, Settings, DeferredPool, QuickTests
from src.ui.media_browser_controller import MediaBrowserController
from src.core.media_catalogs import search_catalog


class BrowserTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.settings = Settings(self.root)
        self.pool = DeferredPool()
        self.browser = MediaBrowserController(ROOT, self.settings, self.pool, SimpleNamespace(ffmpeg_path='ffmpeg'))
        rows = []
        for name, kind in [('A.wav', 'Audio'), ('B.mp4', 'Video'), ('C.wav', 'Audio')]:
            path = self.browser.root / name
            path.write_bytes(b'media')
            row = {role: '' for role in self.browser.ROLES}
            row.update(path=str(path), name=name, kind=kind, duration=2., sizeBytes=5, searchText=name.lower())
            rows.append(row)
        self.browser.items.replace(rows)
        self.browser._rebuild_browser()
        self.paths = [row['path'] for row in rows]

    def tearDown(self):
        self.browser.shutdown()
        self.temp.cleanup()

    def test_range_selection_collections_and_restart_preserve_originals(self):
        self.browser.chooseItem(self.paths[0], False, False)
        self.browser.chooseItem(self.paths[2], False, True)
        self.assertEqual(self.browser.chosenPaths(), self.paths)
        self.browser.addCollection('Mi montaje')
        key = self.browser.state['collections'][0]['key']
        self.browser.setScope(key)
        self.assertEqual(self.browser.browser_items.count(), 3)
        self.browser.chooseItem(self.paths[1], False, False)
        self.browser.removeFromCollection()
        self.assertEqual(self.browser.browser_items.count(), 2)
        self.assertTrue(Path(self.paths[1]).exists())
        self.assertEqual(len(self.settings.get('media_browser_collections')[0]['paths']), 2)
        self.browser.removeSource()
        self.assertEqual(len(self.settings.get('media_browser_collections')), 0)
        self.assertTrue(all(Path(path).exists() for path in self.paths))

    def test_filters_favorites_sort_and_control_selection(self):
        self.browser.chooseItem(self.paths[0], False, False)
        self.browser.chooseItem(self.paths[2], True, False)
        self.browser.chooseItem(self.paths[0], True, False)
        self.assertEqual(self.browser.chosenPaths(), [self.paths[2]])
        self.browser.toggleFavorite(self.paths[2])
        self.browser.setScope('favorites')
        self.assertEqual([row['name'] for row in self.browser.browser_items.items()], ['C.wav'])
        self.browser.setScope('all')
        self.browser.setBrowserValue('kindFilter', 'Audio')
        self.browser.setBrowserValue('sortDescending', True)
        self.assertEqual([row['name'] for row in self.browser.browser_items.items()], ['C.wav', 'A.wav'])
        self.browser.setSearchText('a.wav')
        self.assertEqual(self.browser.browser_items.count(), 1)

    def test_folder_scope_does_not_mix_siblings(self):
        sub = self.browser.root / 'sub'
        sub.mkdir()
        row = self.browser.items.item(0)
        row['path'] = str(sub / 'inside.wav')
        Path(row['path']).write_bytes(b'audio')
        self.browser.items.append(row)
        self.browser.setScope('folder:' + str(sub))
        self.assertEqual(self.browser.browser_items.count(), 1)
        self.assertEqual(self.browser.browser_items.item(0)['path'], row['path'])

    def test_old_catalog_response_cannot_replace_new_scope(self):
        self.browser.setScope('web:Openverse')
        self.browser.setSearchText('ocean')
        self.browser.searchWeb(1)
        callback = self.pool.calls[-1][2]['on_result']
        self.browser.setScope('favorites')
        callback([{'unexpected': 'stale'}])
        self.assertEqual(self.browser.state['scope'], 'favorites')
        self.assertEqual(self.browser.browser_items.count(), 0)

    def test_web_download_rejects_html_and_cleans_partial_file(self):
        response = Mock()
        response.__enter__ = Mock(return_value=response)
        response.__exit__ = Mock(return_value=False)
        response.headers = {'Content-Type': 'text/html'}
        with patch('requests.get', return_value=response):
            with self.assertRaisesRegex(ValueError, 'página'):
                self.browser._web_download_worker({'downloadUrl': 'https://example.com/bad.mp3', 'name': 'bad'}, self.root/'web')
        self.assertFalse(list((self.root/'web').iterdir()))

    def test_web_download_preserves_credits_and_duplicate_original(self):
        response = Mock()
        response.__enter__ = Mock(return_value=response)
        response.__exit__ = Mock(return_value=False)
        response.headers = {'Content-Type': 'audio/mpeg'}
        response.iter_content.return_value = iter([b'mp3-bytes'])
        folder = self.root/'web'; folder.mkdir()
        original = folder/'Sound.mp3'; original.write_bytes(b'original')
        row = dict(downloadUrl='https://example.com/audio', name='Sound.mp3', creator='Artist', license='CC BY 4.0', pageUrl='https://example.com/credits')
        with patch('requests.get', return_value=response):
            output = Path(self.browser._web_download_worker(row, folder))
        self.assertEqual(original.read_bytes(), b'original')
        self.assertNotEqual(output, original)
        self.assertIn('CC BY 4.0', output.with_suffix('.mp3.credits.txt').read_text())
        self.assertEqual(output.read_bytes(), b'mp3-bytes')


class QuickExtrasTests(QuickTests):
    # Inherits queue/error/cancellation coverage and exercises the added controls.
    def test_history_is_separate_and_activity_clear_keeps_history(self):
        self.add()
        output = Path(self.temp.name)/'result.mp4'; output.write_bytes(b'media')
        self.quick._finished('Completado', str(output))
        self.assertEqual(self.quick.history.count(), 1)
        self.quick.clearActivity()
        self.assertEqual(self.quick.jobs.count(), 0)
        self.assertEqual(self.quick.history.count(), 1)
        self.quick.clearHistory()
        self.assertEqual(self.quick.history.count(), 0)
        self.assertTrue(output.exists())

    def test_cancel_all_stops_pending_before_current_completes(self):
        self.add('https://example.com/a https://example.com/b')
        self.quick.cancelAll()
        self.assertEqual(self.quick.state['pending'], 0)
        self.assertTrue(self.quick.runner.cancellation.is_set())
        self.quick.runner._operation_error('Cancelado')
        APP.processEvents()
        self.assertFalse(self.quick.state['running'])

    def test_ranges_and_tag_destination_are_snapshotted_per_job(self):
        tag_dir = str(Path(self.temp.name)/'tag')
        self.settings.set('download_tags', [{'name': 'Edición', 'folder': tag_dir, 'color': '#FFFFFF'}])
        self.quick.setValue('selectedTag', 'Edición')
        self.quick.addRange('abc', '00:00:03')
        self.assertEqual(self.quick.state['ranges'], [])
        self.quick.addRange('00:00:01', '00:00:03')
        self.add()
        self.quick.removeRange(0)
        self.assertEqual(self.quick.runner.quick_options['outputPath'], tag_dir)
        self.assertEqual(len(self.quick.runner.quick_options['ranges']), 1)
        self.assertEqual(self.quick.state['ranges'], [])

    def test_thumbnail_is_decoded_to_real_jpeg(self):
        source = Path(self.temp.name)/'source.png'
        Image.new('RGBA', (32, 32), (120, 10, 20, 80)).save(source)
        target = self.quick.runner._thumbnail_worker(QUrl.fromLocalFile(str(source)).toString(), self.temp.name, 'Thumbnail')
        with Image.open(target) as image:
            self.assertEqual(image.format, 'JPEG')
            self.assertEqual(image.mode, 'RGB')

    def test_playlist_only_enqueues_checked_entries_and_keeps_settings(self):
        self.quick.setValue('playlist', True)
        self.quick.setValue('url', 'https://example.com/list')
        self.quick.enqueue()
        self.assertEqual(self.quick.jobs.count(), 0)
        self.quick._discovery_done([{'url': 'https://example.com/a', 'title': 'A', 'duration': 2, 'chosen': True},
                                    {'url': 'https://example.com/b', 'title': 'B', 'duration': 2, 'chosen': False}])
        self.quick.enqueueDiscovery()
        self.assertEqual(self.quick.jobs.count(), 1)
        self.assertEqual(self.quick.jobs.item(0)['url'], 'https://example.com/a')

    def test_all_fragment_outputs_are_sent_to_premiere(self):
        self.quick.setValue('sendPremiere', True)
        self.add()
        paths = [str(Path(self.temp.name)/f'clip{i}.mp4') for i in (1, 2)]
        for path in paths: Path(path).write_bytes(b'media')
        self.quick.runner.quick_outputs = paths
        emitted = []
        self.quick.premiereRequested.connect(lambda path, _timeline: emitted.append(path))
        self.quick._finished('Completado', self.temp.name)
        self.assertEqual(emitted, paths)


class CatalogTests(unittest.TestCase):
    def test_freesound_preview_is_explicitly_labelled(self):
        data = {'results': [{'id': 4, 'name': 'sound.wav', 'url': 'https://freesound.org/s/4/', 'license': 'CC0',
                             'previews': {'preview-hq-mp3': 'https://cdn.freesound.org/4.mp3'}}]}
        with patch('src.core.media_catalogs._get', return_value=data):
            rows = search_catalog('Freesound', 'sound', 'Audio', 1, 'personal-token')
        self.assertEqual(rows[0]['extension'], '.mp3')
        self.assertIn('Previa MP3', rows[0]['note'])

    def test_pixabay_cache_does_not_repeat_request_or_store_key(self):
        data = {'hits': [{'id': 4, 'tags': 'ocean', 'largeImageURL': 'https://cdn.pixabay.com/image.jpg', 'pageURL': 'https://pixabay.com/p/4/'}]}
        with tempfile.TemporaryDirectory() as directory, patch('src.core.media_catalogs._get', return_value=data) as get:
            first = search_catalog('Pixabay', 'ocean', 'Imagen', 1, 'private-api-key', Path(directory))
            second = search_catalog('Pixabay', 'ocean', 'Imagen', 1, 'private-api-key', Path(directory))
            self.assertEqual(first, second)
            self.assertEqual(get.call_count, 1)
            for path in Path(directory).iterdir():
                self.assertNotIn('private-api-key', path.name + path.read_text())

    def test_catalog_requires_key_without_requesting_or_printing_one(self):
        with patch('requests.get') as request:
            with self.assertRaisesRegex(ValueError, 'Configura tu clave'):
                search_catalog('Pexels', 'ocean', 'Video', 1)
            request.assert_not_called()

    def test_wikimedia_strips_html_and_selects_requested_kind(self):
        data = {'query': {'pages': {'1': {'pageid': 1, 'title': 'File:Ocean.jpg', 'imageinfo': [{
            'mime': 'image/jpeg', 'url': 'https://commons.wikimedia.org/ocean.jpg',
            'extmetadata': {'Artist': {'value': '<a href="x">Creator &amp; Co</a>'}, 'LicenseShortName': {'value': 'CC BY-SA'}}}]}}}}
        with patch('src.core.media_catalogs._get', return_value=data):
            rows = search_catalog('Wikimedia', 'ocean', 'Imagen', 1)
            self.assertEqual(rows[0]['creator'], 'Creator & Co')
            self.assertEqual(search_catalog('Wikimedia', 'ocean', 'Audio', 1), [])


if __name__ == '__main__': unittest.main()
