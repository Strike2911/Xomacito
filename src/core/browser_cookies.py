"""Resolve the visible cookie source consistently across application tools."""
from pathlib import Path
from urllib.parse import urlparse

BROWSERS = {name.title(): name for name in ("chrome", "edge", "firefox", "brave", "opera", "vivaldi")}


def cookie_options(settings, url=""):
    host = (urlparse(str(url)).hostname or "").lower()
    tiktok_path = str(settings.get("tiktok_cookies_path", ""))
    if tiktok_path and (host == "tiktok.com" or host.endswith(".tiktok.com")):
        return {"cookiefile": tiktok_path}
    mode = str(settings.get("cookies_mode", "No usar"))
    if mode == "No usar":
        return {}
    if mode == "Archivo Manual...":
        path = str(settings.get("cookies_path", ""))
        return {"cookiefile": path} if path else {}
    browser = BROWSERS.get(mode, str(settings.get("selected_browser", "chrome")).lower())
    profile = str(settings.get("browser_profile", ""))
    return {"cookiesfrombrowser": (browser, profile) if profile else (browser,)}


def import_tiktok_cookies(source, destination):
    """Keep only TikTok cookies, never persist an all-sites export."""
    source = Path(source)
    rows = []
    for line in source.read_text(encoding="utf-8-sig").splitlines():
        if line.startswith("#") and not line.startswith("#HttpOnly_"):
            continue
        fields = line.split("\t")
        if len(fields) != 7:
            continue
        host = fields[0].removeprefix("#HttpOnly_").lstrip(".").lower()
        if host == "tiktok.com" or host.endswith(".tiktok.com"):
            rows.append(fields)
    if not rows:
        raise ValueError("El archivo no contiene cookies de TikTok. Abre el video en tu navegador y exporta desde esa pestaña usando Export, no Export All Cookies.")
    if not any(row[5] in ("sessionid", "sessionid_ss", "sid_tt") and row[6] for row in rows):
        raise ValueError("La exportación de TikTok no contiene una sesión iniciada. Inicia sesión, comprueba que el video se reproduce y vuelve a exportar.")
    destination = Path(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text("# Netscape HTTP Cookie File\n" + "\n".join("\t".join(row) for row in rows) + "\n", encoding="utf-8")
    return len(rows)
