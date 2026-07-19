from __future__ import annotations

import importlib
import os
import re
import sys
import threading
from pathlib import Path


_LOAD_LOCK = threading.Lock()


class _LazyYtDlpModule:
    """Proxy que evita importar el motor completo hasta su primer uso real."""

    def __getattr__(self, name):
        return getattr(load_ytdlp(), name)

    def __dir__(self):
        return sorted(set(super().__dir__()) | set(dir(load_ytdlp())))


_LAZY_YTDLP = _LazyYtDlpModule()


def _roots() -> list[Path]:
    roots: list[Path] = []
    if getattr(sys, "frozen", False):
        executable_root = Path(sys.executable).resolve().parent
        roots.extend((executable_root / "_internal", executable_root, executable_root.parent))
    try:
        roots.extend(Path(__file__).resolve().parents)
    except OSError:
        pass
    return list(dict.fromkeys(roots))


def ytdlp_zip_path() -> Path | None:
    for root in _roots():
        candidate = root / "bin" / "ytdlp" / "yt-dlp.zip"
        if candidate.is_file():
            return candidate
    return None


def _add_tool_paths() -> None:
    current = os.environ.get("PATH", "").split(os.pathsep)
    additions: list[str] = []
    for root in _roots():
        for relative in (("bin", "deno"), ("bin", "ffmpeg")):
            candidate = root.joinpath(*relative)
            value = str(candidate)
            if candidate.is_dir() and value not in current and value not in additions:
                additions.append(value)
    if additions:
        os.environ["PATH"] = os.pathsep.join(additions + current)


def load_ytdlp():
    """Carga el ZipApp actualizable de yt-dlp en vez de la copia congelada."""
    with _LOAD_LOCK:
        _add_tool_paths()
        archive = ytdlp_zip_path()
        archive_value = str(archive) if archive else ""
        current = sys.modules.get("yt_dlp")
        current_file = str(getattr(current, "__file__", ""))
        if current is not None and (not archive_value or archive_value in current_file):
            return current

        if archive:
            sys.path[:] = [archive_value] + [entry for entry in sys.path if entry != archive_value]
            for name in tuple(sys.modules):
                if name == "yt_dlp" or name.startswith("yt_dlp."):
                    sys.modules.pop(name, None)
            importlib.invalidate_caches()
        return importlib.import_module("yt_dlp")


def lazy_ytdlp():
    """Devuelve un proxy compartido que carga yt-dlp solo cuando se utiliza."""
    return _LAZY_YTDLP


def configure_ytdlp_options(options: dict) -> dict:
    """Activa el Deno incluido para los desafíos JavaScript de YouTube."""
    _add_tool_paths()
    for root in _roots():
        deno = root / "bin" / "deno" / ("deno.exe" if os.name == "nt" else "deno")
        if deno.is_file():
            options.setdefault("js_runtimes", {"deno": {"path": str(deno)}})
            break
    options.setdefault("remote_components", ["ejs:github"])
    return options


def is_youtube_url(url: str) -> bool:
    lowered = str(url or "").lower()
    return any(host in lowered for host in ("youtube.com", "youtu.be", "youtube-nocookie.com"))


def is_youtube_access_error(url: str, error: object) -> bool:
    """Detecta bloqueos temporales de YouTube que admiten un cliente alternativo."""
    if not is_youtube_url(url):
        return False
    lowered = str(error).lower()
    markers = (
        "http error 403",
        "403: forbidden",
        "http error 429",
        "too many requests",
        "sign in to confirm you’re not a bot",
        "sign in to confirm you're not a bot",
        "confirm you are not a bot",
        "missing required visitor data",
    )
    return any(marker in lowered for marker in markers)


def youtube_access_fallback_options(options: dict) -> dict:
    """Crea un segundo intento aislado sin alterar las opciones originales."""
    fallback = dict(options)
    extractor_args = {
        key: dict(value) if isinstance(value, dict) else value
        for key, value in options.get("extractor_args", {}).items()
    }
    youtube_args = dict(extractor_args.get("youtube", {}))

    if fallback.get("cookiefile") or fallback.get("cookiesfrombrowser"):
        youtube_args["player_client"] = ["tv", "default", "-android_sdkless", "-android_vr"]
    else:
        youtube_args["player_client"] = ["web_embedded"]

    youtube_args.pop("n_client", None)
    youtube_args["skip"] = []
    extractor_args["youtube"] = youtube_args
    fallback["extractor_args"] = extractor_args

    # Deja que yt-dlp aplique los encabezados vinculados al cliente alternativo.
    fallback.pop("user_agent", None)
    fallback.pop("referer", None)
    fallback.pop("impersonate", None)
    return configure_ytdlp_options(fallback)


def friendly_ytdlp_error(error: object, log_lines: list[str] | None = None) -> str:
    parts = [str(error)]
    if log_lines:
        parts.extend(str(line) for line in log_lines)
    raw = " ".join(part.strip() for part in parts if part and part.strip())
    lowered = raw.lower()
    if "429" in lowered or "too many requests" in lowered:
        return (
            "YouTube limitó temporalmente las solicitudes. Xomacito probó también el cliente alternativo; "
            "si continúa, espera unos minutos o activa Cookies en Ajustes."
        )
    if "403" in lowered or "forbidden" in lowered:
        return (
            "YouTube rechazó temporalmente el enlace de descarga (error 403). "
            "Xomacito probó el cliente alternativo; si continúa, vuelve a analizar o activa Cookies en Ajustes."
        )
    if "video unavailable" in lowered:
        return (
            "El video no está disponible para esta conexión. Puede estar eliminado, ser privado, "
            "tener restricción regional o requerir Cookies desde una sesión iniciada."
        )
    if any(token in lowered for token in ("sign in", "login required", "private video", "members-only")):
        return "El video requiere iniciar sesión. Configura Cookies en Ajustes y vuelve a analizarlo."
    if "failed to decrypt with dpapi" in lowered:
        return "Windows no pudo leer las Cookies del navegador. Usa un archivo cookies.txt exportado localmente."

    error_lines = [line.strip() for line in raw.splitlines() if line.strip()]
    message = error_lines[-1] if error_lines else "yt-dlp no pudo analizar la URL."
    message = re.sub(r"^ERROR:\s*", "", message, flags=re.IGNORECASE)
    return message[:600]
