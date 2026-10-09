"""Small public-catalog adapters. Credentials belong to the user, never the build."""
from __future__ import annotations

import hashlib
import html
import json
import re
import time
from pathlib import Path
from urllib.parse import urlsplit

import requests

PROVIDERS = {
    "Wikimedia": ("Imagen", "Video", "Audio"),
    "Openverse": ("Imagen", "Audio"),
    "Freesound": ("Audio",),
    "Pixabay": ("Imagen", "Video"),
    "Pexels": ("Imagen", "Video"),
}
KEY_PROVIDERS = {"Freesound", "Pixabay", "Pexels"}
HEADERS = {"User-Agent": "Xomacito/1.3 (https://github.com/Strike2911/Xomacito; desktop media library)"}


def plain(value):
    return html.unescape(re.sub(r"<[^>]+>", "", str(value or ""))).strip()


def web_url(value):
    value = str(value or "")
    try:
        parsed = urlsplit(value)
        return value if parsed.scheme in {"http", "https"} and parsed.hostname else ""
    except ValueError:
        return ""


def _get(url, params, headers=None):
    try:
        response = requests.get(url, params=params, headers={**HEADERS, **(headers or {})}, timeout=(10, 25))
        if response.status_code in {401, 403}:
            raise ValueError("El proveedor rechazó el acceso. Revisa tu clave o abre su página.")
        if response.status_code == 429:
            raise ValueError("El proveedor alcanzó su límite temporal. Inténtalo más tarde.")
        response.raise_for_status()
        data = response.json()
    except requests.RequestException:
        # requests exceptions can contain API keys from query-string parameters.
        raise ValueError("No se pudo conectar con el catálogo. Inténtalo de nuevo.") from None
    if data.get("error"):
        raise ValueError("El catálogo no pudo completar la búsqueda.")
    return data


def _item(provider, identity, title, kind, url, thumb="", page="", creator="", license="", duration=0, width=0, height=0, preview="", note=""):
    url = web_url(url)
    if not url: return None
    suffix = Path(urlsplit(url).path).suffix.lower()
    return dict(id=str(identity), provider=provider, title=plain(title) or provider,
                kind=kind, downloadUrl=url, thumbnailSource=web_url(thumb), pageUrl=web_url(page),
                creator=plain(creator), license=plain(license) or "Consulta la licencia en el origen",
                duration=float(duration or 0), dimensions=f"{width} × {height}" if width and height else "—",
                previewSource=web_url(preview) or (web_url(thumb) if kind == 'Imagen' else '') or url, extension=suffix, note=note)


def search_catalog(provider, query, kind, page, key="", cache_dir=None):
    if provider not in PROVIDERS: raise ValueError("Catálogo desconocido.")
    if provider in KEY_PROVIDERS and not key:
        raise ValueError("Configura tu clave de " + provider + " para buscar.")
    kinds = PROVIDERS[provider] if kind == "Todos" else (kind,)
    if any(value not in PROVIDERS[provider] for value in kinds): return []
    page = max(1, int(page))
    # Pixabay requires 24h caching. The filename contains a hash, never the key.
    digest = hashlib.sha256(json.dumps([provider, query, kind, page, key]).encode()).hexdigest()
    cache = Path(cache_dir) / (digest + ".json") if cache_dir else None
    if cache and cache.is_file() and time.time() - cache.stat().st_mtime < 86400:
        try: return json.loads(cache.read_text(encoding="utf-8"))
        except (ValueError, OSError): pass
    rows = []
    if provider == "Wikimedia":
        data = _get("https://commons.wikimedia.org/w/api.php", {
            "action": "query", "format": "json", "generator": "search", "gsrsearch": query,
            "gsrnamespace": 6, "gsrlimit": 30, "gsroffset": (page-1)*30,
            "prop": "imageinfo", "iiprop": "url|size|mime|extmetadata", "iiurlwidth": 360,
        })
        for item in (data.get("query", {}).get("pages", {}) or {}).values():
            info = (item.get("imageinfo") or [{}])[0]
            mime = info.get("mime", "")
            media_kind = "Video" if mime.startswith("video/") else "Audio" if mime.startswith("audio/") else "Imagen" if mime.startswith("image/") else ""
            if media_kind not in kinds: continue
            meta = info.get("extmetadata", {})
            rows.append(_item(provider, item["pageid"], item.get("title", "").removeprefix("File:"), media_kind,
                info.get("url"), info.get("thumburl"), info.get("descriptionurl"),
                meta.get("Artist", {}).get("value"), meta.get("LicenseShortName", {}).get("value"),
                width=info.get("width"), height=info.get("height")))
    else:
        for media_kind in kinds:
            if provider == "Openverse":
                endpoint = "audio" if media_kind == "Audio" else "images"
                data = _get(f"https://api.openverse.org/v1/{endpoint}/", {"q": query, "page": page, "page_size": 20})
                for item in data.get("results", []):
                    rows.append(_item(provider, item["id"], item.get("title"), media_kind, item.get("url"),
                        item.get("thumbnail") or item.get("waveform"), item.get("foreign_landing_url"),
                        item.get("creator"), "CC " + str(item.get("license", "")).upper() + " " + str(item.get("license_version", "")),
                        duration=float(item.get("duration") or 0)/1000 if media_kind == "Audio" else 0,
                        width=item.get("width"), height=item.get("height")))
            elif provider == "Freesound":
                data = _get("https://freesound.org/apiv2/search/", {
                    "query": query, "page": page, "page_size": 30,
                    "fields": "id,name,url,username,license,previews,images,duration",
                }, {"Authorization": "Token " + key})
                for item in data.get("results", []):
                    preview = item.get("previews", {}).get("preview-hq-mp3")
                    rows.append(_item(provider, item["id"], item.get("name"), "Audio", preview,
                        item.get("images", {}).get("waveform_m"), item.get("url"), item.get("username"),
                        item.get("license"), duration=item.get("duration"), note="Previa MP3. El original se obtiene en Freesound."))
            elif provider == "Pexels":
                endpoint = "videos/search" if media_kind == "Video" else "search"
                data = _get("https://api.pexels.com/v1/" + endpoint, {"query": query, "page": page, "per_page": 20}, {"Authorization": key})
                for item in data.get("videos" if media_kind == "Video" else "photos", []):
                    if media_kind == "Video":
                        files = [file for file in item.get("video_files", []) if file.get("file_type") == "video/mp4"]
                        video = max(files, key=lambda file: int(file.get("width") or 0), default={})
                        url, thumb, creator = video.get("link"), item.get("image"), item.get("user", {}).get("name")
                    else:
                        url, thumb, creator = item.get("src", {}).get("original"), item.get("src", {}).get("medium"), item.get("photographer")
                    rows.append(_item(provider, item["id"], item.get("alt") or query, media_kind, url, thumb,
                        item.get("url"), creator, "Pexels License", duration=item.get("duration"),
                        width=item.get("width"), height=item.get("height")))
            elif provider == "Pixabay":
                data = _get("https://pixabay.com/api/" + ("videos/" if media_kind == "Video" else ""), {
                    "key": key, "q": query[:100], "page": page, "per_page": 20, "safesearch": "true",
                })
                for item in data.get("hits", []):
                    if media_kind == "Video":
                        video = item.get("videos", {}).get("large") or item.get("videos", {}).get("medium") or {}
                        url, thumb, width, height = video.get("url"), video.get("thumbnail"), video.get("width"), video.get("height")
                    else:
                        url, thumb = item.get("imageURL") or item.get("largeImageURL"), item.get("webformatURL")
                        width, height = item.get("imageWidth"), item.get("imageHeight")
                    rows.append(_item(provider, item["id"], item.get("tags") or query, media_kind, url, thumb,
                        item.get("pageURL"), item.get("user"), "Pixabay Content License",
                        duration=item.get("duration"), width=width, height=height,
                        note="" if media_kind == "Video" or item.get("imageURL") else "Imagen de hasta 1280 px ofrecida por la API."))
    rows = [row for row in rows if row]
    if cache:
        cache.parent.mkdir(parents=True, exist_ok=True)
        cache.write_text(json.dumps(rows, ensure_ascii=False), encoding="utf-8")
    return rows
