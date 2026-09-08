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


def test_tiktok_session_is_scoped_to_tiktok_hosts():
    settings={"cookies_mode":"No usar","tiktok_cookies_path":"session.txt"}
    assert cookie_options(settings,"https://www.tiktok.com/@a/video/1")=={"cookiefile":"session.txt"}
    assert cookie_options(settings,"https://www.youtube.com/watch?v=1")=={}
    assert cookie_options(settings,"https://tiktok.com.evil.test/")=={}


def test_import_keeps_only_tiktok_and_source_is_unchanged(tmp_path):
    from src.core.browser_cookies import import_tiktok_cookies
    source=tmp_path/"all.txt"
    contents="# Netscape HTTP Cookie File\n.tiktok.com\tTRUE\t/\tTRUE\t0\tsessionid\tfake\n.example.org\tTRUE\t/\tTRUE\t0\tother\tfake\n"
    source.write_text(contents)
    target=tmp_path/"private"/"tiktok.txt"
    assert import_tiktok_cookies(source,target)==1
    assert "example.org" not in target.read_text()
    assert source.read_text()==contents


def test_empty_export_does_not_replace_saved_session(tmp_path):
    from src.core.browser_cookies import import_tiktok_cookies
    source=tmp_path/"empty.txt";source.write_text("# Netscape HTTP Cookie File\n")
    target=tmp_path/"session.txt";target.write_text("existing")
    with pytest.raises(ValueError,match="no contiene cookies"):
        import_tiktok_cookies(source,target)
    assert target.read_text()=="existing"
