from __future__ import annotations

import time
from urllib.parse import urlsplit

from PySide6.QtCore import QObject, Property, Signal, Slot
from src.core.downloader import extract_info_resilient
from src.core.ytdlp_runtime import configure_ytdlp_options, friendly_ytdlp_error
from .media_preview_proxy import MediaPreviewProxy


def _has_codec(row, name):
    return row.get(name) not in (None, '', 'none')


def choose_preview_format(info):
    """Prefer a modest combined stream. Preview never changes download quality."""
    formats = [row for row in info.get('formats', []) if str(row.get('url', '')).startswith(('https://', 'http://'))
               and row.get('protocol') not in {'mhtml', 'http_dash_segments'}
               and (_has_codec(row, 'vcodec') or _has_codec(row, 'acodec'))]
    if not formats and info.get('url'):
        formats = [info]
    combined = [row for row in formats if _has_codec(row, 'vcodec') and _has_codec(row, 'acodec')]
    video = [row for row in formats if _has_codec(row, 'vcodec')]
    candidates = combined or video or formats
    if not candidates:
        raise ValueError('El sitio no ofrece un flujo para previsualizar este resultado.')
    def score(row):
        height = float(row.get('height') or 0)
        progressive = 'm3u8' not in str(row.get('protocol', '')) and '.m3u8' not in row.get('url', '')
        return (height <= 720, progressive, -abs(height - 480), str(row.get('ext')) == 'mp4')
    return max(candidates, key=score)


class SearchPreviewController(QObject):
    stateChanged = Signal()

    def __init__(self, settings, pool, parent=None):
        super().__init__(parent)
        self.settings, self.pool = settings, pool
        self.proxy = MediaPreviewProxy()
        self._generation = 0
        self._closed = False
        self._cache = {}
        self._state = dict(open=False, busy=False, source='', pageUrl='', title='', poster='',
                           kind='Video', hasAudio=True, error='', duration=0, detail='')

    @Property('QVariantMap', notify=stateChanged)
    def state(self): return self._state

    def _set(self, **values):
        self._state.update(values)
        self.stateChanged.emit()

    def show(self, row):
        url = str(row.get('url') or '')
        try:
            parsed = urlsplit(url)
            if parsed.scheme not in {'http', 'https'} or not parsed.netloc or self._closed: return
        except ValueError:
            return
        self._generation += 1
        generation = self._generation
        self._set(open=True, busy=True, source='', pageUrl=url, title=row.get('title') or url,
                  poster=row.get('thumbnail') or '', error='', duration=row.get('duration') or 0, detail='Conectando con la vista previa…')
        cached = self._cache.get(url)
        if cached and time.monotonic() - cached[0] < 240:
            self._ready(generation, url, cached[1])
            return
        self.pool.submit(self._resolve, url, on_result=lambda result: self._ready(generation, url, result),
                         on_error=lambda message, detail: self._error(generation, message))

    def _resolve(self, url):
        from src.core.browser_cookies import cookie_options
        options = configure_ytdlp_options(dict(quiet=True, noplaylist=True, skip_download=True,
                                               socket_timeout=15, retries=1, extractor_retries=1))
        options.update(cookie_options(self.settings, url))
        info = extract_info_resilient(url, options, download=False) or {}
        fmt = choose_preview_format(info)
        video = _has_codec(fmt, 'vcodec')
        audio = _has_codec(fmt, 'acodec')
        return dict(url=fmt['url'], headers={**(info.get('http_headers') or {}), **(fmt.get('http_headers') or {})},
                    kind='Video' if video else 'Audio', hasAudio=audio, duration=info.get('duration') or 0,
                    detail=('Vista previa · ' + str(fmt.get('height')) + 'p') if video and fmt.get('height') else 'Vista previa de audio')

    def _ready(self, generation, url, result):
        if self._closed or generation != self._generation: return
        self._cache[url] = (time.monotonic(), result)
        if len(self._cache) > 20: self._cache.pop(next(iter(self._cache)))
        source = self.proxy.url_for(result['url'], result['headers'])
        self._set(busy=False, error='', source=source, kind=result['kind'], hasAudio=result['hasAudio'],
                  duration=result['duration'], detail=result['detail'] + (' · Sin audio en este flujo' if not result['hasAudio'] else ''))

    def _error(self, generation, message):
        if not self._closed and generation == self._generation:
            self._set(busy=False, error=friendly_ytdlp_error(message), detail='No se pudo abrir la vista previa.')

    @Slot()
    def retry(self):
        self._cache.pop(self._state['pageUrl'], None)
        self.show(dict(url=self._state['pageUrl'], title=self._state['title'], thumbnail=self._state['poster']))

    @Slot()
    def close(self):
        self._generation += 1
        self._set(open=False, busy=False, source='', error='')

    def shutdown(self):
        self._closed = True
        self.close()
        self.proxy.shutdown()
