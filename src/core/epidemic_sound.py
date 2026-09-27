"""Compatibility for Epidemic Sound's UUID music links.

Reuse yt-dlp's public metadata and MP3 extraction, including its preference
for the full mix over stems. No account or premium download endpoints are used.
"""

import re
from urllib.parse import urlparse


def is_epidemic_music_url(url):
    try:
        parsed = urlparse(str(url).strip())
    except ValueError:
        return False
    return (
        parsed.scheme in {"http", "https"}
        and parsed.hostname in {"epidemicsound.com", "www.epidemicsound.com"}
        and re.fullmatch(
            r"/music/tracks/[0-9a-fA-F]{8}(?:-[0-9a-fA-F]{4}){3}-[0-9a-fA-F]{12}/?",
            parsed.path,
        ) is not None
    )


def music_extractor():
    # Import only after YoutubeDL loads the bundled/updatable engine.
    from yt_dlp.extractor.epidemicsound import EpidemicSoundIE

    class XomacitoEpidemicMusicIE(EpidemicSoundIE):
        IE_NAME = "epidemicsound:music"
        # Both the current music and sound-effect links use Kosmos UUIDs.
        # The upstream extractor's sfx group selects that public metadata route.
        _VALID_URL = r"https?://(?:www\.)?epidemicsound\.com/(?P<sfx>music/tracks)/(?P<id>[0-9a-fA-F-]+)"
        _TESTS = []

        def _real_extract(self, url):
            info = super()._real_extract(url)
            info["webpage_url"] = url
            for fmt in info.get("formats", []):
                fmt.update(vcodec="none", acodec="mp3", ext="mp3")
                fmt["xomacito_audio_part"] = fmt.get("format_id") or fmt.get("format")
            return info

    return XomacitoEpidemicMusicIE()
