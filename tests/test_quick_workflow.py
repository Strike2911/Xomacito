import json
import os
import tempfile
import time
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
from PySide6.QtCore import QObject, Signal
from PySide6.QtWidgets import QApplication
from src.ui.quick_controller import QuickController, choose_video
from src.ui.premiere_controller import PremiereController
from src.ui.media_library_controller import MediaLibraryController
from src.ui.presets import PresetStore

ROOT = Path(__file__).resolve().parents[1]
APP = QApplication.instance() or QApplication([])

class Settings(QObject):
    changed = Signal(str, object)
    def __init__(self, root):
        super().__init__()
        self.directory = root
        self.presets_path = root / 'presets.json'
        self.values = {'premiere_library_path': str(root / 'library')}
    def get(self, key, default=None): return self.values.get(key, default)
    def set(self, key, value):
        self.values[key] = value
        self.changed.emit(key, value)

class DeferredPool:
    def __init__(self): self.calls = []
    def submit(self, function, *args, **kwargs):
        self.calls.append((function, args, kwargs))

class QuickTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.settings = Settings(Path(self.temp.name))
        self.pool = DeferredPool()
        self.quick = QuickController(ROOT, self.settings, self.pool, object(), PresetStore(self.settings), 'test')
    def tearDown(self):
        self.quick.shutdown()
        APP.processEvents()
        self.temp.cleanup()
    def add(self, url='https://example.com/video.mp4'):
        self.quick.setValue('url', url)
        self.quick.enqueue()
    def test_queue_keeps_settings_per_job_and_controls_stay_free(self):
        self.add()
        self.quick.setValue('mode', 'Audio')
        self.quick.setValue('audioFormat', 'MP3 320')
        self.add('https://example.com/second.mp4')
        self.quick.setValue('audioFormat', 'WAV')
        self.assertEqual(self.quick.runner.quick_options['mode'], 'Video')
        self.assertEqual(self.quick._pending[0]['audioFormat'], 'MP3 320')
        self.quick.runner._operation_error('Network failed')
        APP.processEvents()
        self.assertEqual(self.quick.runner.quick_options['mode'], 'Audio')
        self.assertEqual(self.quick.runner.quick_options['audioFormat'], 'MP3 320')
        self.assertEqual(self.quick.jobs.item(0)['status'], 'Error')
    def test_cancel_pending_does_not_cancel_active_download(self):
        self.add('https://example.com/a.mp4 https://example.com/b.mp4')
        self.quick.cancel(self.quick.jobs.item(1)['jobId'])
        self.assertEqual(self.quick.state['pending'], 0)
        self.assertFalse(self.quick.runner.cancellation.is_set())
        self.assertEqual(self.quick.jobs.item(1)['status'], 'Cancelado')
    def test_cancel_analysis_never_starts_the_download(self):
        self.add()
        self.quick.cancel(self.quick.jobs.item(0)['jobId'])
        self.quick.runner._apply_url_analysis({})
        self.assertEqual(self.quick.jobs.item(0)['status'], 'Cancelado')
        self.assertEqual(len(self.pool.calls), 1)
    def test_quality_prefers_resolution_then_compatible_codec(self):
        formats = {'4k': {'height': 2160}, 'webm': {'height': 1080}, 'mp4': {'height': 1080, 'compatible': True}, '720': {'height': 720}}
        self.assertEqual(choose_video(formats, '1080p'), 'mp4')
        self.assertEqual(choose_video(formats, 'Mejor disponible'), '4k')
        self.assertEqual(choose_video(formats, '480p'), '720')
    def test_invalid_url_cannot_start_a_job(self):
        self.add('file:///private/file.mp4')
        self.assertEqual(self.quick.jobs.count(), 0)
        self.assertEqual(self.pool.calls, [])
    def test_output_collisions_create_a_copy_without_waiting_for_a_dialog(self):
        folder = Path(self.temp.name)
        existing = folder / 'sound.mp3'; existing.write_bytes(b'original')
        result = self.quick.runner._resolve_output(folder, 'sound', '.mp3')
        self.assertEqual(result.name, 'sound (1).mp3')
        self.assertEqual(existing.read_bytes(), b'original')
    def test_saved_history_can_be_cleared_without_cancelling_a_job(self):
        self.add()
        self.quick.clearHistory()
        self.assertEqual(self.quick.jobs.count(), 1)
        self.assertTrue(self.quick.state['running'])

class BridgeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.bridge = PremiereController(SimpleNamespace(root=self.root))
        self.media = self.root / 'toma con espacios.mp4'; self.media.write_bytes(b'media')
        self.folder = self.root / '.xomacito-link'; self.folder.mkdir()
    def tearDown(self):
        self.bridge.shutdown(); self.temp.cleanup()
    def heartbeat(self, age=0):
        (self.folder / 'heartbeat.json').write_text(json.dumps({'time':time.time()-age, 'project':'Prueba'}), encoding='utf-8')
    def test_send_requires_live_panel_and_explicit_confirmation(self):
        self.bridge.send(str(self.media), True)
        self.assertEqual(self.bridge.state['pending'], 0)
        self.heartbeat()
        self.bridge.send(str(self.media), True)
        request = next(self.folder.glob('*.request.json'))
        payload = json.loads(request.read_text(encoding='utf-8'))
        self.assertEqual(payload['path'], str(self.media.resolve()))
        self.assertEqual(payload['action'], 'timeline')
        self.assertEqual(self.bridge.state['pending'], 1)
        (self.folder / (payload['id'] + '.result.json')).write_text(json.dumps({'id':payload['id'],'ok':True,'message':'Importado'}),encoding='utf-8')
        self.bridge.poll()
        self.assertEqual(self.bridge.state['pending'], 0)
        self.assertEqual(self.bridge.state['status'], 'Importado')
        self.assertFalse(request.exists())
    def test_stale_heartbeat_cannot_queue_into_a_closed_project(self):
        self.heartbeat(30)
        self.bridge.send(str(self.media), False)
        self.assertFalse(self.bridge.state['connected'])
        self.assertFalse(list(self.folder.glob('*.request.json')))

    def test_live_panel_without_project_is_not_connected(self):
        (self.folder / 'heartbeat.json').write_text(json.dumps({'time': time.time(), 'project': ''}), encoding='utf-8')
        self.bridge.send(str(self.media), False)
        self.assertFalse(self.bridge.state['connected'])
        self.assertFalse(list(self.folder.glob('*.request.json')))

    def test_modern_batch_and_automatic_completion_deduplicate_pending(self):
        (self.folder / 'heartbeat.json').write_text(json.dumps({'time': time.time(), 'project': 'Prueba', 'projectId': 'a', 'protocol': 2, 'autoImport': True}), encoding='utf-8')
        self.bridge.completed(str(self.media))
        self.bridge.send(str(self.media), False)
        requests = list(self.folder.glob('*.request.json'))
        self.assertEqual(len(requests), 1)
        data = json.loads(requests[0].read_text(encoding='utf-8'))
        self.assertEqual(data['schema'], 2)
        self.assertTrue(data['automatic'])
        self.assertEqual(data['paths'], [str(self.media.resolve())])
        self.assertEqual(data['projectId'], 'a')

    def test_reverse_selection_links_available_sources_and_acknowledges(self):
        calls = []
        self.bridge.library.linkPaths = calls.append
        request_id = 'a' * 32
        message = self.folder / f'{request_id}.to-app.json'
        message.write_text(json.dumps({'schema': 1, 'id': request_id, 'expires': time.time()+120,
            'paths': [str(self.media), str(self.root / 'missing.wav')]}), encoding='utf-8')
        self.bridge.poll()
        self.assertEqual(calls, [[str(self.media)]])
        result = json.loads((self.folder / f'{request_id}.app-result.json').read_text(encoding='utf-8'))
        self.assertTrue(result['ok'])
        self.assertIn('1 de 2', result['message'])
        self.assertFalse(message.exists())
        self.bridge.poll()
        self.assertEqual(len(calls), 1)
    def test_expired_requests_report_failure_and_are_removed(self):
        self.heartbeat(); self.bridge.send(str(self.media), False)
        request_id = next(iter(self.bridge._pending))
        self.bridge._pending[request_id] = (self.folder, time.time()-130)
        self.bridge.poll()
        self.assertEqual(self.bridge.state['pending'], 0)
        self.assertIn('no confirmó', self.bridge.state['status'])
        self.assertFalse(list(self.folder.glob('*.request.json')))

class LinkedLibraryTests(unittest.TestCase):
    def test_linking_preserves_original_and_cached_scans_avoid_reprobing(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            settings = Settings(root)
            media = root / 'outside' / 'sound.wav'; media.parent.mkdir(); media.write_bytes(b'audio')
            ffmpeg = SimpleNamespace(get_local_media_info=Mock(return_value={'streams':[{'codec_type':'audio','codec_name':'pcm_s16le'}], 'format':{'duration':'2'}}))
            library = MediaLibraryController(ROOT, settings, DeferredPool(), ffmpeg)
            library.linkPath(str(media.parent))
            first = library._scan_worker()
            second = library._scan_worker()
            self.assertEqual(first, second)
            self.assertEqual(ffmpeg.get_local_media_info.call_count, 1)
            self.assertEqual(first[0]['path'], str(media.resolve()))
            self.assertEqual(media.read_bytes(), b'audio')
            self.assertFalse(list(library.root.glob('**/sound.wav')))
            media.write_bytes(b'changed audio')
            library._scan_worker()
            self.assertEqual(ffmpeg.get_local_media_info.call_count, 2)

if __name__ == '__main__': unittest.main()
