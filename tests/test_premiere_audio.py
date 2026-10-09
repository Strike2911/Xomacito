import json
from pathlib import Path
import shutil
import subprocess
import threading
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from src.ui.presets import BUILT_IN_PRESETS, PREMIERE_AUDIO_PRESET, resolve_recode_parameters
from src.ui.download_controller import DownloadController, automatic_audio_options
from src.core.processor import FFmpegProcessor


@pytest.mark.parametrize('url', [
    'https://www.epidemicsound.com/music/tracks/07580420-9735-4f85-8c75-d408918ff2ae/',
    'https://www.epidemicsound.com/track/legacy/',
    'https://epidemicsound.com/sound-effects/tracks/example/',
])
@pytest.mark.parametrize('preference', ['MP3', 'Original', 'WAV para Premiere'])
def test_epidemic_forces_wav_without_changing_saved_choice(url, preference):
    options = {'url': url, 'mode': 'Solo Audio', 'audioOutputFormat': preference,
               'recode_audio_enabled': True, 'recode_audio_codec_name': 'MP3 (libmp3lame)'}
    result = automatic_audio_options(options)
    assert result['recode_container'] == '.wav'
    assert result['recode_audio_profile_name'] == 'Premiere · PCM 24-bit / 48 kHz'
    assert options['audioOutputFormat'] == preference
    for other in ('https://youtube.com/watch?v=abc', 'https://instagram.com/reel/abc/',
                  'https://epidemicsound.com.example.com/track/abc'):
        following = {**options, 'url': other}
        assert automatic_audio_options(following) == following


@pytest.mark.parametrize('extra', [
    {'local_file': 'local.m4a'}, {'mode': 'Video+Audio'},
    {'audioOutputFormat': 'Original'}, {'recode_audio_enabled': True},
])
def test_automatic_audio_respects_explicit_choices(extra):
    options = {'mode': 'Solo Audio', **extra}
    assert automatic_audio_options(options) == options


@pytest.mark.parametrize('extension,codec,output,url', [
    ('m4a', 'aac', 'MP3', ''), ('opus', 'libopus', 'MP3', ''),
    ('mp3', 'libmp3lame', 'MP3', ''), ('mp3', 'libmp3lame', 'WAV para Premiere', ''),
    ('mp3', 'libmp3lame', 'MP3', 'https://www.epidemicsound.com/track/example/'),
    ('m4a', 'aac', 'Preset MP3', ''),
])
def test_download_worker_automatically_produces_chosen_audio(tmp_path, extension, codec, output, url):
    ffmpeg = FFmpegProcessor()
    if not Path(ffmpeg.ffmpeg_path).is_file():
        pytest.skip('Packaged FFmpeg required')
    source = tmp_path / ('download.' + extension)
    subprocess.run([ffmpeg.ffmpeg_path, '-v', 'error', '-f', 'lavfi', '-i',
                    'sine=frequency=440:sample_rate=44100:duration=1',
                    '-c:a', codec, str(source)], check=True)
    original = source.read_bytes()
    worker = SimpleNamespace(
        _image_post=None, _download_worker=lambda options: str(source),
        cancellation=threading.Event(), ffmpeg=ffmpeg, progressReported=Mock(),
        _ffmpeg_progress=lambda *args: None,
        _resolve_output=lambda folder, title, container: folder / (title + container),
    )
    worker._recode_file = lambda *args, **kwargs: DownloadController._recode_file(worker, *args, **kwargs)
    result = Path(DownloadController._process_worker(worker, {
        'mode': 'Solo Audio', 'audioOutputFormat': output, 'url': url,
        'output_path': str(tmp_path), 'title': 'result', 'duration': 1,
        **(BUILT_IN_PRESETS['Audio - MP3 128kbps'] if output == 'Preset MP3' else {}),
    }))
    if url:
        output = 'WAV para Premiere'
    info = ffmpeg.get_local_media_info(str(result))
    audio = info['streams'][0]
    assert audio['codec_name'] == ('pcm_s24le' if output == 'WAV para Premiere' else 'mp3')
    assert result.suffix == ('.wav' if output == 'WAV para Premiere' else '.mp3')
    assert abs(float(info['format']['duration']) - 1) < 0.1
    if extension == 'mp3' and output == 'MP3':
        assert result.read_bytes() == original
    elif output != 'Preset MP3':
        assert not source.exists()  # Only the verified final file is delivered.
    if output != 'WAV para Premiere':
        assert not list(tmp_path.glob('*.wav')), 'MP3 must not create an unsolicited WAV companion'
    if output == 'WAV para Premiere':
        assert audio['sample_rate'] == '48000'


def test_premiere_preset_converts_compressed_audio_to_pcm_48k(tmp_path):
    root = Path(__file__).resolve().parents[1]
    ffmpeg = shutil.which('ffmpeg') or str(root / 'bin/ffmpeg/ffmpeg.exe')
    ffprobe = shutil.which('ffprobe') or str(root / 'bin/ffmpeg/ffprobe.exe')
    if not Path(ffmpeg).is_file() or not Path(ffprobe).is_file():
        pytest.skip('FFmpeg and FFprobe required for audio integration test')
    source = tmp_path / 'source.mp3'
    target = tmp_path / 'premiere.wav'
    subprocess.run([ffmpeg, '-v', 'error', '-f', 'lavfi', '-i',
                    'sine=frequency=440:sample_rate=44100:duration=1',
                    '-c:a', 'libmp3lame', str(source)], check=True)
    options = {**BUILT_IN_PRESETS[PREMIERE_AUDIO_PRESET], 'mode': 'Solo Audio'}
    params, container = resolve_recode_parameters(options)
    assert container == '.wav'
    assert options['keep_original_file']
    subprocess.run([ffmpeg, '-v', 'error', '-xerror', '-i', str(source),
                    *params, str(target)], check=True)
    info = json.loads(subprocess.check_output([ffprobe, '-v', 'error', '-show_streams',
                                               '-show_format', '-of', 'json', str(target)]))
    audio = info['streams'][0]
    assert audio['codec_name'] == 'pcm_s24le'
    assert audio['sample_rate'] == '48000'
    assert audio['bits_per_sample'] == 24
    assert abs(float(info['format']['duration']) - 1) < 0.01
    subprocess.run([ffmpeg, '-v', 'error', '-xerror', '-i', str(target), '-f', 'null', '-'], check=True)
