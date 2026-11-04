import contextlib
import io
import subprocess
import threading
from pathlib import Path

import pytest

from src.core.diagnostics import diagnostic_print
from src.core.processor import FFmpegProcessor
from src.core.premiere_media import prepare_for_premiere


def test_ansi_diagnostic_stream_escapes_unicode_without_changing_path():
    path = 'C:/Vídeos/Minecraft \ufe0f 🎬 日本語.mp4'
    buffer = io.BytesIO()
    stream = io.TextIOWrapper(buffer, encoding='cp1252', errors='strict')
    diagnostic_print('Analizando:', path, file=stream, flush=True)
    text = buffer.getvalue().decode('cp1252')
    assert '\\ufe0f' in text and '\\U0001f3ac' in text
    assert 'Vídeos' in text
    assert '\ufe0f' in path and '日本語' in path


def test_utf8_log_keeps_unicode():
    buffer = io.BytesIO()
    stream = io.TextIOWrapper(buffer, encoding='utf-8', newline='\n')
    diagnostic_print('Minecraft \ufe0f 🎬', file=stream, flush=True)
    assert buffer.getvalue().decode('utf-8') == 'Minecraft \ufe0f 🎬\n'


def test_unavailable_diagnostic_stream_does_not_abort(monkeypatch):
    monkeypatch.setattr('src.core.diagnostics.sys.stdout', None)
    diagnostic_print('Without console \ufe0f')
    stream = io.StringIO()
    stream.close()
    diagnostic_print('Closed stream \ufe0f', file=stream)


@pytest.mark.parametrize('encoder', ['libaom-av1', 'libvpx-vp9'])
def test_real_premiere_conversion_with_unicode_path_and_ansi_stdout(tmp_path, encoder):
    processor = FFmpegProcessor()
    if not Path(processor.ffmpeg_path).is_file():
        pytest.skip('FFmpeg not installed')
    source = tmp_path / 'Minecraft \ufe0f 🎬 日本語.mp4'
    options = ['-cpu-used', '6'] if encoder == 'libaom-av1' else []
    subprocess.run([processor.ffmpeg_path, '-v', 'error', '-f', 'lavfi', '-i',
        'testsrc2=size=160x90:rate=30', '-t', '0.5', '-c:v', encoder,
        *options, '-threads', '2', str(source)], capture_output=True, check=True, timeout=60)
    before = source.read_bytes()
    buffer = io.BytesIO()
    stream = io.TextIOWrapper(buffer, encoding='cp1252', errors='strict')
    with contextlib.redirect_stdout(stream):
        output = prepare_for_premiere(source, tmp_path, processor, threading.Event(), lambda *a: None)
        result = processor.get_local_media_info(output)
    assert source.read_bytes() == before
    assert result['streams'][0]['codec_name'] == 'h264'
    assert result['streams'][0]['nb_frames'] == '15'
    assert '日本語' in output and '\ufe0f' in output
    stream.flush()
    assert b'\\ufe0f' in buffer.getvalue()
