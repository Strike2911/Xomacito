"""Resolve the visible cookie source consistently across application tools."""
BROWSERS = {name.title(): name for name in ("chrome", "edge", "firefox", "brave", "opera", "vivaldi")}


def cookie_options(settings):
    mode = str(settings.get("cookies_mode", "No usar"))
    if mode == "No usar":
        return {}
    if mode == "Archivo Manual...":
        path = str(settings.get("cookies_path", ""))
        return {"cookiefile": path} if path else {}
    browser = BROWSERS.get(mode, str(settings.get("selected_browser", "chrome")).lower())
    profile = str(settings.get("browser_profile", ""))
    return {"cookiesfrombrowser": (browser, profile) if profile else (browser,)}
