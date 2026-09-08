import pytest
from src.core.browser_cookies import cookie_options

@pytest.mark.parametrize("mode,expected", [("Brave","brave"),("Chrome","chrome"),("Firefox","firefox")])
def test_visible_source_overrides_stale_browser(mode,expected):
    assert cookie_options({"cookies_mode":mode,"selected_browser":"edge"}) == {"cookiesfrombrowser":(expected,)}

def test_manual_without_file_does_not_read_browser():
    assert cookie_options({"cookies_mode":"Archivo Manual..."}) == {}

def test_profile_and_disabled():
    assert cookie_options({"cookies_mode":"Brave","browser_profile":"Profile 1"}) == {"cookiesfrombrowser":("brave","Profile 1")}
    assert cookie_options({"cookies_mode":"No usar","selected_browser":"brave"}) == {}
