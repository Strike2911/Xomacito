from .ytdlp_runtime import (
    configure_ytdlp_options,
    is_youtube_access_error,
    lazy_ytdlp,
    safe_console_print,
    youtube_access_fallback_options,
)

yt_dlp = lazy_ytdlp()
from .exceptions import UserCancelledError, PlaylistDownloadError
from html import unescape
from html.parser import HTMLParser
import threading 
import os
import re
import sys
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import requests


class _OpenGraphParser(HTMLParser):
    """Extrae metadatos Open Graph sin añadir otra dependencia al instalador."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.values = {}

    def handle_starttag(self, tag, attrs):
        if tag.lower() != "meta":
            return
        attributes = {str(key).lower(): value for key, value in attrs if key}
        property_name = str(attributes.get("property") or attributes.get("name") or "").lower()
        content = attributes.get("content")
        if property_name in {
            "og:image", "og:title", "og:description", "og:video",
            "og:video:url", "og:video:secure_url", "twitter:player:stream",
            "twitter:player:stream:url",
        } and content:
            self.values.setdefault(property_name, unescape(str(content)).strip())


class _InstagramImageParser(HTMLParser):
    """Collects the actual publication images exposed by Instagram embeds."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.images = []

    def handle_starttag(self, tag, attrs):
        if tag.lower() != "img":
            return
        attributes = {str(key).lower(): value for key, value in attrs if key}
        candidate = str(attributes.get("src") or "").strip()
        try:
            width = int(str(attributes.get("width") or "0").split(".", 1)[0])
            height = int(str(attributes.get("height") or "0").split(".", 1)[0])
        except ValueError:
            width = height = 0
        # Instagram profile avatars are small and are not part of a carousel.
        if candidate.startswith("https://") and not (width and height and max(width, height) < 240):
            if candidate not in self.images:
                self.images.append(unescape(candidate))


def is_instagram_post_url(url):
    """Devuelve True solo para publicaciones /p/ alojadas realmente en Instagram."""
    try:
        parsed = urlparse(str(url).strip())
    except (TypeError, ValueError):
        return False
    hostname = (parsed.hostname or "").lower()
    is_instagram = hostname == "instagram.com" or hostname.endswith(".instagram.com")
    return parsed.scheme in {"http", "https"} and is_instagram and bool(
        re.match(r"^/p/[^/]+/?$", parsed.path)
    )


def is_instagram_reel_url(url):
    """Return True for public Instagram reel URLs without treating them as photos."""
    try:
        parsed = urlparse(str(url).strip())
    except (TypeError, ValueError):
        return False
    hostname = (parsed.hostname or "").lower()
    is_instagram = hostname == "instagram.com" or hostname.endswith(".instagram.com")
    return parsed.scheme in {"http", "https"} and is_instagram and bool(
        re.match(r"^/(?:reel|reels|tv)/[^/]+/?$", parsed.path)
    )


def is_x_status_url(url):
    """Return True for canonical X/Twitter status links, including /photo/N."""
    try:
        parsed = urlparse(str(url).strip())
    except (TypeError, ValueError):
        return False
    hostname = (parsed.hostname or "").lower()
    if hostname not in {"x.com", "www.x.com", "twitter.com", "www.twitter.com"}:
        return False
    return bool(re.match(r"^/[^/]+/status/(\d+)(?:/(?:photo|video)/(\d+))?/?$", parsed.path))


def extract_x_media_post_info(url, timeout=25, session=None):
    """Resolve X photos, carousels and GIFs through public media metadata.

    yt-dlp treats links ending in ``/photo/1`` as video selectors and can reject
    animated GIF posts with "Media #1 is not a video". FxTwitter exposes the
    same public post metadata without credentials, so it is a reliable fallback
    for both still images and directly downloadable MP4 variants.
    """
    if not is_x_status_url(url):
        return None
    parsed = urlparse(str(url).strip())
    match = re.search(r"/status/(\d+)", parsed.path)
    if not match:
        return None
    status_id = match.group(1)
    client = session or requests.Session()
    response = client.get(
        f"https://api.fxtwitter.com/status/{status_id}",
        timeout=timeout,
        headers={"User-Agent": "Xomacito/3 (+https://github.com/Strike2911/Xomacito)"},
    )
    response.raise_for_status()
    tweet = (response.json() or {}).get("tweet") or {}
    media_payload = tweet.get("media") or {}
    if isinstance(media_payload, dict):
        media = media_payload.get("all") or media_payload.get("media") or []
    elif isinstance(media_payload, list):
        # FxTwitter has returned both a media object and a media list over
        # time. Supporting both keeps X posts from silently falling back to
        # lower-quality extractor formats.
        media = media_payload
    else:
        media = []
    media = [item for item in media if isinstance(item, dict)]
    if not media:
        return None
    title = str(tweet.get("text") or f"X_{status_id}").strip()
    author = (tweet.get("author") or {}).get("screen_name") or "X"
    images = [
        str(item.get("url") or "") for item in media
        if str(item.get("type") or "").lower() in {"photo", "image"} and item.get("url")
    ]
    video_items = [
        item for item in media
        if str(item.get("type") or "").lower() in {"video", "gif", "animated_gif"}
        or item.get("variants") or item.get("formats")
    ]
    if images and not video_items:
        return {
            "id": status_id,
            "title": title,
            "description": title,
            "uploader": author,
            "thumbnail": images[0],
            "url": images[0],
            "webpage_url": str(url).strip(),
            "original_url": str(url).strip(),
            "extractor": "x:image",
            "extractor_key": "XImage",
            "xomacito_media_type": "image",
            "xomacito_images": images,
            "image_count": len(images),
            "formats": [],
            "subtitles": {},
            "automatic_captions": {},
        }
    # A post can contain photos followed by a video. Prefer the first item
    # that actually contains playable variants instead of blindly selecting
    # media[0].
    selected = video_items[0] if video_items else media[0]
    formats = []
    variants = selected.get("variants") or selected.get("formats") or []
    for index, variant in enumerate(variants):
        direct_url = variant.get("url")
        content_type = str(variant.get("content_type") or "").lower()
        source_path = urlparse(str(direct_url or "")).path.lower()
        if (
            not direct_url
            or "mpegurl" in content_type
            or source_path.endswith(".m3u8")
            or (content_type and "mp4" not in content_type and ".mp4" not in source_path)
        ):
            continue
        try:
            width = int(variant.get("width") or variant.get("w") or selected.get("width") or 0)
            height = int(variant.get("height") or variant.get("h") or selected.get("height") or 0)
            bitrate = float(
                variant.get("bit_rate") or variant.get("bitrate")
                or variant.get("bitrate_bps") or 0
            )
        except (TypeError, ValueError):
            width = height = 0
            bitrate = 0
        formats.append({
            "format_id": f"x-{index}",
            "url": direct_url,
            "ext": "mp4",
            "protocol": "https",
            "vcodec": variant.get("codec") or "h264",
            "acodec": "none" if selected.get("type") == "gif" else "aac",
            "tbr": (bitrate / 1000.0) or None,
            "width": width or selected.get("width"),
            "height": height or selected.get("height"),
            # yt-dlp uses this while resolving "best". Prefer pixels first,
            # then the higher bitrate version of the same resolution.
            "preference": int(width * height + bitrate),
        })
    direct_url = selected.get("url")
    if direct_url and not formats:
        formats.append({
            "format_id": "x-direct", "url": direct_url, "ext": "mp4",
            "protocol": "https", "vcodec": "h264", "acodec": "none",
            "width": selected.get("width"), "height": selected.get("height"),
        })
    if not formats:
        return None
    formats.sort(
        key=lambda item: (
            int(item.get("width") or 0) * int(item.get("height") or 0),
            float(item.get("tbr") or 0),
        ),
        reverse=True,
    )
    for rank, item in enumerate(formats, 1):
        item["format_id"] = f"x-mp4-{rank}"
    return {
        "id": status_id,
        "title": title,
        "description": title,
        "uploader": author,
        "thumbnail": selected.get("thumbnail_url") or "",
        "webpage_url": str(url).strip(),
        "original_url": str(url).strip(),
        "extractor": "x:media",
        "extractor_key": "XMedia",
        "formats": formats,
        "duration": selected.get("duration") or 0,
        "width": selected.get("width"),
        "height": selected.get("height"),
    }


def _instagram_image_title(raw_title, shortcode):
    title = unescape(str(raw_title or "")).strip()
    match = re.match(r"^.+?\s+on\s+Instagram:\s*[\"“]?(.*?)[\"”]?\s*$", title, re.IGNORECASE)
    if match and match.group(1).strip():
        title = match.group(1).strip().strip('"“”')
    return title or f"Instagram_{shortcode}"


def _instagram_entry_image_url(entry):
    """Return an image URL only when yt-dlp did not expose playable video."""
    if not isinstance(entry, dict):
        return ""
    image_extensions = {"jpg", "jpeg", "png", "webp", "avif"}
    entry_ext = str(entry.get("ext") or "").lower().lstrip(".")
    formats = [item for item in (entry.get("formats") or []) if isinstance(item, dict)]
    has_video = any(
        str(item.get("vcodec") or "none").lower() not in {"", "none"}
        and str(item.get("ext") or "").lower() not in image_extensions
        for item in formats
    )
    if has_video:
        return ""
    candidates = [entry.get("url"), entry.get("thumbnail")]
    candidates.extend(
        thumbnail.get("url")
        for thumbnail in (entry.get("thumbnails") or [])
        if isinstance(thumbnail, dict)
    )
    for candidate in candidates:
        if not candidate:
            continue
        suffix = Path(urlparse(str(candidate)).path).suffix.lower().lstrip(".")
        if entry_ext in image_extensions or suffix in image_extensions or not formats:
            return str(candidate)
    return ""


def _instagram_images_from_html(html):
    """Collect public carousel images embedded in Instagram's page payload."""
    found = []
    patterns = (
        r'"display_url"\s*:\s*"([^"]+)"',
        r'"image_url"\s*:\s*"([^"]+)"',
    )
    for pattern in patterns:
        for value in re.findall(pattern, str(html or "")):
            candidate = unescape(value).replace(r"\/", "/").replace(r"\u0026", "&")
            if candidate.startswith("https://") and candidate not in found:
                found.append(candidate)
    parser = _InstagramImageParser()
    try:
        parser.feed(str(html or ""))
    except (TypeError, ValueError):
        pass
    for candidate in parser.images:
        if candidate not in found:
            found.append(candidate)
    return found


def _instagram_videos_from_html(html):
    """Extract direct MP4 URLs exposed by Instagram reel pages and embeds."""
    found = []
    patterns = (
        r'"video_url"\s*:\s*"([^"]+)"',
        r'"contentUrl"\s*:\s*"([^"]+)"',
        r'"video_versions"\s*:\s*\[[^\]]*?"url"\s*:\s*"([^"]+)"',
    )
    for pattern in patterns:
        for value in re.findall(pattern, str(html or ""), flags=re.IGNORECASE | re.DOTALL):
            candidate = unescape(value).replace(r"\/", "/").replace(r"\u0026", "&").replace(r"\u003d", "=")
            # Instagram CDN video URLs are frequently extensionless. The
            # surrounding field already identifies these as video resources,
            # so requiring a literal .mp4 loses otherwise valid reels.
            if candidate.startswith("https://") and candidate not in found:
                found.append(candidate)
    return found


def _instagram_public_pages(url):
    """Yield canonical and embed pages while preserving the Instagram media type."""
    parsed = urlparse(str(url).strip())
    parts = [part for part in parsed.path.strip("/").split("/") if part]
    shortcode = parts[-1]
    media_kind = parts[-2].lower() if len(parts) > 1 else "p"
    if media_kind not in {"p", "reel", "reels", "tv"}:
        media_kind = "p"
    canonical = f"https://www.instagram.com/{media_kind}/{shortcode}/"
    embed_pages = [canonical, f"{canonical}embed/"]
    if media_kind == "p":
        embed_pages.insert(1, f"{canonical}embed/captioned/")
    return canonical, (
        *embed_pages,
    )


def _instagram_requests_client(ydl_options=None, session=None):
    """Build a requests client that reuses the cookies selected in Settings."""
    if session is not None:
        return session
    client = requests.Session()
    if not ydl_options:
        return client
    cookie_options = {
        key: ydl_options[key]
        for key in ("cookiefile", "cookiesfrombrowser")
        if ydl_options.get(key)
    }
    if not cookie_options:
        return client
    try:
        with yt_dlp.YoutubeDL({"quiet": True, "no_warnings": True, **cookie_options}) as ydl:
            for cookie in ydl.cookiejar:
                client.cookies.set(
                    cookie.name, cookie.value, domain=cookie.domain, path=cookie.path,
                )
    except Exception:
        pass
    return client


def _instagram_api_images(payload):
    """Return the best image of every slide from Instagram's media-info JSON."""
    try:
        item = (payload.get("items") or [])[0]
    except (AttributeError, IndexError, TypeError):
        return []
    slides = item.get("carousel_media") or [item]
    images = []
    for slide in slides:
        candidates = ((slide.get("image_versions2") or {}).get("candidates") or [])
        candidates = [candidate for candidate in candidates if candidate.get("url")]
        if not candidates:
            continue
        best = max(
            candidates,
            key=lambda candidate: int(candidate.get("width") or 0) * int(candidate.get("height") or 0),
        )
        image_url = str(best["url"])
        if image_url not in images:
            images.append(image_url)
    return images


def _instagram_authenticated_carousel(client, canonical, timeout, headers):
    """Resolve carousel slides through Instagram's authenticated media API."""
    try:
        oembed = client.get(
            "https://www.instagram.com/api/v1/oembed/",
            params={"url": canonical}, timeout=timeout, headers=headers,
        )
        oembed.raise_for_status()
        oembed_data = oembed.json()
    except Exception:
        return [], {}
    media_id = str(oembed_data.get("media_id") or "").strip()
    if not media_id:
        return [], oembed_data
    api_headers = {
        **headers,
        "Referer": canonical,
        "X-IG-App-ID": "936619743392459",
        "X-ASBD-ID": "129477",
    }
    try:
        response = client.get(
            f"https://i.instagram.com/api/v1/media/{media_id}/info/",
            timeout=timeout, headers=api_headers,
        )
        response.raise_for_status()
        return _instagram_api_images(response.json()), oembed_data
    except Exception:
        return [], oembed_data


def instagram_image_post_info_from_metadata(url, metadata):
    """Convierte metadatos sin formatos de video en una imagen descargable."""
    if not is_instagram_post_url(url) or not isinstance(metadata, dict):
        return None

    selected = metadata
    entries = [entry for entry in (metadata.get("entries") or []) if isinstance(entry, dict)]
    entry_index = 0
    if metadata.get("_type") in {"playlist", "multi_video"} and entries:
        requested_index = parse_qs(urlparse(str(url)).query).get("img_index", ["1"])[0]
        try:
            entry_index = max(0, int(requested_index) - 1)
        except (TypeError, ValueError):
            entry_index = 0
        entry_index = min(entry_index, len(entries) - 1)
        selected = entries[entry_index] or {}

    image_urls = []
    for entry in entries or [selected]:
        candidate = _instagram_entry_image_url(entry)
        if candidate and candidate not in image_urls:
            image_urls.append(candidate)
    if not image_urls:
        candidate = _instagram_entry_image_url(selected)
        if not candidate:
            return None
        image_urls = [candidate]

    shortcode = urlparse(str(url).strip()).path.strip("/").split("/")[-1]
    raw_title = str(selected.get("title") or "").strip()
    description = selected.get("description") or metadata.get("description")
    title_source = description if raw_title.lower().startswith("video by ") else (raw_title or description)
    title = _instagram_image_title(title_source, shortcode)
    if len(entries) > 1:
        title = f"{title} - {entry_index + 1}"

    return {
        **selected,
        "id": selected.get("id") or shortcode,
        "title": title,
        "description": selected.get("description") or metadata.get("description") or "",
        "thumbnail": selected.get("thumbnail") or image_urls[0],
        "webpage_url": str(url).strip(),
        "original_url": str(url).strip(),
        "extractor": "instagram:image",
        "extractor_key": "InstagramImage",
        "xomacito_media_type": "image",
        "xomacito_images": image_urls,
        "image_count": len(image_urls),
        "formats": [],
        "subtitles": {},
        "automatic_captions": {},
    }


def extract_instagram_image_post_info(url, timeout=30, session=None, ydl_options=None):
    """
    Crea metadatos sintéticos para una publicación pública de imagen.

    yt-dlp está orientado a audio/video y responde "There is no video in this
    post" ante fotos. En ese caso se usa la imagen Open Graph publicada por
    Instagram; Reels y videos continúan en el flujo normal de yt-dlp.
    """
    if not is_instagram_post_url(url):
        return None

    if ydl_options is not None:
        metadata_options = dict(ydl_options)
        metadata_options.update({
            "ignore_no_formats_error": True,
            "skip_download": True,
            "noplaylist": False,
        })
        try:
            with yt_dlp.YoutubeDL(metadata_options) as ydl:
                metadata = ydl.extract_info(str(url).strip(), download=False)
            image_info = instagram_image_post_info_from_metadata(url, metadata)
            if image_info:
                return image_info
        except Exception:
            # Respaldo para cambios frecuentes de la API pública de Instagram.
            pass

    client = _instagram_requests_client(ydl_options, session)
    canonical, public_pages = _instagram_public_pages(url)
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/126 Safari/537.36",
        "Accept-Language": "es-ES,es;q=0.9,en;q=0.7",
    }
    parser = _OpenGraphParser()
    image_urls = []
    api_images, oembed_data = _instagram_authenticated_carousel(
        client, canonical, timeout, headers,
    )
    image_urls.extend(api_images)
    # The regular page often exposes only the first slide. Public embed pages
    # include the carousel payload without requiring an authenticated session.
    for page_url in public_pages:
        try:
            response = client.get(
                page_url, timeout=timeout, allow_redirects=True, headers=headers,
            )
            response.raise_for_status()
        except Exception:
            continue
        page_parser = _OpenGraphParser()
        page_parser.feed(response.text)
        if not parser.values:
            parser = page_parser
        page_images = _instagram_images_from_html(response.text)
        image_url = page_parser.values.get("og:image")
        if image_url and image_url not in page_images:
            page_images.insert(0, image_url)
        for item in page_images:
            if item not in image_urls:
                image_urls.append(item)
        if len(image_urls) > 1:
            break
    image_urls = [item for item in image_urls if urlparse(item).scheme == "https"]
    if not image_urls:
        return None
    image_url = image_urls[0]

    shortcode = urlparse(canonical).path.strip("/").split("/")[-1]
    return instagram_image_post_info_from_metadata(url, {
        "id": shortcode,
        "title": _instagram_image_title(
            parser.values.get("og:title") or oembed_data.get("title"), shortcode,
        ),
        "description": parser.values.get("og:description", ""),
        "thumbnail": image_url,
        "url": image_url,
        "entries": [
            {"id": f"{shortcode}-{index}", "thumbnail": item, "url": item, "ext": "jpg"}
            for index, item in enumerate(image_urls, 1)
        ],
        "_type": "playlist" if len(image_urls) > 1 else "video",
        "formats": [],
    })


def extract_instagram_reel_info(url, timeout=30, session=None, ydl_options=None):
    """Build playable metadata from the MP4 references exposed by a Reel page.

    Instagram occasionally replies to yt-dlp with an empty format list even
    though the browser-facing page still exposes its Open Graph video URL.
    Keeping this narrowly scoped to reel URLs avoids treating image carousels
    as videos while providing a useful fallback for public reels.
    """
    if not is_instagram_reel_url(url):
        return None

    client = _instagram_requests_client(ydl_options, session)
    canonical, public_pages = _instagram_public_pages(url)
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/126 Safari/537.36",
        "Accept-Language": "es-ES,es;q=0.9,en;q=0.7",
        "Referer": canonical,
    }
    shortcode = urlparse(canonical).path.strip("/").split("/")[-1]
    for page_url in public_pages:
        try:
            response = client.get(page_url, timeout=timeout, allow_redirects=True, headers=headers)
            response.raise_for_status()
        except Exception:
            continue

        parser = _OpenGraphParser()
        try:
            parser.feed(response.text)
        except (TypeError, ValueError):
            pass

        urls = []
        for field in (
            "og:video:secure_url", "og:video:url", "og:video",
            "twitter:player:stream:url", "twitter:player:stream",
        ):
            candidate = str(parser.values.get(field) or "").strip()
            if candidate.startswith("https://") and candidate not in urls:
                urls.append(candidate)
        for candidate in _instagram_videos_from_html(response.text):
            if candidate not in urls:
                urls.append(candidate)

        formats = []
        for index, candidate in enumerate(urls, 1):
            formats.append({
                "format_id": f"instagram-reel-{index}",
                "url": candidate,
                "ext": "mp4",
                "protocol": "https",
                "vcodec": "h264",
                "acodec": "aac",
                "preference": len(urls) - index + 1,
            })
        if not formats:
            continue

        thumbnail = str(parser.values.get("og:image") or "").strip()
        title = _instagram_image_title(parser.values.get("og:title"), shortcode)
        return {
            "id": shortcode,
            "title": title,
            "description": str(parser.values.get("og:description") or ""),
            "thumbnail": thumbnail,
            "webpage_url": str(url).strip(),
            "original_url": str(url).strip(),
            "extractor": "instagram:reel",
            "extractor_key": "InstagramReel",
            "formats": formats,
            "url": formats[0]["url"],
            "ext": "mp4",
            "vcodec": "h264",
            "acodec": "aac",
            "subtitles": {},
            "automatic_captions": {},
        }
    return None

def get_deno_path():
    """Obtiene la ruta absoluta de la carpeta donde está deno.exe."""
    if getattr(sys, 'frozen', False):
        root = os.path.dirname(sys.executable)
    else:
        root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    return os.path.join(root, "bin", "deno")

def apply_yt_patch(ydl_opts):
    """Configuración optimizada SOLO para cuando se usan cookies."""
    if getattr(sys, 'frozen', False):
        root = os.path.dirname(sys.executable)
    else:
        root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    
    # Detectar plataforma
    if sys.platform == "win32":
        deno_executable = "deno.exe"
    else:
        deno_executable = "deno"
    
    deno_path = os.path.join(root, "bin", "deno", deno_executable)
    
    # Verificar Deno
    if not os.path.exists(deno_path):
        safe_console_print(f"⚠️ Deno no encontrado en {deno_path}")
        import shutil
        system_deno = shutil.which("deno")
        if system_deno:
            deno_path = system_deno
            safe_console_print(f"✅ Usando Deno del sistema: {deno_path}")
        else:
            safe_console_print("❌ Deno no disponible. El parche puede no funcionar correctamente.")
            return ydl_opts
    
    # Configuración para cookies
    ydl_opts['quiet'] = False
    ydl_opts['no_warnings'] = False
    
    ydl_opts['js_runtimes'] = {
        'deno': {
            'path': deno_path
        }
    }
    
    ydl_opts['remote_components'] = ['ejs:github']
    
    if 'extractor_args' not in ydl_opts:
        ydl_opts['extractor_args'] = {}
    
    youtube_args = ydl_opts['extractor_args'].setdefault('youtube', {})
    youtube_args['player_client'] = ['tv', 'default', '-android_sdkless', '-android_vr']
    youtube_args.pop('n_client', None)
    
    safe_console_print(f"✅ Parche aplicado (con cookies). Deno: {deno_path}")
    return ydl_opts


def extract_info_resilient(url, ydl_opts, download=False, progress_callback=None):
    """Ejecuta yt-dlp y reintenta bloqueos de YouTube con un cliente seguro alternativo."""
    configured_opts = configure_ytdlp_options(ydl_opts)

    def run(options):
        with yt_dlp.YoutubeDL(options) as ydl:
            return ydl.extract_info(url, download=download)

    try:
        return run(configured_opts)
    except Exception as error:
        if not is_youtube_access_error(url, error):
            raise

        if progress_callback:
            progress_callback(-1, "YouTube rechazó el enlace. Reintentando con conexión alternativa...")
        safe_console_print(f"YouTube bloqueó el primer cliente ({error}). Reintentando con web_embedded.")
        fallback_opts = youtube_access_fallback_options(configured_opts)
        return run(fallback_opts)


def get_video_info(url, cookie_opts=None):
    ydl_opts = {
        'quiet': True,
        'no_warnings': True,  # Cambiar a True para modo sin cookies
        'skip_download': True,
        'timeout': 30,
        'impersonate': True, 
    }
    
    ydl_opts = configure_ytdlp_options(ydl_opts)
    use_cookies = False
    
    # Manejo de cookies
    if cookie_opts:
        if 'cookiefile' in cookie_opts and cookie_opts['cookiefile']:
            ydl_opts['cookiefile'] = cookie_opts['cookiefile']
            use_cookies = True
        elif 'cookiesfrombrowser' in cookie_opts and cookie_opts['cookiesfrombrowser']:
            ydl_opts['cookiesfrombrowser'] = cookie_opts['cookiesfrombrowser']
            use_cookies = True
    
    # 🔧 SOLO aplicar parche si hay cookies
    if use_cookies:
        ydl_opts = apply_yt_patch(ydl_opts)
        safe_console_print("📝 Modo: Con cookies (parche aplicado)")
    else:
        safe_console_print("📝 Modo: Sin cookies (configuración predeterminada de yt-dlp)")

    try:
        info_dict = extract_info_resilient(url, ydl_opts, download=False)

        if info_dict:
            info_dict = apply_site_specific_rules(info_dict)

        return info_dict
    except Exception as e:
        safe_console_print(f"ERROR en get_video_info: {e}")
        return None


def download_media(url, ydl_opts, progress_callback, cancellation_event: threading.Event):
    """
    Descarga y procesa el medio.
    """
    ydl_opts = configure_ytdlp_options(ydl_opts)
    
    # 🔧 DETECTAR si hay cookies en ydl_opts
    use_cookies = 'cookiefile' in ydl_opts or 'cookiesfrombrowser' in ydl_opts
    
    # 🔧 SOLO aplicar parche si hay cookies
    if use_cookies:
        ydl_opts = apply_yt_patch(ydl_opts)
        safe_console_print("📥 Descarga: Con cookies (parche aplicado)")
    else:
        safe_console_print("📥 Descarga: Sin cookies (configuración predeterminada de yt-dlp)")
    
    # Variables para tracking de progreso en fragmentos
    is_fragment = 'download_ranges' in ydl_opts
    fragment_started = False
    
    def hook(d):
        nonlocal fragment_started
        
        if cancellation_event.is_set():
            safe_console_print("DEBUG: Evento de cancelación detectado en el hook de yt-dlp.")
            raise UserCancelledError("Descarga cancelada por el usuario.")
        
        status = d.get('status', 'N/A')
        
        if status == 'downloading':
            fragment_started = True
            
            total_bytes = d.get('total_bytes') or d.get('total_bytes_estimate', 0)
            downloaded_bytes = d.get('downloaded_bytes', 0)
            
            if total_bytes > 0:
                percentage = (downloaded_bytes / total_bytes) * 100
                speed = d.get('speed')
                
                if speed:
                    speed_mb = speed / 1024 / 1024
                    if speed_mb >= 1.0:
                        speed_str = f"{speed_mb:.1f} MB/s"
                    else:
                        speed_kb = speed / 1024
                        speed_str = f"{speed_kb:.0f} KB/s"
                else:
                    speed_str = "N/A"

                download_type = "fragmento" if is_fragment else "archivo"
                progress_callback(percentage, f"Descargando {download_type}... {percentage:.1f}% a {speed_str}")
            
            elif is_fragment:
                elapsed = d.get('elapsed', 0)
                progress_callback(-1, f"Descargando fragmento... {elapsed:.0f}s transcurridos")
        
        elif status == 'finished':
            if is_fragment:
                progress_callback(-1, "Fragmento descargado. Procesando con FFmpeg...")
            else:
                progress_callback(95, "Descarga completada. Fusionando archivos si es necesario...")
        
        elif status == 'error':
            raise yt_dlp.utils.DownloadError("yt-dlp reportó un error durante la descarga.")
    
    ydl_opts['progress_hooks'] = [hook]
    ydl_opts.setdefault('downloader', 'native')
    
    if 'outtmpl' in ydl_opts:
        ydl_opts['restrictfilenames'] = True 
    
    try:
        if cancellation_event.is_set():
            raise UserCancelledError("Descarga cancelada por el usuario antes de iniciar.")
        
        if is_fragment:
            progress_callback(-1, "Descargando fragmento, esto puede tardar...")
        
        info_dict = extract_info_resilient(
            url,
            ydl_opts,
            download=True,
            progress_callback=progress_callback,
        )
        
        if is_fragment and not fragment_started:
            progress_callback(-1, "Fragmento extraído. Finalizando...")
        
        final_filepath = info_dict.get('filepath')
        if not final_filepath and 'requested_downloads' in info_dict:
            final_filepath = info_dict['requested_downloads'][0].get('filepath')
            
        if not final_filepath:
            raise PlaylistDownloadError("No se pudo determinar la ruta del archivo descargado después del proceso.")
        
        progress_callback(100, "✅ Descarga completada exitosamente")
        
        return final_filepath
        
    except UserCancelledError as e:
        safe_console_print(f"DEBUG: Operación de descarga interrumpida: {e}")
        raise e
    except Exception as e:
        safe_console_print(f"Error en el proceso de descarga de yt-dlp: {e}")
        raise e
    
# =========================================================
# 🆕 SECCIÓN DE REGLAS ESPECÍFICAS POR SITIO
# =========================================================

def apply_site_specific_rules(info):
    """
    Normaliza metadatos de sitios problemáticos antes de que la UI los procese.
    """
    if not info:
        return info

    extractor = info.get('extractor_key', '').lower()
    url = info.get('webpage_url', '').lower()
    
    # Filtro Estricto para Clips de Twitch
    is_twitch_clip = 'clips' in extractor or '/clip/' in url
    
    if is_twitch_clip:
        safe_console_print(f"DEBUG: 🚑 Aplicando parche de compatibilidad para Twitch CLIP ({extractor})")
        info = _fix_twitch_clip_formats(info)

    return info

def _fix_twitch_clip_formats(info):
    """
    Asigna códecs falsos (h264/aac) si faltan, para que la UI habilite los menús.
    """
    formats = info.get('formats', [])
    
    for f in formats:
        # ✅ CORRECCIÓN: Detectar explícitamente None, 'none' y 'unknown'
        vcodec = f.get('vcodec')
        acodec = f.get('acodec')

        # Si el video es desconocido o nulo -> Forzar H.264
        if not vcodec or vcodec == 'none' or vcodec == 'unknown':
            f['vcodec'] = 'h264'
        
        # Si el audio es desconocido o nulo -> Forzar AAC
        if not acodec or acodec == 'none' or acodec == 'unknown':
            f['acodec'] = 'aac'
            
        # Asegurar contenedor MP4
        if not f.get('ext') or f.get('ext') == 'unknown':
            f['ext'] = 'mp4'

    return info
