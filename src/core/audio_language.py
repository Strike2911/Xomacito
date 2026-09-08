"""Apply an explicit audio language without silently downloading another dub."""
import re
from .ytdlp_runtime import load_ytdlp

LANGUAGES = {"Español": "es", "Inglés": "en"}


def apply_audio_language(options, language):
    result = dict(options)
    code = LANGUAGES.get(language)
    if not code:
        return result
    original = result.get("format") or "bestvideo+bestaudio/best"
    if callable(original):
        return result

    def select(context):
        formats = context.get("formats", [])
        def matching(fmt):
            lang = str(fmt.get("language") or "").lower().replace("_", "-")
            return lang == code or lang.startswith(code + "-")
        available = [f for f in formats if f.get("acodec") != "none" and matching(f)]
        if not available:
            raise load_ytdlp().utils.DownloadError(
                f"No hay una pista de audio identificada como {language}. "
                "Elige Automático o un idioma disponible; esta opción no traduce el video.")
        filtered = [f for f in formats if f.get("acodec") == "none" or matching(f)]
        selector = original
        for fmt in formats:
            if fmt.get("acodec") == "none" or matching(fmt):
                continue
            identifier = str(fmt.get("format_id") or "")
            if not identifier:
                continue
            if fmt.get("vcodec") == "none":
                replacement = "bestaudio"
            else:
                height = fmt.get("height")
                bound = f"[height<={int(height)}]" if height else ""
                replacement = f"bestvideo{bound}+bestaudio/best{bound}"
            selector = re.sub(r"(?<![\w.-])" + re.escape(identifier) + r"(?![\w.-])", replacement, selector)
        with load_ytdlp().YoutubeDL({"quiet": True}) as ydl:
            yield from ydl.build_format_selector(selector)({**context, "formats": filtered})
    result["format"] = select
    return result
