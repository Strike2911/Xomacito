import importlib.util
from pathlib import Path

import pytest

SPEC = importlib.util.spec_from_file_location("publish_release", Path(__file__).resolve().parents[1] / "scripts/publish_release.py")
publisher = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(publisher)


def release():
    name = "Xomacito-1.4.1-Setup.exe"
    return {"tag_name": "v4.0.41", "assets": [{
        "name": name, "size": 495000000, "state": "uploaded", "digest": "sha256:" + "a" * 64,
        "browser_download_url": f"https://github.com/Strike2911/Xomacito/releases/download/v4.0.41/{name}",
    }]}


def test_full_setup_is_required_even_when_light_update_is_available():
    payload = release()
    payload["assets"][0]["name"] = "Xomacito-1.4.1-Update-Light.exe"
    with pytest.raises(ValueError, match="Update-Light"):
        publisher.validate_release(payload)


def test_valid_full_installer_passes():
    assert publisher.validate_release(release())["name"].endswith("-Setup.exe")


def test_official_draft_asset_can_be_published_but_stable_needs_exact_tag():
    payload = release()
    payload["draft"] = True
    payload["assets"][0]["browser_download_url"] = payload["assets"][0]["browser_download_url"].replace("v4.0.41", "untagged-0123abcdef")
    publisher.validate_release(payload)
    payload["draft"] = False
    with pytest.raises(ValueError):
        publisher.validate_release(payload)
    payload["draft"] = True
    payload["assets"][0]["browser_download_url"] = payload["assets"][0]["browser_download_url"].replace("Strike2911/Xomacito", "someone/other")
    with pytest.raises(ValueError):
        publisher.validate_release(payload)


@pytest.mark.parametrize("field,value", [
    ("state", "starter"), ("size", 0), ("size", 2 * 1024**3 + 1),
    ("digest", None), ("digest", "sha256:bad"),
    ("browser_download_url", "https://example.com/Xomacito-1.4.1-Setup.exe"),
])
def test_incomplete_or_unverifiable_asset_is_rejected(field, value):
    payload = release()
    payload["assets"][0][field] = value
    with pytest.raises(ValueError):
        publisher.validate_release(payload)


def test_public_version_cannot_replace_monotonic_internal_tag():
    payload = release()
    payload["tag_name"] = "v1.4.1"
    with pytest.raises(ValueError, match="tag interno"):
        publisher.validate_release(payload)
