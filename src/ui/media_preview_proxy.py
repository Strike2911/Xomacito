from __future__ import annotations

import secrets
import threading
from dataclasses import dataclass
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import unquote, urlparse

import requests


_RESPONSE_HEADERS = (
    "Content-Type", "Content-Length", "Content-Range", "Accept-Ranges", "ETag", "Last-Modified",
)


@dataclass(frozen=True)
class _PreviewRoute:
    source: str
    headers: dict[str, str]


class _PreviewServer(ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = True

    def __init__(self, address, handler, routes, lock):
        super().__init__(address, handler)
        self.routes = routes
        self.routes_lock = lock
        self.session = requests.Session()


class _PreviewHandler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def do_HEAD(self):  # noqa: N802
        self._relay(include_body=False)

    def do_GET(self):  # noqa: N802
        self._relay(include_body=True)

    def _relay(self, *, include_body: bool):
        token = unquote(urlparse(self.path).path).removeprefix("/media/")
        with self.server.routes_lock:
            route = self.server.routes.get(token)
        if route is None:
            self.send_error(404)
            return

        headers = {
            str(key): str(value)
            for key, value in route.headers.items()
            if str(key).lower() not in {"host", "content-length", "accept-encoding"}
        }
        headers["Accept-Encoding"] = "identity"
        if self.headers.get("Range"):
            headers["Range"] = self.headers["Range"]

        response = None
        try:
            # Algunos CDN rechazan HEAD. GET sin enviar el cuerpo al cliente
            # permite que Qt consulte las mismas cabeceras de forma fiable.
            response = self.server.session.get(
                route.source,
                headers=headers,
                stream=True,
                timeout=(10, 45),
                allow_redirects=True,
            )
            self.send_response(response.status_code)
            for name in _RESPONSE_HEADERS:
                value = response.headers.get(name)
                if value:
                    self.send_header(name, value)
            self.end_headers()
            if include_body and response.status_code < 400:
                for chunk in response.iter_content(chunk_size=256 * 1024):
                    if chunk:
                        self.wfile.write(chunk)
        except (requests.RequestException, BrokenPipeError, ConnectionResetError, OSError):
            self.close_connection = True
        finally:
            if response is not None:
                response.close()

    def log_message(self, _format, *_args):
        return


class MediaPreviewProxy:
    """Expone streams firmados como recursos locales reproducibles por Qt."""

    def __init__(self):
        self._routes: dict[str, _PreviewRoute] = {}
        self._lock = threading.RLock()
        self._server: _PreviewServer | None = None
        self._thread: threading.Thread | None = None

    def url_for(self, source: str, headers: dict[str, str] | None = None) -> str:
        source = str(source or "").strip()
        if not source:
            return ""
        with self._lock:
            if self._server is None:
                self._server = _PreviewServer(("127.0.0.1", 0), _PreviewHandler, self._routes, self._lock)
                self._thread = threading.Thread(
                    target=self._server.serve_forever,
                    name="xomacito-media-preview",
                    daemon=True,
                )
                self._thread.start()
            token = secrets.token_urlsafe(18)
            self._routes[token] = _PreviewRoute(source, dict(headers or {}))
            port = self._server.server_address[1]
        return f"http://127.0.0.1:{port}/media/{token}"

    def shutdown(self):
        with self._lock:
            server = self._server
            thread = self._thread
            self._server = None
            self._thread = None
            self._routes.clear()
        if server is not None:
            server.shutdown()
            server.session.close()
            server.server_close()
        if thread is not None and thread.is_alive():
            thread.join(timeout=1.5)
