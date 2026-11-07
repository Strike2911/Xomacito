from pathlib import Path
import pytest
from scripts.windows_version_info import make_version_info, read_versions


def test_versions_are_read_without_executing_main(tmp_path):
    (tmp_path / 'main.py').write_text(
        'raise RuntimeError("must not execute")\nAPP_VERSION="1.4.6"\nUPDATE_VERSION="4.0.46"',
        encoding='utf-8',
    )
    assert read_versions(tmp_path) == ('1.4.6', '4.0.46')
    info = make_version_info(tmp_path)
    assert info.ffi.fileVersionMS == (4 << 16)
    assert info.ffi.fileVersionLS == (46 << 16)
    text = str(info)
    assert "'ProductName', 'Xomacito'" in text
    assert "'ProductVersion', '1.4.6'" in text


@pytest.mark.parametrize('version', ['1.4', '1.4.6-beta', '1.4.65536', '1.4.6.0.1'])
def test_invalid_versions_fail_before_packaging(tmp_path, version):
    (tmp_path / 'main.py').write_text(
        f'APP_VERSION={version!r}\nUPDATE_VERSION="4.0.46"', encoding='utf-8',
    )
    with pytest.raises(ValueError):
        read_versions(tmp_path)
