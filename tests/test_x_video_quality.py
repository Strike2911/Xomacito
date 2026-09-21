from unittest.mock import Mock

from src.core.downloader import extract_x_media_post_info
from src.ui.media_logic import build_media_choices


def extract(variants, direct="https://video.twimg.com/vid/1080x1080/main.mp4"):
    session = Mock()
    session.get.return_value.json.return_value = {"tweet": {"media": {"all": [{
        "type": "video", "width": 1080, "height": 1080, "url": direct,
        "variants": variants,
    }]}}}
    return extract_x_media_post_info("https://x.com/test/status/123/video/1", session=session)


def test_each_x_rendition_has_its_own_dimensions_and_selection():
    variants = [{"url": f"https://video.twimg.com/vid/avc1/{size}x{size}/{size}.mp4",
                 "bitrate": size * 1000, "content_type": "video/mp4"}
                for size in (320, 540, 720, 1080)]
    info = extract(variants)
    choices = build_media_choices(info)["video"]
    by_label = {entry["label"]: entry for entry in choices}
    assert len(by_label) == 4
    assert [item["height"] for item in choices] == [1080, 720, 540, 320]
    assert "/1080x1080/" in by_label[choices[0]["label"]]["raw"]["url"]


def test_unknown_rendition_does_not_inherit_original_resolution():
    result = extract([{"url": "https://video.twimg.com/unknown.mp4", "content_type": "video/mp4"}])
    assert result["formats"][0]["height"] is None
    assert result["formats"][0]["width"] is None


def test_explicit_rendition_dimensions_are_used_when_url_has_none():
    result = extract([{"url": "https://video.twimg.com/unknown.mp4", "width": 640, "height": 360}])
    assert result["formats"][0]["height"] == 360


def test_matching_original_url_can_use_original_dimensions():
    url = "https://video.twimg.com/original.mp4"
    result = extract([{"url": url}], direct=url)
    assert result["formats"][0]["height"] == 1080


def test_duplicate_labels_never_replace_the_best_rendition():
    formats = [dict(format_id=str(rate), url=f"https://example.test/{rate}.mp4",
                    width=1080, height=1080, vcodec="h264", acodec="aac", ext="mp4", tbr=rate)
               for rate in (432, 8768)]
    choices = build_media_choices({"formats": formats})["video"]
    by_label = {entry["label"]: entry for entry in choices}
    assert len(by_label) == 2
    assert by_label[choices[0]["label"]]["tbr"] == 8768
