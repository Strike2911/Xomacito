import pytest
from src.core.audio_language import apply_audio_language
from src.core.ytdlp_runtime import friendly_ytdlp_error


def formats():
    return [dict(format_id="v", url="https://example.org/v", ext="mp4", vcodec="avc1", acodec="none", height=720),
            dict(format_id="es", url="https://example.org/es", ext="m4a", vcodec="none", acodec="aac", language="es-419"),
            dict(format_id="en", url="https://example.org/en", ext="m4a", vcodec="none", acodec="aac", language="en")]

@pytest.mark.parametrize("language,expected", [("Español", "es"), ("Inglés", "en")])
@pytest.mark.parametrize("selector", ["v+en", "v+es", "bestvideo+bestaudio/best", "bestaudio", "en"])
def test_language_overrides_default_dub(language, expected, selector):
    choose = apply_audio_language({"format": selector}, language)["format"]
    results = list(choose({"formats": formats(), "has_merged_format": False, "incomplete_formats": False}))
    assert results
    streams = results[0].get("requested_formats", results)
    assert [f["format_id"] for f in streams if f["acodec"] != "none"] == [expected]

def test_missing_language_does_not_download_wrong_audio():
    choose = apply_audio_language({"format": "best"}, "Español")["format"]
    with pytest.raises(Exception, match="No hay una pista"):
        list(choose({"formats": [formats()[-1]]}))

def test_automatic_preserves_selector():
    assert apply_audio_language({"format": "v+en"}, "Automático")["format"] == "v+en"

@pytest.mark.parametrize("message", ["[TikTok] Log in for access", "[Instagram] login required", "[Facebook] private video"])
def test_social_login_errors(message):
    result = friendly_ytdlp_error(message, ["Downloading webpage debug output"])
    assert "Configuración > Cookies" in result
    assert "Downloading" not in result

def test_social_403_not_youtube_specific():
    assert "YouTube" not in friendly_ytdlp_error("[Facebook] HTTP Error 403")
