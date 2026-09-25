"""Platform dispatch checks runnable without a native macOS GUI."""

import hashlib
import ast
import subprocess
import sys
from types import SimpleNamespace
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

import main
from src.core import app_updater, macos_runtime, notification_sound, setup


def test_existing_windows_code_is_preserved():
    """Compare executable ASTs after selecting the Windows platform branches."""
    root = Path(__file__).resolve().parents[1]

    class WindowsBranches(ast.NodeTransformer):
        def visit_If(self, node):
            node = self.generic_visit(node)
            if "sys.platform" not in ast.unparse(node.test):
                return node
            try:
                selected = eval(compile(ast.Expression(node.test), "<platform>", "eval"),
                                {"__builtins__": {}, "sys": SimpleNamespace(platform="win32")})
            except (NameError, AttributeError):
                return node
            return node.body if selected else node.orelse

        def visit_Import(self, node):
            node.names = [alias for alias in node.names if alias.name not in {"sys", "subprocess"}]
            return node if node.names else None

    paths = subprocess.check_output(["git", "diff", "--name-only", "--", "main.py", "src"], cwd=root, text=True).splitlines()
    if not paths:
        pytest.skip("This acceptance audit compares uncommitted platform changes with HEAD.")
    for path in paths:
        original = subprocess.check_output(["git", "show", f"HEAD:{path}"], cwd=root).decode("utf-8-sig")
        current = (root / path).read_text(encoding="utf-8-sig")
        before = ast.dump(WindowsBranches().visit(ast.parse(original)))
        after = ast.dump(WindowsBranches().visit(ast.parse(current)))
        assert before == after, f"Windows executable code changed: {path}"


def test_mac_models_are_outside_application_bundle(monkeypatch, tmp_path):
    monkeypatch.delenv("XOMACITO_MODELS_DIR", raising=False)
    monkeypatch.setattr(macos_runtime, "support_path", lambda: tmp_path)
    with patch.object(sys, "platform", "darwin"):
        assert main._persistent_models_path() == tmp_path / "models"


@pytest.mark.parametrize("system,architecture,ort,rawpy", [
    ("Windows", "AMD64", "onnxruntime-directml", "==0.27.0"),
    ("Darwin", "arm64", "onnxruntime", "==0.27.0"),
    ("Darwin", "x86_64", "onnxruntime", "==0.25.1"),
])
def test_requirements_select_one_native_runtime(system, architecture, ort, rawpy):
    from packaging.requirements import Requirement

    environment = {"platform_system": system, "sys_platform": "win32" if system == "Windows" else "darwin",
                   "platform_machine": architecture}
    requirements = [Requirement(line) for line in (Path(__file__).resolve().parents[1] / "requirements.txt").read_text().splitlines()
                    if line.strip() and not line.startswith("#")]
    selected = {item.name: str(item.specifier) for item in requirements
                if item.marker is None or item.marker.evaluate(environment)}
    assert [name for name in selected if name.startswith("onnxruntime")] == [ort]
    assert selected["rawpy"] == rawpy
    if system == "Windows":
        assert selected[ort] == "==1.24.4"
        assert "pyinstaller" not in selected
    elif architecture == "x86_64":
        assert selected[ort] == "==1.23.2"


def test_mac_tools_never_request_windows_archives():
    with patch.object(sys, "platform", "darwin"), patch.object(setup.requests, "get") as get:
        for function in (setup.get_latest_ffmpeg_info, setup.get_safe_ffmpeg_info,
                         setup.get_latest_deno_info, setup.get_latest_poppler_info,
                         setup.get_latest_inkscape_info):
            assert function(lambda *args: None) == (None, None)
        get.assert_not_called()


def test_mac_update_selects_matching_architecture():
    assets = [{"name": name} for name in (
        "Xomacito-Setup.exe", "Xomacito-1.2.8-x86_64.dmg", "Xomacito-1.2.8-arm64.dmg")]
    with patch.object(sys, "platform", "darwin"), patch("platform.machine", return_value="arm64"):
        assert app_updater._select_installer_asset(assets) == assets[2]
        assert app_updater._select_installer_asset(assets[:2]) is None


@pytest.mark.parametrize("valid_digest,valid_format", [(True, True), (False, True), (True, False)])
def test_mac_update_validates_dmg_and_digest(tmp_path, valid_digest, valid_format):
    payload = (b"koly" if valid_format else b"MZxx") + bytes(508)
    response = Mock()
    response.iter_content.return_value = [payload]
    client = Mock()
    client.get.return_value = response
    info = {
        "installer_url": "https://github.com/Strike2911/Xomacito/releases/download/v4.0.27/Xomacito-1.2.8-arm64.dmg",
        "installer_size": len(payload),
        "installer_digest": "sha256:" + (hashlib.sha256(payload).hexdigest() if valid_digest else "0" * 64),
    }
    destination = tmp_path / "update.dmg"
    with patch.object(sys, "platform", "darwin"):
        if valid_digest and valid_format:
            assert app_updater.download_installer(info, destination, session=client) == destination
            assert destination.read_bytes() == payload
        else:
            with pytest.raises(app_updater.AppUpdateError):
                app_updater.download_installer(info, destination, session=client)
            assert not destination.exists()
            assert not destination.with_suffix(".dmg.part").exists()
    response.close.assert_called_once()


def test_mac_update_opens_dmg_without_powershell(tmp_path):
    with patch.object(sys, "platform", "darwin"):
        command = app_updater.deferred_installer_command(tmp_path / "update.dmg", 123)
    assert command == ["/usr/bin/open", str((tmp_path / "update.dmg").resolve())]
    assert list(tmp_path.iterdir()) == []


def test_mac_audio_uses_afplay():
    with patch.object(sys, "platform", "darwin"), patch.object(notification_sound.subprocess, "run") as run:
        notification_sound._play_with_mci(Path("sound.mp3"), 316)
    assert run.call_args.args[0] == ["/usr/bin/afplay", "-v", "0.316", "sound.mp3"]


def test_mac_upscaler_archive_and_permissions(tmp_path, monkeypatch):
    import zipfile

    monkeypatch.setattr(setup, "UPSCALING_DIR", str(tmp_path))
    monkeypatch.setattr(setup, "migrate_old_upscaling_models", lambda: None)
    monkeypatch.setattr(setup, "ensure_curated_upscayl_models", lambda callback: True)
    urls = []

    def download(url, target, *args):
        urls.append(url)
        with zipfile.ZipFile(target, "w") as archive:
            archive.writestr("upscayl-bin", b"native-test-binary")

    monkeypatch.setattr(setup, "download_upscaler_archive", download)
    with patch.object(sys, "platform", "darwin"), patch.object(setup.os, "chmod") as chmod:
        assert setup.check_and_download_upscaling_tools(lambda *args: None, "Upscayl")
        assert chmod.call_args.args[0] == str(tmp_path / "upscayl/upscayl-bin")
        assert chmod.call_args.args[1] & 0o111 == 0o111
    assert urls[0].endswith("-macos.zip")
    assert (tmp_path / "upscayl/upscayl-bin").is_file()
