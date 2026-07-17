import json
import subprocess
import sys
import unittest
from datetime import date, timedelta
from pathlib import Path
from unittest.mock import patch

import customtkinter as ctk

import launcher
import main
from src.core import downloader
from src.core.daily_icon import CAT_COUNT, daily_cat_assets, daily_cat_number
from src.core.restart import clean_restart_environment
from src.core.ytdlp_runtime import (
    configure_ytdlp_options,
    is_youtube_access_error,
    youtube_access_fallback_options,
)
from src.gui.visual_shell import _derived_visual, _rgb


ROOT = Path(__file__).resolve().parents[1]
LEGACY_APP_NAME = "Do" + "wP"


class XomacitoWrapperTests(unittest.TestCase):
    def test_xomacito_launcher_and_standalone_runtime_are_present(self):
        launcher_exe = ROOT / "Xomacito.exe"
        app_exe = ROOT / "dist" / "Xomacito" / "Xomacito.exe"
        installer = ROOT / "release" / "Xomacito-Setup-1.5.0.exe"
        self.assertGreater(launcher_exe.stat().st_size, 100_000)
        self.assertGreater(app_exe.stat().st_size, 100_000)
        self.assertGreater(installer.stat().st_size, 100_000)

    def test_packaged_runtime_is_present(self):
        self.assertTrue((ROOT / "dist" / "Xomacito" / "_internal" / "python311.dll").exists())
        self.assertTrue((ROOT / "src" / "gui" / "main_window.py").exists())
        self.assertTrue((ROOT / "bin" / "ffmpeg" / "ffmpeg.exe").exists())

    def test_branding_is_xomacito(self):
        main_window_py = (ROOT / "src" / "gui" / "main_window.py").read_text(encoding="utf-8")
        dialogs_py = (ROOT / "src" / "gui" / "dialogs.py").read_text(encoding="utf-8")
        single_tab_py = (ROOT / "src" / "gui" / "single_download_tab.py").read_text(encoding="utf-8")
        self.assertIn("Xomacito", main_window_py)
        self.assertNotIn(LEGACY_APP_NAME, main_window_py + dialogs_py + single_tab_py)

    def test_legacy_maintenance_panel_is_removed(self):
        single_tab_py = (ROOT / "src" / "gui" / "single_download_tab.py").read_text(encoding="utf-8")
        main_window_py = (ROOT / "src" / "gui" / "main_window.py").read_text(encoding="utf-8")
        self.assertNotIn('text="Mantenimiento"', single_tab_py)
        self.assertNotIn("MarckDP/Xomacito", main_window_py)
        self.assertNotIn("app_status_label =", single_tab_py)

    def test_completion_sound_is_installed(self):
        sound = ROOT / "assets" / "download-complete.mp3"
        self.assertTrue(sound.exists())
        self.assertGreater(sound.stat().st_size, 10_000)
        self.assertEqual(sound.read_bytes()[:3], b"ID3")

    def test_runtime_uses_updatable_ytdlp_zip(self):
        helper = (ROOT / "src" / "core" / "ytdlp_runtime.py").read_text(encoding="utf-8")
        self.assertIn("yt-dlp.zip", helper)
        self.assertIn("configure_ytdlp_options", helper)
        for relative in (
            "core/downloader.py",
            "core/batch_processor.py",
            "gui/main_window.py",
            "gui/single_download_tab.py",
            "gui/batch_download_tab.py",
            "gui/image_tools_tab.py",
        ):
            source = (ROOT / "src" / relative).read_text(encoding="utf-8")
            self.assertIn("load_ytdlp", source, relative)

    def test_youtube_403_uses_an_isolated_embedded_client_retry(self):
        original = {
            "user_agent": "old-agent",
            "referer": "https://www.youtube.com/watch?v=test",
            "extractor_args": {"youtube": {"skip": ["translated_subs"]}},
        }
        configured = configure_ytdlp_options(original)
        fallback = youtube_access_fallback_options(configured)

        self.assertEqual(fallback["extractor_args"]["youtube"]["player_client"], ["web_embedded"])
        self.assertEqual(fallback["extractor_args"]["youtube"]["skip"], [])
        self.assertNotIn("user_agent", fallback)
        self.assertNotIn("referer", fallback)
        self.assertEqual(fallback["remote_components"], ["ejs:github"])
        self.assertNotIn("player_client", original["extractor_args"]["youtube"])
        self.assertTrue(
            is_youtube_access_error(
                "https://youtu.be/test",
                "ERROR: unable to download video data: HTTP Error 403: Forbidden",
            )
        )
        self.assertFalse(is_youtube_access_error("https://example.com/video", "HTTP Error 403"))

        attempts = []

        class FakeYoutubeDL:
            def __init__(self, options):
                self.options = options

            def __enter__(self):
                return self

            def __exit__(self, *_args):
                return False

            def extract_info(self, _url, download=False):
                attempts.append((self.options, download))
                if len(attempts) == 1:
                    raise RuntimeError("HTTP Error 403: Forbidden")
                return {"id": "test", "filepath": "video.mp4"}

        with patch.object(downloader.yt_dlp, "YoutubeDL", FakeYoutubeDL):
            result = downloader.extract_info_resilient(
                "https://www.youtube.com/watch?v=test",
                {"format": "best"},
                download=True,
            )

        self.assertEqual(result["filepath"], "video.mp4")
        self.assertEqual(len(attempts), 2)
        self.assertEqual(
            attempts[1][0]["extractor_args"]["youtube"]["player_client"],
            ["web_embedded"],
        )

    def test_professional_shell_is_present(self):
        main_window_py = (ROOT / "src" / "gui" / "main_window.py").read_text(encoding="utf-8")
        visual_shell_py = (ROOT / "src" / "gui" / "visual_shell.py").read_text(encoding="utf-8")
        self.assertIn('"XOMACITO"', visual_shell_py)
        self.assertIn("GATITO DEL DÍA", visual_shell_py)
        self.assertIn('self.tab_view.add("Descargar")', main_window_py)
        self.assertIn('self.tab_view.add("Estudio de Imagen")', main_window_py)

    def test_launcher_self_test_finds_exe(self):
        result = subprocess.run(
            [sys.executable, str(ROOT / "launcher.py"), "--self-test"],
            cwd=str(ROOT),
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr or result.stdout)

    def test_launcher_name(self):
        self.assertEqual(launcher.APP_NAME, "Xomacito")
        self.assertEqual(launcher.STANDALONE_EXE_NAME, "dist\\Xomacito\\Xomacito.exe")
        launcher_source = (ROOT / "launcher.py").read_text(encoding="utf-8")
        self.assertNotIn("engine\\\\Xomacito.exe", launcher_source)
        self.assertNotIn("XomacitoTitleFixer", launcher_source)

    def test_public_brand_links_belong_to_strike(self):
        source = (ROOT / "src" / "gui" / "config_tab.py").read_text(encoding="utf-8")
        self.assertIn("Creado por Strike |", source)
        self.assertIn("https://www.youtube.com/@ElStrikew", source)
        self.assertIn("https://ko-fi.com/strikepoint", source)
        self.assertNotIn("MarckDBM", source)

    def test_brand_icon_is_canonical_and_legacy_artifacts_are_absent(self):
        self.assertEqual(
            (ROOT / "Xomacito-icon.ico").read_bytes(),
            (ROOT / "assets" / "cat-icons" / "cat-01.ico").read_bytes(),
        )
        obsolete_paths = (
            "DowP-icon.ico", "XomacitoCore.exe", "XomacitoTitleFixer.exe",
            "XomacitoTitleFixer.spec", "title_fixer.py", "app.py",
            "runtime_bootstrap.py", "_extracted_main.pyc", "_main_extracted.pyc",
            "_internal", "engine", "build",
        )
        for relative in obsolete_paths:
            self.assertFalse((ROOT / relative).exists(), relative)

        build_entries = {path.name for path in (ROOT / ".build").iterdir()}
        self.assertEqual(build_entries, {"XomacitoInstaller.spec", "XomacitoLauncher.spec"})

        for source_path in (ROOT / "src").rglob("*.py"):
            source = source_path.read_text(encoding="utf-8")
            runtime_source = source.replace(".dowp_preset", "")
            self.assertNotIn("dowp_", runtime_source, source_path)
            self.assertNotIn("dowp.lock", source, source_path)

    def test_eight_daily_cat_icons_are_installed(self):
        cat_dir = ROOT / "assets" / "cat-icons"
        self.assertEqual(CAT_COUNT, 8)
        self.assertEqual(len(list(cat_dir.glob("cat-*.png"))), 8)
        self.assertEqual(len(list(cat_dir.glob("cat-*.ico"))), 8)
        for number in range(1, 9):
            self.assertGreater((cat_dir / f"cat-{number:02d}.png").stat().st_size, 10_000)
            self.assertGreater((cat_dir / f"cat-{number:02d}.ico").stat().st_size, 10_000)

    def test_daily_cat_changes_once_per_day_and_cycles(self):
        start = date(2026, 1, 1)
        sequence = [daily_cat_number(start + timedelta(days=offset)) for offset in range(9)]
        self.assertEqual(len(set(sequence[:8])), 8)
        self.assertEqual(sequence[0], sequence[8])
        selected = daily_cat_assets(ROOT, start)
        self.assertTrue(selected.png_path.exists())
        self.assertTrue(selected.ico_path.exists())

    def test_gradient_shell_is_integrated_without_replacing_tabs(self):
        source = (ROOT / "src" / "gui" / "main_window.py").read_text(encoding="utf-8")
        self.assertIn("GradientBackdrop(self, self.theme_data)", source)
        self.assertIn("DailyBrandHeader(self, self.daily_cat", source)
        self.assertIn("gradient_backdrop.update_theme", source)
        self.assertIn("brand_header.update_theme", source)
        self.assertIn("segmented_button_selected_color", source)
        self.assertIn('self.tab_view.add("Descargar")', source)
        self.assertIn('self.tab_view.add("Cola")', source)

    def test_builtin_blue_theme_drives_shell_and_custom_widgets(self):
        ctk.set_appearance_mode("Dark")
        blue = main._builtin_theme_data(ctk, "blue")
        deep_blue = main._builtin_theme_data(ctk, "dark-blue")

        self.assertEqual(blue["ThemeName"], "Azul (Estándar)")
        self.assertIn("CustomColors", blue)
        self.assertIn("XomacitoVisual", blue)
        self.assertEqual(blue["CustomColors"]["DOWNLOAD_BTN"], blue["CTkButton"]["fg_color"])
        self.assertNotEqual(
            blue["XomacitoVisual"]["background_top"],
            deep_blue["XomacitoVisual"]["background_top"],
        )

        derived = _derived_visual(blue, dark_mode=True)
        for color in derived.values():
            if isinstance(color, str) and color.startswith("#"):
                self.assertEqual(len(_rgb(color)), 3)
        self.assertEqual(_rgb("gray10"), (26, 26, 26))

    def test_scrollable_panels_use_solid_theme_surfaces(self):
        config_source = (ROOT / "src" / "gui" / "config_tab.py").read_text(encoding="utf-8")
        single_source = (ROOT / "src" / "gui" / "single_download_tab.py").read_text(encoding="utf-8")

        self.assertGreaterEqual(config_source.count("fg_color=self.SCROLL_SURFACE"), 4)
        self.assertNotIn('frame_deps._scrollbar.bind("<B1-Motion>"', config_source)
        self.assertNotIn('frame_models.bind("<MouseWheel>"', config_source)
        self.assertIn('self.options_scroll_frame = ctk.CTkScrollableFrame(', single_source)
        self.assertIn('scrollable.configure(fg_color=scroll_surface)', single_source)

    def test_refined_themes_have_dynamic_visual_tokens_and_accessible_contrast(self):
        def luminance(color):
            channels = []
            for index in (1, 3, 5):
                value = int(color[index:index + 2], 16) / 255
                channels.append(value / 12.92 if value <= 0.04045 else ((value + 0.055) / 1.055) ** 2.4)
            return 0.2126 * channels[0] + 0.7152 * channels[1] + 0.0722 * channels[2]

        def ratio(first, second):
            light, dark = sorted((luminance(first), luminance(second)), reverse=True)
            return (light + 0.05) / (dark + 0.05)

        allowed_fonts = {"Segoe UI Variable Text", "Candara", "Bahnschrift"}
        themes = sorted((ROOT / "src" / "gui" / "themes").glob("*.json"))
        self.assertEqual(len(themes), 10)
        for path in themes:
            data = json.loads(path.read_text(encoding="utf-8-sig"))
            self.assertEqual(data["_INSTRUCCIONES_XOMACITO"]["VERSION"], "5.2", path.name)
            self.assertIn(data["CTkFont"]["Windows"]["family"], allowed_fonts, path.name)
            self.assertEqual(data["CTkFont"]["Windows"]["size"], 14, path.name)
            self.assertTrue({
                "background_top", "background_bottom", "glow_primary", "glow_secondary",
                "header_top", "header_bottom", "header_border", "font_family",
            }.issubset(data["XomacitoVisual"]), path.name)
            for mode in (0, 1):
                pairs = (
                    (data["CTkLabel"]["text_color"][mode], data["CTkFrame"]["fg_color"][mode]),
                    (data["CTkButton"]["text_color"][mode], data["CTkButton"]["fg_color"][mode]),
                    (data["CTkEntry"]["text_color"][mode], data["CTkEntry"]["fg_color"][mode]),
                    (data["DropdownMenu"]["text_color"][mode], data["DropdownMenu"]["fg_color"][mode]),
                    (data["CustomColors"]["SECTION_SUBTITLE"][mode], data["CustomColors"]["CONFIG_CARD_BG"][mode]),
                )
                for foreground, background in pairs:
                    self.assertGreaterEqual(ratio(foreground, background), 4.5, f"{path.name}: {foreground}/{background}")

    def test_frozen_restart_uses_an_independent_pyinstaller_environment(self):
        environment = clean_restart_environment({"EXAMPLE": "kept"})
        self.assertEqual(environment["EXAMPLE"], "kept")
        self.assertEqual(environment["PYINSTALLER_RESET_ENVIRONMENT"], "1")
        config_source = (ROOT / "src" / "gui" / "config_tab.py").read_text(encoding="utf-8")
        window_source = (ROOT / "src" / "gui" / "main_window.py").read_text(encoding="utf-8")
        theme_handler = config_source.split("def _on_theme_change", 1)[1].split("def _on_appearance_mode_change", 1)[0]
        self.assertIn("restart_application()", theme_handler)
        self.assertNotIn("on_closing()", theme_handler)
        self.assertIn("clean_restart_environment()", window_source)

    def test_explicit_builtin_theme_survives_restart(self):
        self.assertEqual(main._theme_path({"selected_theme_accent": "dark-blue"}).name, "midnight_ocean.json")
        self.assertEqual(
            main._theme_path({"selected_theme_accent": "dark-blue", "theme_selection_explicit": True}),
            "dark-blue",
        )

    def test_installer_uses_direct_one_folder_runtime(self):
        spec = (ROOT / ".build" / "XomacitoInstaller.spec").read_text(encoding="utf-8")
        installer = (ROOT / "installer" / "Xomacito.iss").read_text(encoding="utf-8")

        self.assertIn("exclude_binaries=True", spec)
        self.assertIn("COLLECT(", spec)
        self.assertIn('name="Xomacito"', spec)
        for tool_name in ("deno", "ffmpeg", "ghostscript", "poppler", "ytdlp"):
            self.assertIn(f'"{tool_name}"', spec)
            self.assertIn('f"bin/{tool_name}"', spec)
        for dll_name in (
            "cairo-2.dll", "z-1.dll", "png16.dll", "fontconfig-1.dll",
            "freetype-6.dll", "pixman-1-0.dll", "libexpat.dll",
            "intl-8.dll", "bz2.dll",
        ):
            self.assertIn(dll_name, spec)
        self.assertNotIn("launcher.py", spec)
        self.assertNotIn("title_fixer.py", spec)

        self.assertIn("PrivilegesRequired=lowest", installer)
        self.assertIn("CloseApplications=force", installer)
        self.assertIn("CloseApplicationsFilter=*.*", installer)
        self.assertIn("[UninstallRun]", installer)
        self.assertIn('{sys}\\taskkill.exe', installer)
        self.assertIn('/F /IM ""{#MyAppExeName}""', installer)
        self.assertIn("Uninstallable=yes", installer)
        self.assertIn("Desinstalar Xomacito", installer)
        self.assertIn("{uninstallexe}", installer)
        self.assertIn("UninstallDisplayName={#MyAppName} {#MyAppVersion}", installer)
        self.assertIn('Name: "{userappdata}\\Xomacito\\encoder_cache.json"', installer)
        self.assertIn('Name: "{app}\\_internal\\bin\\models"', installer)
        self.assertIn("procedure CurUninstallStepChanged", installer)
        self.assertIn("DelTree(UserDataDir", installer)
        self.assertIn("UninstallSilent", installer)
        self.assertNotIn('Source: "{#ProjectRoot}\\bin\\ffmpeg', installer)
        self.assertNotIn("bin\\models\\*", installer)
        self.assertNotIn("engine\\", installer)

    def test_startup_uses_bundled_ffmpeg_without_auto_installing(self):
        source = (ROOT / "src" / "gui" / "main_window.py").read_text(encoding="utf-8")
        dialogs = (ROOT / "src" / "gui" / "dialogs.py").read_text(encoding="utf-8")
        startup = source.split("def run_initial_setup(self):", 1)[1].split(
            "def on_update_check_complete", 1
        )[0]
        self.assertNotIn("DependencySetupWindow", startup)
        self.assertNotIn("download_and_install_ffmpeg", startup)
        self.assertIn("no descargará dependencias al iniciar", startup)
        self.assertNotIn("Iniciando descarga automática", source)
        self.assertNotIn("self.after(500, self.start_installation)", dialogs)

        main_source = (ROOT / "main.py").read_text(encoding="utf-8")
        runtime_source = (ROOT / "src" / "core" / "ytdlp_runtime.py").read_text(encoding="utf-8")
        self.assertIn('BIN_PATH = INTERNAL_DIR / "bin"', main_source)
        self.assertIn('executable_root / "_internal"', runtime_source)

        ffmpeg = ROOT / "dist" / "Xomacito" / "_internal" / "bin" / "ffmpeg" / "ffmpeg.exe"
        ffprobe = ROOT / "dist" / "Xomacito" / "_internal" / "bin" / "ffmpeg" / "ffprobe.exe"
        self.assertGreater(ffmpeg.stat().st_size, 100_000_000)
        self.assertGreater(ffprobe.stat().st_size, 100_000_000)
        result = subprocess.run(
            [str(ffmpeg), "-version"],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
        self.assertEqual(result.returncode, 0)
        self.assertIn("ffmpeg version", result.stdout.lower())

    def test_xomacito_is_standalone_without_editor_plugin_bridge(self):
        source_paths = (
            ROOT / "src" / "gui" / "main_window.py",
            ROOT / "src" / "gui" / "config_tab.py",
            ROOT / "src" / "gui" / "single_download_tab.py",
            ROOT / "src" / "gui" / "batch_download_tab.py",
            ROOT / "src" / "gui" / "image_tools_tab.py",
            ROOT / "src" / "core" / "batch_processor.py",
        )
        combined_source = "\n".join(path.read_text(encoding="utf-8") for path in source_paths)
        forbidden_bridges = (
            "flask_socketio",
            "SocketIO",
            "IntegrationManager",
            "ACTIVE_TARGET_SID",
            "port=7788",
            "_check_whats_new",
            "DaVinci Resolve",
            "Adobe (Premiere",
        )
        for bridge in forbidden_bridges:
            self.assertNotIn(bridge, combined_source)

        self.assertFalse((ROOT / "src" / "core" / "integration_manager.py").exists())
        self.assertFalse((ROOT / "src" / "core" / "davinci_api.py").exists())
        self.assertFalse((ROOT / "src" / "gui" / "whats_new_dialog.py").exists())

        installer_spec = (ROOT / ".build" / "XomacitoInstaller.spec").read_text(encoding="utf-8")
        self.assertNotIn("engineio.async_drivers", installer_spec)
        for package in ("flask_socketio", "socketio", "engineio", "gevent"):
            self.assertIn(package, installer_spec.split("excludes=", 1)[1])

        # Importar un archivo desde el equipo es una función local de la app y se conserva.
        single_source = (ROOT / "src" / "gui" / "single_download_tab.py").read_text(encoding="utf-8")
        self.assertIn("Importar Archivo Local para Recodificar", single_source)

    def test_self_test_does_not_open_the_tk_interface(self):
        source = (ROOT / "main.py").read_text(encoding="utf-8")
        main_body = source.split("def main() -> int:", 1)[1].split("def _run_safely", 1)[0]
        self.assertLess(main_body.index('"--self-test"'), main_body.index("import customtkinter"))
        self.assertIn('INTERNAL_DIR / "_tcl_data" / "init.tcl"', source)
        self.assertIn('INTERNAL_DIR / "_tk_data" / "tk.tcl"', source)

    def test_release_build_and_benchmark_scripts_are_present(self):
        build_script = (ROOT / "scripts" / "build_release.ps1").read_text(encoding="utf-8-sig")
        benchmark_script = (ROOT / "scripts" / "benchmark_startup.ps1").read_text(encoding="utf-8-sig")
        cleanup_script = (ROOT / "scripts" / "clean_project.ps1").read_text(encoding="utf-8-sig")
        uninstall_launcher = ROOT / "installer" / "Desinstalar Xomacito.cmd"

        self.assertIn("XomacitoInstaller.spec", build_script)
        self.assertIn("Xomacito.iss", build_script)
        self.assertIn("AverageStartupSeconds", benchmark_script)
        self.assertIn("MainWindowHandle", benchmark_script)
        self.assertIn("ExpectedWindowTitle", benchmark_script)
        self.assertIn("Assert-ProjectChild", cleanup_script)
        self.assertIn(".tools\\python311full", cleanup_script)
        cleanup_targets = cleanup_script.split("$Targets = @(", 1)[1].split(") |", 1)[0]
        self.assertNotIn("'.tools\\python311full'", cleanup_targets)
        self.assertIn("unins000.exe", uninstall_launcher.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
