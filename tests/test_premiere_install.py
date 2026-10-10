import json
from pathlib import Path
from subprocess import CompletedProcess, TimeoutExpired
import tempfile
import unittest
from unittest.mock import patch
from zipfile import ZipFile

from src.core.premiere_install import PLUGIN_ID, panel_status, parse_listing


def listing(version=None, enabled=True, host="26.0"):
    return f"1 extension installed for Premiere Pro (ver {host})\n" + (
        f" {'Enabled' if enabled else 'Disabled'} Xomacito Link {version}\n" if version else "")


def result(output="", code=0):
    return CompletedProcess([], code, output, "")


class PremiereInstallTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.package = Path(self.temp.name) / "Xomacito Link.ccx"
        with ZipFile(self.package, "w") as archive:
            archive.writestr("manifest.json", json.dumps({"id": PLUGIN_ID, "version": "1.6.0", "host": {"minVersion": "25.6.0"}}))

    def test_only_current_enabled_premiere_panel_is_verified(self):
        for output in (listing("1.2.0"), listing("1.6.0", False), listing("1.6.0", host="25.5"),
                       "1 extension installed for Photoshop (ver 27.0)\n Enabled Xomacito Link 1.6.0",
                       listing() + "1 extension installed for Others\n Enabled Xomacito Link 1.6.0"):
            self.assertFalse(parse_listing(output, "25.6", "1.6.0")["verified"])
        self.assertTrue(parse_listing(listing("1.6.0"), "25.6", "1.6.0")["verified"])

    @patch("src.core.premiere_install.find_agent", return_value=None)
    def test_missing_creative_cloud(self, _):
        status = panel_status(self.package)
        self.assertFalse(status["canInstall"])
        self.assertIn("Creative Cloud", status["message"])

    @patch("src.core.premiere_install.find_agent", return_value=Path("agent.exe"))
    @patch("src.core.premiere_install.run_agent")
    def test_install_requires_post_install_confirmation(self, run, _):
        run.side_effect = [result(listing("1.2.0")), result(), result(listing("1.6.0"))]
        status = panel_status(self.package, True)
        self.assertTrue(status["verified"])
        self.assertEqual(run.call_args_list[1].args[1:], ("install", str(self.package.resolve())))
        run.side_effect = [result(listing("1.2.0")), result(), result(listing("1.2.0"))]
        self.assertFalse(panel_status(self.package, True)["verified"])

    @patch("src.core.premiere_install.find_agent", return_value=Path("agent.exe"))
    @patch("src.core.premiere_install.run_agent")
    def test_adobe_failure_and_timeout_are_actionable(self, run, _):
        run.side_effect = [result(listing()), result("Adobe error", 42)]
        status = panel_status(self.package, True)
        self.assertFalse(status["verified"])
        self.assertIn("42", status["message"])
        run.side_effect = [result(listing()), TimeoutExpired("agent", 180)]
        self.assertIn("Comprobar estado", panel_status(self.package, True)["message"])

    @patch("src.core.premiere_install.find_agent", return_value=Path("agent.exe"))
    @patch("src.core.premiere_install.run_agent")
    def test_unknown_final_state_does_not_reuse_earlier_verification(self, run, _):
        run.side_effect = [result(listing("1.6.0")), result(), result(code=1)]
        self.assertFalse(panel_status(self.package, True)["verified"])

    @patch("src.core.premiere_install.find_agent", return_value=Path("agent.exe"))
    @patch("src.core.premiere_install.run_agent")
    def test_incompatible_host_never_installs(self, run, _):
        run.return_value = result(listing(host="25.0"))
        self.assertFalse(panel_status(self.package, True)["canInstall"])
        self.assertEqual(run.call_count, 1)
