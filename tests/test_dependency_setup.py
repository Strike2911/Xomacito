import io
import zipfile
from unittest.mock import Mock

import pytest
import requests

from src.core.dependency_status import dependency_status
from src.core import setup


@pytest.mark.parametrize('local,latest,expected', [
    ('8.0.1', '9.0.1', 'Actualización disponible'),
    ('v2.9.6', '2.9.6', 'Actualizado'),
    ('2026.08.19', '2026.08.19', 'Actualizado'),
    ('10.0', '9.0', 'Versión local más reciente'),
    ('Instalado', '2.0', 'Versión local desconocida'),
])
def test_dependency_comparison(local, latest, expected):
    assert dependency_status(local, latest)['detail'] == expected


def test_missing_dependency_is_not_reported_updated():
    assert dependency_status('—', '2.0', False)['action'] == 'Instalar'


def test_interrupted_archive_retries_and_publishes_complete_zip(tmp_path, monkeypatch):
    payload = io.BytesIO()
    with zipfile.ZipFile(payload, 'w') as archive:
        archive.writestr('upscayl-bin.exe', b'complete engine')
    data = payload.getvalue()
    response = Mock()
    response.__enter__ = Mock(return_value=response)
    response.__exit__ = Mock(return_value=False)
    response.headers = {'content-length': str(len(data))}
    response.iter_content.return_value = [data]
    get = Mock(side_effect=[requests.ConnectionError('interrupted'), response])
    monkeypatch.setattr(setup.requests, 'get', get)
    target = str(tmp_path / 'engine.zip')
    setup.download_upscaler_archive('https://example.com/engine.zip', target, lambda *a: None, 'Upscayl')
    assert get.call_count == 2
    assert zipfile.is_zipfile(target)
    assert not (tmp_path / 'engine.zip.part').exists()


def test_wrong_archive_does_not_destroy_existing_models(tmp_path, monkeypatch):
    monkeypatch.setattr(setup, 'UPSCALING_DIR', str(tmp_path))
    monkeypatch.setattr(setup, 'migrate_old_upscaling_models', lambda: None)
    old = tmp_path / 'upscayl/models/custom.bin'
    old.parent.mkdir(parents=True)
    old.write_bytes(b'keep my model')
    def wrong_download(url, path, *args):
        with zipfile.ZipFile(path, 'w') as archive:
            archive.writestr('README.txt', 'no executable')
    monkeypatch.setattr(setup, 'download_upscaler_archive', wrong_download)
    messages = []
    assert not setup.check_and_download_upscaling_tools(lambda *a: messages.append(a), 'Upscayl')
    assert old.read_bytes() == b'keep my model'
    assert any('no contiene' in message for message, _ in messages)
