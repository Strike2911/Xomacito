import threading
import unittest
import re
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import requests

from src.ui.media_preview_proxy import MediaPreviewProxy


class _RangeSource(BaseHTTPRequestHandler):
    payload = b"0123456789"
    received_header = ""

    def do_GET(self):  # noqa: N802
        type(self).received_header = self.headers.get("X-Xomacito-Test", "")
        requested = self.headers.get("Range", "")
        if requested == "bytes=2-5":
            body = self.payload[2:6]
            self.send_response(206)
            self.send_header("Content-Range", "bytes 2-5/10")
        else:
            body = self.payload
            self.send_response(200)
        self.send_header("Content-Type", "video/mp4")
        self.send_header("Accept-Ranges", "bytes")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, _format, *_args):
        return


class MediaPreviewProxyTests(unittest.TestCase):
    def test_hls_rewrites_nested_playlists_keys_and_segments_with_headers(self):
        received = []

        class Source(BaseHTTPRequestHandler):
            def do_GET(self):
                received.append((self.path, self.headers.get('X-Test-Access')))
                bodies = {
                    '/master.m3u8': b'#EXTM3U\n#EXT-X-STREAM-INF:BANDWIDTH=1000\nvideo/index.m3u8?token=123\n',
                    '/video/index.m3u8?token=123': b'#EXTM3U\n#EXT-X-KEY:METHOD=AES-128,URI="../secret.key?token=456"\n#EXTINF:2,\npart.ts?token=789\n#EXT-X-ENDLIST\n',
                    '/secret.key?token=456': b'0123456789abcdef',
                    '/video/part.ts?token=789': b'segment',
                }
                body = bodies[self.path]
                self.send_response(200)
                self.send_header('Content-Type', 'application/vnd.apple.mpegurl' if '.m3u8' in self.path else 'application/octet-stream')
                self.send_header('Content-Length', str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def log_message(self, *_args): pass

        upstream = ThreadingHTTPServer(('127.0.0.1', 0), Source)
        thread = threading.Thread(target=upstream.serve_forever, daemon=True)
        thread.start()
        proxy = MediaPreviewProxy()
        try:
            preview = proxy.url_for(f'http://127.0.0.1:{upstream.server_port}/master.m3u8', {'X-Test-Access': 'present'})
            master = requests.get(preview, timeout=3)
            child = next(line for line in master.text.splitlines() if line.startswith('http'))
            self.assertTrue(child.endswith('/stream.m3u8'))
            playlist = requests.get(child, timeout=3)
            key = re.search(r'URI="([^"]+)"', playlist.text)[1]
            segment = next(line for line in playlist.text.splitlines() if line.startswith('http'))
            self.assertEqual(requests.get(key, timeout=3).content, b'0123456789abcdef')
            self.assertEqual(requests.get(segment, timeout=3).content, b'segment')
            self.assertTrue(all(header == 'present' for _, header in received))
            self.assertEqual(requests.head(child, timeout=3).headers['Content-Length'], str(len(playlist.content)))
            self.assertEqual(requests.get(child, timeout=3).content, playlist.content)
        finally:
            proxy.shutdown()
            upstream.shutdown()
            upstream.server_close()
            thread.join(timeout=1)

    def test_relays_required_headers_and_byte_ranges(self):
        upstream = ThreadingHTTPServer(("127.0.0.1", 0), _RangeSource)
        upstream_thread = threading.Thread(target=upstream.serve_forever, daemon=True)
        upstream_thread.start()
        proxy = MediaPreviewProxy()
        try:
            source = f"http://127.0.0.1:{upstream.server_address[1]}/video"
            preview = proxy.url_for(source, {"X-Xomacito-Test": "presente"})
            response = requests.get(preview, headers={"Range": "bytes=2-5"}, timeout=3)
            self.assertEqual(response.status_code, 206)
            self.assertEqual(response.content, b"2345")
            self.assertEqual(response.headers["Content-Range"], "bytes 2-5/10")
            self.assertEqual(_RangeSource.received_header, "presente")
        finally:
            proxy.shutdown()
            upstream.shutdown()
            upstream.server_close()
            upstream_thread.join(timeout=1)
