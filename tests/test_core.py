import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
import uuid
from datetime import date, timedelta
from pathlib import Path
from unittest.mock import patch

import customtkinter as ctk

import launcher
import main
from src.core import downloader
from src.core.app_updater import (
    AppUpdateError,
    check_for_app_update,
    download_installer,
    silent_installer_command,
)
from src.core.daily_icon import CAT_COUNT, daily_cat_assets, daily_cat_number
from src.core.restart import RESTART_WAIT_ENV, clean_restart_environment, restart_wait_requested
from src.core.single_instance import SingleInstanceGuard
from src.core.ytdlp_runtime import (
    configure_ytdlp_options,
    is_youtube_access_error,
    youtube_access_fallback_options,
)
from src.gui.visual_shell import _derived_visual, _rgb


ROOT = Path(__file__).resolve().parents[1]
LEGACY_APP_NAME = "Do" + "wP"


class XomacitoWrapperTests(unittest.TestCase):
    @staticmethod
    def _release_payload(tag="v1.6.0", payload_size=512, digest=None):
        if digest is None:
            digest = "sha256:" + ("a" * 64)
        return {
            "tag_name": tag,
            "html_url": f"https://github.com/Strike2911/Xomacito/releases/tag/{tag}",
            "body": "Mejoras de Xomacito",
            "assets": [
                {
                    "name": "setup.exe",
                    "state": "uploaded",
                    "size": payload_size,
                    "digest": digest,
                    "browser_download_url": (
                        f"https://github.com/Strike2911/Xomacito/releases/download/{tag}/setup.exe"
                    ),
                }
            ],
        }

    def test_app_update_only_exists_when_the_remote_version_is_greater(self):
        class FakeResponse:
            def __init__(self, payload):
                self.payload = payload

            def raise_for_status(self):
                return None

            def json(self):
                return self.payload

        class FakeSession:
            def __init__(self, payload):
                self.payload = payload

            def get(self, url, headers, timeout):
                self.assert_api = (url, headers, timeout)
                return FakeResponse(self.payload)

        equal = check_for_app_update(
            "1.6.0", session=FakeSession(self._release_payload("v1.6.0"))
        )
        newer_local = check_for_app_update(
            "1.7.0", session=FakeSession(self._release_payload("v1.6.0"))
        )
        outdated = check_for_app_update(
            "1.5.1", session=FakeSession(self._release_payload("v1.6.0"))
        )

        self.assertFalse(equal["update_available"])
        self.assertFalse(newer_local["update_available"])
        self.assertTrue(outdated["update_available"])
        self.assertEqual(outdated["latest_version"], "1.6.0")
        self.assertTrue(outdated["installer_url"].endswith("/setup.exe"))

    def test_app_installer_download_checks_size_pe_header_and_sha256(self):
        payload = b"MZ" + (b"xomacito" * 64)
        digest = "sha256:" + hashlib.sha256(payload).hexdigest()
        update_info = {
            "latest_version": "1.6.1",
            "installer_url": (
                "https://github.com/Strike2911/Xomacito/"
                "releases/download/v1.6.1/setup.exe"
            ),
            "installer_size": len(payload),
            "installer_digest": digest,
        }

        class FakeDownloadResponse:
            def raise_for_status(self):
                return None

            def iter_content(self, chunk_size):
                self.chunk_size = chunk_size
                yield payload[:17]
                yield payload[17:]

            def close(self):
                self.closed = True

        class FakeDownloadSession:
            def get(self, url, headers, stream, timeout):
                self.request = (url, headers, stream, timeout)
                return FakeDownloadResponse()

        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "setup.exe"
            progress = []
            result = download_installer(
                update_info,
                destination=target,
                progress_callback=lambda done, total: progress.append((done, total)),
                session=FakeDownloadSession(),
            )
            self.assertEqual(result, target)
            self.assertEqual(target.read_bytes(), payload)
            self.assertEqual(progress[-1], (len(payload), len(payload)))

        command = silent_installer_command("C:/Temp/setup.exe")
        self.assertIn("/SILENT", command)
        self.assertIn("/XOMACITOUPDATE=1", command)

    def test_app_installer_rejects_a_wrong_digest(self):
        payload = b"MZinvalid"
        update_info = {
            "latest_version": "1.6.1",
            "installer_url": (
                "https://github.com/Strike2911/Xomacito/"
                "releases/download/v1.6.1/setup.exe"
            ),
            "installer_size": len(payload),
            "installer_digest": "sha256:" + ("0" * 64),
        }

        class FakeResponse:
            def raise_for_status(self):
                return None

            def iter_content(self, chunk_size):
                yield payload

            def close(self):
                return None

        class FakeSession:
            def get(self, url, headers, stream, timeout):
                return FakeResponse()

        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "setup.exe"
            with self.assertRaises(AppUpdateError):
                download_installer(update_info, target, session=FakeSession())
            self.assertFalse(target.exists())

    def test_only_one_xomacito_instance_can_hold_the_lock(self):
        with tempfile.TemporaryDirectory() as directory:
            name = f"Xomacito-test-{uuid.uuid4()}"
            first = SingleInstanceGuard(name, directory)
            second = SingleInstanceGuard(name, directory)

            self.assertTrue(first.acquire())
            self.assertFalse(second.acquire())
            first.release()
            self.assertTrue(second.acquire())
            second.release()

    def test_restart_environment_allows_a_controlled_instance_handoff(self):
        environment = clean_restart_environment({})
        self.assertEqual(environment[RESTART_WAIT_ENV], "1")
        self.assertTrue(restart_wait_requested(environment))
        self.assertFalse(restart_wait_requested({}))

        main_source = (ROOT / "main.py").read_text(encoding="utf-8")
        main_window_source = (ROOT / "src" / "gui" / "main_window.py").read_text(encoding="utf-8")
        config_source = (ROOT / "src" / "gui" / "config_tab.py").read_text(encoding="utf-8")
        self.assertIn("SingleInstanceGuard(APP_NAME)", main_source)
        self.assertIn("focus_existing_window(APP_NAME)", main_source)
        self.assertNotIn("xomacito.lock", main_window_source + config_source)

    def test_instagram_photo_posts_have_an_image_fallback(self):
        class FakeResponse:
            text = (
                '<html><head>'
                '<meta content="Cuenta on Instagram: &quot;Foto bonita&quot;" property="og:title">'
                '<meta property="og:image" content="https://scontent.cdninstagram.com/photo.webp?a=1&amp;b=2">'
                '<meta property="og:description" content="Publicación pública">'
                '</head></html>'
            )

            @staticmethod
            def raise_for_status():
                return None

        class FakeSession:
            @staticmethod
            def get(url, timeout, allow_redirects):
                self.assertEqual(url, "https://www.instagram.com/p/ABC123/")
                self.assertEqual(timeout, 5)
                self.assertTrue(allow_redirects)
                return FakeResponse()

        info = downloader.extract_instagram_image_post_info(
            "https://www.instagram.com/p/ABC123/",
            timeout=5,
            session=FakeSession(),
        )
        self.assertEqual(info["xomacito_media_type"], "image")
        self.assertEqual(info["extractor_key"], "InstagramImage")
        self.assertEqual(info["title"], "Foto bonita")
        self.assertEqual(info["thumbnail"], "https://scontent.cdninstagram.com/photo.webp?a=1&b=2")
        self.assertTrue(downloader.is_instagram_post_url("https://instagram.com/p/ABC123/"))
        self.assertFalse(downloader.is_instagram_post_url("https://evilinstagram.com/p/ABC123/"))

    def test_instagram_metadata_without_video_formats_becomes_an_image(self):
        metadata = {
            "id": "ABC123",
            "title": "Video by cuenta",
            "description": "Foto bonita",
            "thumbnail": "https://instagram.example/photo.jpg",
            "formats": [],
            "http_headers": {"User-Agent": "Xomacito test"},
        }
        info = downloader.instagram_image_post_info_from_metadata(
            "https://www.instagram.com/p/ABC123/?img_index=1",
            metadata,
        )
        self.assertEqual(info["xomacito_media_type"], "image")
        self.assertEqual(info["title"], "Foto bonita")
        self.assertEqual(info["thumbnail"], metadata["thumbnail"])
        self.assertEqual(info["http_headers"]["User-Agent"], "Xomacito test")

    def test_instagram_carousel_respects_the_requested_image_index(self):
        metadata = {
            "_type": "playlist",
            "description": "Carrusel",
            "entries": [
                {"id": "one", "thumbnail": "https://instagram.example/one.jpg", "formats": []},
                {"id": "two", "thumbnail": "https://instagram.example/two.jpg", "formats": []},
            ],
        }
        info = downloader.instagram_image_post_info_from_metadata(
            "https://www.instagram.com/p/ABC123/?img_index=2",
            metadata,
        )
        self.assertEqual(info["id"], "two")
        self.assertEqual(info["thumbnail"], "https://instagram.example/two.jpg")
        self.assertTrue(info["title"].endswith(" - 2"))

    def test_instagram_image_fallback_is_available_from_both_buttons(self):
        source = (ROOT / "src" / "gui" / "single_download_tab.py").read_text(encoding="utf-8")
        self.assertIn("extract_instagram_image_post_info(url, ydl_options=ydl_opts or {})", source)
        self.assertIn('button_text = "Descargar Imagen"', source)
        self.assertIn("def save_thumbnail(self):", source)
        self.assertIn("def _download_image_post_worker", source)

    def test_xomacito_launcher_and_standalone_runtime_are_present(self):
        launcher_exe = ROOT / "Xomacito.exe"
        app_exe = ROOT / "dist" / "Xomacito" / "Xomacito.exe"
        installer = ROOT / "release" / "Xomacito-Setup-1.6.2.exe"
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
        self.assertIn("def lazy_ytdlp", helper)
        for relative in (
            "core/downloader.py",
            "core/batch_processor.py",
            "gui/single_download_tab.py",
        ):
            source = (ROOT / "src" / relative).read_text(encoding="utf-8")
            self.assertIn("lazy_ytdlp", source, relative)

        # Abrir el flujo principal no debe cargar el motor antes de que el
        # usuario analice o descargue una URL.
        result = subprocess.run(
            [
                sys.executable,
                "-c",
                "import sys; import src.gui.single_download_tab; "
                "print('yt_dlp' in sys.modules)",
            ],
            cwd=ROOT,
            capture_output=True,
            text=True,
            timeout=20,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), "False")

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
        self.assertIn('self._register_lazy_tab("Estudio de Imagen", "image_tab"', main_window_py)

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
        self.assertIn('self._register_lazy_tab("Cola", "batch_tab"', source)

    def test_secondary_tabs_and_heavy_engines_are_loaded_on_demand(self):
        source = (ROOT / "src" / "gui" / "main_window.py").read_text(encoding="utf-8")
        imports = source.split("class MainWindow", 1)[0]
        config_source = (ROOT / "src" / "gui" / "config_tab.py").read_text(encoding="utf-8")
        visual_source = (ROOT / "src" / "gui" / "visual_shell.py").read_text(encoding="utf-8")

        self.assertNotIn("from .batch_download_tab import BatchDownloadTab", imports)
        self.assertNotIn("from .image_tools_tab import ImageToolsTab", imports)
        self.assertNotIn("from .config_tab import ConfigTab", imports)
        self.assertIn('self._register_lazy_tab("Estudio de Imagen", "image_tab"', source)
        self.assertIn('self._register_lazy_tab("Configuración", "config_tab"', source)
        self.assertIn('host = ctk.CTkFrame(container, fg_color="transparent")', source)
        self.assertIn('widget = ConfigTab(master=host, app=self)', source)
        self.assertIn('spec["host"].pack(expand=True, fill="both")', source)
        self.assertIn('spec["state"] == "loaded"', source)
        self.assertIn('Solo tardará la primera vez.', source)
        self.assertNotIn('Construyendo {tab_name}', source)
        self.assertIn('deadline = time.monotonic() + 0.008', source)
        self.assertIn('self.after(180000, self._start_memory_cleaner)', source)
        self.assertNotIn("EmptyWorkingSet", source)

        clipboard = source.split("def _check_clipboard_and_paste", 1)[1].split(
            "def on_ffmpeg_check_complete", 1
        )[0]
        self.assertNotIn("time.sleep", clipboard)
        self.assertIn("self.after(", clipboard)

        self.assertIn("self._models_populated = False", config_source)
        self.assertIn("def _populate_model_sections", config_source)
        self.assertIn("width // 4", visual_source)
        self.assertIn("@lru_cache", visual_source)

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
        self.assertIn("XOMACITOUPDATE", installer)
        self.assertIn("skipifnotsilent", installer)
        self.assertIn("IsAutoUpdate", installer)
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
        self.assertIn("release\\setup.exe", build_script)
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
