import threading
import unittest
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
