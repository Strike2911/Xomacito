from unittest.mock import patch

import pytest
from src.core.downloader import extract_info_resilient, yt_dlp
from src.core.epidemic_sound import is_epidemic_music_url
from src.ui.media_logic import build_media_choices, normalize_info

URL = "https://www.epidemicsound.com/music/tracks/07580420-9735-4f85-8c75-d408918ff2ae/"

@pytest.mark.parametrize("url,valid", [
    (URL, True), (URL + "?utm_source=share", True),
    (URL.replace("www.", ""), True), (URL.rstrip("/"), True),
    (URL.replace(".com/", ".com.evil.test/"), False),
    (URL.replace("/music/tracks/", "/sound-effects/tracks/"), False),
    (URL.replace("/music/tracks/", "/track/"), False),
    (URL + "extra", False), ("file:///music/tracks/123", False),
])
def test_music_link_scope(url, valid):
    assert is_epidemic_music_url(url) is valid


def test_music_uses_kosmos_metadata_and_defaults_to_full_mix():
    # Load the same bundled/updatable yt-dlp as the application before patching.
    yt_dlp.YoutubeDL
    data = {"id": 285132, "publicSlug": "Va48BHTPmS", "title": "Resurgence", "length": 138,
            "stems": {name: {"stemType": name, "lqMp3Url": f"https://cdn.example.test/{name}.mp3"}
                      for name in ("bass", "full", "drums")}}
    with patch("yt_dlp.extractor.epidemicsound.EpidemicSoundIE._download_json", return_value=data) as metadata:
        info = extract_info_resilient(URL, {"quiet": True}, download=False)
    assert metadata.call_args.args[0].endswith("/json/track/kosmos-id/07580420-9735-4f85-8c75-d408918ff2ae")
    assert info["title"] == "Resurgence"
    assert info["format_id"] == "full"
    assert info["webpage_url"] == URL
    choices = build_media_choices(normalize_info(info))
    assert choices["hasAudio"] and not choices["hasVideo"]
    assert choices["audio"][0]["formatId"] == "full"
    assert choices["audio"][0]["label"].startswith("Mezcla completa")
    assert any(item["label"].startswith("Bajo") for item in choices["audio"])


def test_metadata_error_is_not_retried_as_youtube():
    yt_dlp.YoutubeDL
    with patch("yt_dlp.extractor.epidemicsound.EpidemicSoundIE._download_json", side_effect=RuntimeError("HTTP 403")) as metadata:
        with pytest.raises(Exception, match="HTTP 403"):
            extract_info_resilient(URL, {"quiet": True}, download=False)
    assert metadata.call_count == 1
