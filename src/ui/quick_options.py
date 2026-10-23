"""Quick-mode preferences and input rules, shared by the UI and job queue."""
from copy import deepcopy
from urllib.parse import urlsplit


CHOICES = {
    "mode": ["Video", "Audio"],
    "quality": ["Mejor disponible", "2160p", "1440p", "1080p", "720p", "480p", "360p"],
    "audioFormat": ["MP3 128", "MP3 192", "MP3 320", "WAV"],
    "thumbnailMode": ["Sin miniatura", "Guardar miniatura", "Solo miniatura"],
}
DEFAULTS = {
    "mode": "Video", "quality": "1080p", "audioFormat": "MP3 192",
    "outputPath": "", "thumbnail": False, "thumbnailOnly": False,
    "sendPremiere": False, "playlist": False, "postprocess": False,
    "preset": "Web/Móvil - H.264 Normal", "selectedTag": "Sin etiqueta",
}
ACTIVE_STATUSES = {"En cola", "Analizando", "Descargando"}


def preferences(saved, output_path):
    result = {**DEFAULTS, "outputPath": output_path}
    if isinstance(saved, dict):
        result.update({key: value for key, value in saved.items()
                       if key in result and type(value) is type(result[key])
                       and (key not in CHOICES or value in CHOICES[key])})
    if result["thumbnailOnly"]:
        result["thumbnail"] = False
    return result


def thumbnail_mode(state):
    return CHOICES["thumbnailMode"][2 if state["thumbnailOnly"] else int(state["thumbnail"])]


def input_kind(text):
    """Reject malformed link batches instead of silently searching for them."""
    parts = text.split()
    if not parts:
        return "empty"
    try:
        if all(urlsplit(part).scheme.lower() in {"http", "https"}
               and urlsplit(part).hostname for part in parts):
            return "links"
    except ValueError:
        pass
    if any("://" in part or part.lower().startswith(("www.", "file:", "http:", "https:")) for part in parts):
        return "invalid"
    return "search"


def job_options(state, tags):
    """Only execution options enter a job; search/UI state never does."""
    result = {key: state[key] for key in DEFAULTS}
    result["ranges"] = deepcopy(state["ranges"])
    result["outputPath"] = output_path(state, tags)
    return result


def output_path(state, tags):
    return next((tag["folder"] for tag in tags
                 if isinstance(tag, dict) and tag.get("name") == state["selectedTag"]
                 and tag.get("folder")), state["outputPath"])
