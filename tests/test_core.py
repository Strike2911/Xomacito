import hashlib
import io
import json
import os
import array
import subprocess
import sys
import tempfile
import threading
import unittest
import uuid
import wave
from datetime import date, timedelta
from pathlib import Path
from unittest.mock import patch

import launcher
import main
from src.core import downloader
from src.core.app_updater import (
    AppUpdateError,
    build_update_prompt,
    check_for_app_update,
    deferred_installer_command,
    download_installer,
    release_notice_for_version,
    silent_installer_command,
)
from src.core.daily_icon import CAT_COUNT, daily_cat_assets, daily_cat_number
from src.core.notification_sound import (
    GACHA_EQUIP_SOUND_FILENAMES,
    GACHA_SOUND_FILENAMES,
    GACHA_STYLE_SOUND_FILENAMES,
    completion_sound_path,
    gacha_equip_sound_path,
    gacha_sound_path,
    platinum_sound_path,
    play_completion_sound,
)
from src.core.processor import (
    CODEC_PROFILES,
    ENCODER_CACHE_SCHEMA_VERSION,
    FFmpegProcessor,
    encoder_cache_is_valid,
    normalize_recode_parameters,
    pixel_format_has_alpha,
    recode_parameters_preserve_alpha,
    validate_recode_result_info,
)
from src.core.restart import RESTART_WAIT_ENV, clean_restart_environment, restart_wait_requested
from src.core.single_instance import SingleInstanceGuard
from src.core.ytdlp_runtime import (
    configure_ytdlp_options,
    is_youtube_access_error,
    safe_console_print,
    youtube_access_fallback_options,
)
ROOT = Path(__file__).resolve().parents[1]
LEGACY_APP_NAME = "Do" + "wP"


class XomacitoWrapperTests(unittest.TestCase):
    def test_explicit_ui_scale_is_applied_before_qt_starts(self):
        with patch.dict(os.environ, {"XOMACITO_UI_SCALE": "1.5"}, clear=False):
            os.environ.pop("QT_SCALE_FACTOR", None)
            main._configure_responsive_qt_scale()
            self.assertEqual(os.environ.get("QT_SCALE_FACTOR"), "1.5")
            os.environ.pop("QT_SCALE_FACTOR", None)

    def test_automatic_ui_scale_is_conservative_and_resolution_aware(self):
        self.assertEqual(main._recommended_ui_scale(1920, 1080, 96), 1.0)
        self.assertEqual(main._recommended_ui_scale(2560, 1440, 96), 1.25)
        self.assertEqual(main._recommended_ui_scale(3840, 2160, 96), 1.5)
        self.assertEqual(main._recommended_ui_scale(2560, 1440, 120), 1.0)

    @staticmethod
    def _release_payload(tag="v1.6.0", payload_size=512, digest=None):
        if digest is None:
            digest = "sha256:" + ("a" * 64)
        release_version = tag.removeprefix("v")
        return {
            "tag_name": tag,
            "html_url": f"https://github.com/Strike2911/Xomacito/releases/tag/{tag}",
            "body": "Mejoras de Xomacito",
            "assets": [
                {
                    "name": f"Xomacito-{release_version}-Setup.exe",
                    "state": "uploaded",
                    "size": payload_size,
                    "digest": digest,
                    "browser_download_url": (
                        f"https://github.com/Strike2911/Xomacito/releases/download/"
                        f"{tag}/Xomacito-{release_version}-Setup.exe"
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
        version_20 = check_for_app_update(
            "2.0", session=FakeSession(self._release_payload("v2.1"))
        )

        self.assertFalse(equal["update_available"])
        self.assertFalse(newer_local["update_available"])
        self.assertTrue(outdated["update_available"])
        self.assertEqual(outdated["latest_version"], "1.6.0")
        self.assertTrue(outdated["installer_url"].endswith("/Xomacito-1.6.0-Setup.exe"))
        self.assertTrue(version_20["update_available"])
        self.assertEqual(version_20["latest_version"], "2.1")
        self.assertTrue(version_20["installer_url"].endswith("/Xomacito-2.1-Setup.exe"))

    def test_update_prompt_displays_the_release_message(self):
        prompt = build_update_prompt(
            {
                "latest_version": "1.6.4",
                "release_notes": (
                    "Playera encontró un fallo en la recodificación.\n"
                    "ᗧ • • •  VIVA LA GRASA!!! :V"
                ),
            },
            "1.6.3",
        )
        self.assertIn("Playera encontró", prompt)
        self.assertIn("VIVA LA GRASA!!! :V", prompt)
        self.assertIn("¿Quieres descargarla e instalarla ahora?", prompt)

    def test_release_164_has_a_one_time_alpha_notice(self):
        notice = release_notice_for_version("v1.6.4")

        self.assertIsNotNone(notice)
        self.assertIn("Playera encontró", notice["message"])
        self.assertIn("ProRes 422 Proxy no admite canal alfa", notice["message"])
        self.assertIn("ProRes 4444 Liviano", notice["message"])
        self.assertIn("VIVA LA GRASA!!! :V", notice["message"])
        self.assertIsNone(release_notice_for_version("1.6.3"))

    def test_release_21_has_the_xomacito_notice_and_idea_contributors(self):
        notice = release_notice_for_version("v2.1")

        self.assertIsNotNone(notice)
        self.assertEqual(notice["title"], "Xomacito 2.1")
        self.assertEqual(notice["subtitle"], "LA XOMACITO KILLER UPDATE!!")
        self.assertEqual(notice["contributors"], ["Jorge", "Xomas", "Megas", "Playera"])
        self.assertIn(
            "¡Nuevo sistema de GACHA! Desbloquea gatos y personaliza tu avatar.",
            notice["highlights"],
        )
        self.assertGreaterEqual(len(notice["highlights"]), 5)

    def test_release_22_notice_mentions_audio_and_installer(self):
        notice = release_notice_for_version("v2.2")

        self.assertIsNotNone(notice)
        highlights = " ".join(notice["highlights"]).casefold()
        self.assertIn("maullido", highlights)
        self.assertIn("actualiz", highlights)
        self.assertEqual(notice["title"], "Xomacito 2.2")

    def test_release_23_notice_mentions_recode_results_and_mensva(self):
        notice = release_notice_for_version("v2.3")

        self.assertIsNotNone(notice)
        highlights = " ".join(notice["highlights"]).casefold()
        self.assertEqual(notice["title"], "Xomacito 2.3")
        self.assertIn("recodific", highlights)
        self.assertIn("resultado", highlights)
        self.assertEqual(
            notice["contributors"],
            ["Jorge", "Xomas", "Megas", "Playera", "Mensva"],
        )

    def test_release_24_is_the_zarking_update(self):
        notice = release_notice_for_version("v2.4")
        self.assertIsNotNone(notice)
        self.assertEqual(notice["title"], "Xomacito 2.4")
        self.assertEqual(notice["subtitle"], "¡LA ZARKING UPDATE!")
        self.assertIn("Zarking", notice["contributors"])
        highlights = " ".join(notice["highlights"]).lower()
        self.assertIn("reescalado", highlights)
        self.assertIn("birefnet", highlights)

    def test_release_25_is_the_papu_update(self):
        notice = release_notice_for_version("v2.5")
        self.assertIsNotNone(notice)
        self.assertEqual(notice["title"], "Xomacito 2.5")
        self.assertEqual(notice["subtitle"], "¡LA PAPU UPDATE!!")
        highlights = " ".join(notice["highlights"]).lower()
        self.assertIn("mp3", highlights)
        self.assertIn("arrastra", highlights)
        self.assertIn("portada", highlights)

    def test_release_26_announces_the_platinum_gacha_and_spike(self):
        notice = release_notice_for_version("v2.6")
        self.assertIsNotNone(notice)
        self.assertEqual(notice["title"], "Xomacito 2.6")
        self.assertEqual(notice["subtitle"], "¡LA PLATINO GACHA UPDATE!!")
        self.assertIn("Spike", notice["contributors"])
        self.assertTrue(notice["platinumCelebration"])
        highlights = " ".join(notice["highlights"]).lower()
        self.assertIn("142", highlights)
        self.assertIn("6★", highlights)
        self.assertIn("gato mago", highlights)

    def test_release_27_fixes_playlists_and_thanks_blackbull(self):
        notice = release_notice_for_version("v2.7")
        self.assertIsNotNone(notice)
        self.assertEqual(notice["title"], "Xomacito 2.7")
        self.assertEqual(notice["subtitle"], "¡LA BLACKBULL PLAYLIST UPDATE!!")
        self.assertIn("BlackBull", notice["contributors"])
        self.assertTrue(notice["platinumCelebration"])
        highlights = " ".join(notice["highlights"]).lower()
        self.assertIn("playlist", highlights)
        self.assertIn("zarking", highlights)

    def test_release_28_mentions_progressive_analysis_and_real_mp3(self):
        notice = release_notice_for_version("v2.8")
        self.assertIsNotNone(notice)
        self.assertEqual(notice["title"], "Xomacito 2.8")
        highlights = " ".join(notice["highlights"])
        self.assertIn("progresivo", highlights.lower())
        self.assertIn("mp3 real", highlights.lower())
        self.assertTrue(notice["platinumCelebration"])

    def test_release_29_previews_playlists_and_thanks_eduardito(self):
        notice = release_notice_for_version("v2.9")
        self.assertIsNotNone(notice)
        self.assertEqual(notice["title"], "Xomacito 2.9")
        self.assertEqual(notice["subtitle"], "¡LA EDUARDITO UPDATE!!")
        self.assertIn("Eduardito3d", notice["contributors"])
        highlights = " ".join(notice["highlights"]).lower()
        self.assertIn("previsualización", highlights)
        self.assertIn("etiquetas", highlights)

    def test_release_30_announces_mythic_gacha_and_fair_queue_progress(self):
        notice = release_notice_for_version("v3.0")

        self.assertIsNotNone(notice)
        self.assertEqual(notice["title"], "Xomacito 3.0")
        self.assertEqual(notice["subtitle"], "¡LA GACHA MÍTICA UPDATE!!")
        highlights = " ".join(notice["highlights"]).upper()
        self.assertIn("GATO MAGO", highlights)
        self.assertIn("GATO PLAYERA", highlights)
        self.assertIn("GATO ZARKING", highlights)
        self.assertIn("COLA", highlights)

    def test_release_31_announces_gako_and_media_workflow_fixes(self):
        notice = release_notice_for_version("v3.1")

        self.assertIsNotNone(notice)
        self.assertEqual(notice["title"], "Xomacito 3.1")
        self.assertIn("GAKO", notice["subtitle"].upper())
        highlights = " ".join(notice["highlights"]).lower()
        self.assertIn("playlists", highlights)
        self.assertIn("jpeg", highlights)
        self.assertIn("instagram", highlights)
        self.assertTrue(notice["platinumCelebration"])

    def test_release_32_is_the_black_bull_smooth_motion_edition(self):
        notice = release_notice_for_version("v3.2")

        self.assertIsNotNone(notice)
        self.assertEqual(notice["title"], "Xomacito 3.2")
        self.assertEqual(notice["subtitle"], "¡BLACK BULL EDITION!!!")
        highlights = " ".join(notice["highlights"]).upper()
        self.assertIn("BLACK BULL", highlights)
        self.assertNotIn("GATO BLACK BULL", highlights)
        self.assertIn("SMOOTH MOTION", highlights)
        self.assertTrue(notice["platinumCelebration"])
        self.assertTrue(notice["smoothMotionPromotion"])

    def test_release_34_is_the_community_streaks_update(self):
        notice = release_notice_for_version("v3.4")

        self.assertIsNotNone(notice)
        self.assertEqual(notice["title"], "Xomacito 3.4")
        self.assertEqual(notice["subtitle"], "¡RACHAS DE COMUNIDAD UPDATE!!")
        highlights = " ".join(notice["highlights"]).upper()
        self.assertIn("RACHAS DIARIAS", highlights)
        self.assertIn("PODIO", highlights)
        self.assertTrue(notice["smoothMotionPromotion"])

    def test_release_35_is_the_papu_update(self):
        notice = release_notice_for_version("v3.5")

        self.assertIsNotNone(notice)
        self.assertEqual(notice["title"], "Xomacito 3.5")
        self.assertEqual(notice["subtitle"], "¡THE PAPU UPDATE!!")
        highlights = " ".join(notice["highlights"]).upper()
        self.assertIn("FORMULARIO DE ID", highlights)
        self.assertIn("BLACK BULL", highlights)
        self.assertTrue(notice["smoothMotionPromotion"])

    def test_release_409_restores_every_historical_contributor(self):
        notice = release_notice_for_version("4.0.9")

        self.assertIsNotNone(notice)
        self.assertEqual(notice["title"], "Xomacito 1.0")
        for contributor in (
            "Jorge", "Xomas", "Megas", "Playera", "Mensva", "Zarking", "Spike",
            "BlackBull", "Eduardito3d", "Gako", "Ale", "Rykozio", "Strike", "Zane", "Nuan",
        ):
            self.assertIn(contributor, notice["contributors"])
        self.assertNotIn("Frido", notice["contributors"])
        self.assertIn("contraseña", " ".join(notice["highlights"]))
        self.assertIn("computadoras", " ".join(notice["highlights"]))

    def test_release_4010_explains_roll_and_collection_repairs(self):
        notice = release_notice_for_version("4.0.10")

        self.assertIsNotNone(notice)
        highlights = " ".join(notice["highlights"])
        self.assertIn("tiradas gastadas", highlights)
        self.assertIn("instalación nueva", highlights)
        self.assertIn("PERRO ZANE", highlights)
        self.assertIn("modelos de IA", highlights)

    def test_app_installer_download_checks_size_pe_header_and_sha256(self):
        payload = b"MZ" + (b"xomacito" * 64)
        digest = "sha256:" + hashlib.sha256(payload).hexdigest()
        update_info = {
            "latest_version": "1.6.1",
            "installer_url": (
                "https://github.com/Strike2911/Xomacito/"
                "releases/download/v1.6.1/Xomacito-1.6.1-Setup.exe"
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

    def test_app_installer_download_uses_a_unique_name_for_each_attempt(self):
        payload = b"MZ" + (b"unique" * 16)
        update_info = {
            "latest_version": "1.6.3",
            "installer_url": (
                "https://github.com/Strike2911/Xomacito/"
                "releases/download/v1.6.3/Xomacito-1.6.3-Setup.exe"
            ),
            "installer_size": len(payload),
            "installer_digest": "sha256:" + hashlib.sha256(payload).hexdigest(),
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
            with patch("src.core.app_updater.tempfile.gettempdir", return_value=directory):
                first = download_installer(update_info, session=FakeSession())
                second = download_installer(update_info, session=FakeSession())

            self.assertNotEqual(first, second)
            self.assertRegex(first.name, r"^Xomacito-1\.6\.3-Setup-[0-9a-f]{12}\.exe$")
            self.assertTrue(first.exists())
            self.assertTrue(second.exists())

    def test_deferred_installer_waits_for_xomacito_before_starting_setup(self):
        with tempfile.TemporaryDirectory() as directory:
            installer = Path(directory) / "Xomacito Setup.exe"
            launcher = Path(directory) / "launch update.ps1"
            installer.write_bytes(b"MZ")

            command = deferred_installer_command(installer, 4321, launcher)
            script = launcher.read_text(encoding="utf-8-sig")

            self.assertEqual(command[0], "powershell.exe")
            self.assertIn("4321", command)
            self.assertIn(str(installer.resolve()), command)
            self.assertIn("Get-Process -Id $XomacitoProcessId", script)
            self.assertIn("Stop-Process -Id $XomacitoProcessId", script)
            self.assertIn("Start-Process -FilePath $InstallerPath", script)
            self.assertIn("-Wait -PassThru", script)
            self.assertIn("/XOMACITOUPDATE=1", script)

        application = (ROOT / "src" / "ui" / "application.py").read_text(encoding="utf-8")
        self.assertIn("deferred_installer_command(path, os.getpid())", application)
        self.assertNotIn("silent_installer_command", application)

    def test_app_installer_rejects_a_wrong_digest(self):
        payload = b"MZinvalid"
        update_info = {
            "latest_version": "1.6.1",
            "installer_url": (
                "https://github.com/Strike2911/Xomacito/"
                "releases/download/v1.6.1/Xomacito-1.6.1-Setup.exe"
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
        application_source = (ROOT / "src" / "ui" / "application.py").read_text(encoding="utf-8")
        instance_source = (ROOT / "src" / "core" / "single_instance.py").read_text(encoding="utf-8")
        self.assertIn("SingleInstanceGuard(APP_NAME)", main_source)
        self.assertIn("focus_existing_window(APP_NAME)", main_source)
        self.assertNotIn("xomacito.lock", application_source)
        self.assertNotIn("IsWindowVisible", instance_source)
        self.assertIn("user32.ShowWindow(hwnd, SW_SHOW)", instance_source)
        self.assertIn("user32.BringWindowToTop(hwnd)", instance_source)

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
            def get(url, timeout, allow_redirects, headers=None):
                self.assertEqual(url, "https://www.instagram.com/p/ABC123/")
                self.assertEqual(timeout, 5)
                self.assertTrue(allow_redirects)
                self.assertIn("User-Agent", headers or {})
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

    def test_instagram_carousel_uses_public_embed_images(self):
        class FakeResponse:
            def __init__(self, text):
                self.text = text

            @staticmethod
            def raise_for_status():
                return None

        class FakeSession:
            @staticmethod
            def get(url, timeout, allow_redirects, headers=None):
                if url.endswith("/embed/captioned/"):
                    return FakeResponse(
                        '<img width="1080" height="1080" src="https://scontent.cdninstagram.com/one.jpg">'
                        '<img width="1080" height="1080" src="https://scontent.cdninstagram.com/two.jpg">'
                        '<img width="1080" height="1080" src="https://scontent.cdninstagram.com/three.jpg">'
                        '<img width="1080" height="1080" src="https://scontent.cdninstagram.com/four.jpg">'
                    )
                return FakeResponse('<meta property="og:image" content="https://scontent.cdninstagram.com/one.jpg">')

        info = downloader.extract_instagram_image_post_info(
            "https://www.instagram.com/p/CAROUSEL/?utm_source=test",
            timeout=5,
            session=FakeSession(),
        )
        self.assertEqual(info["image_count"], 4)
        self.assertEqual(len(info["xomacito_images"]), 4)

    def test_instagram_carousel_uses_authenticated_media_info(self):
        class FakeResponse:
            def __init__(self, *, text="", payload=None):
                self.text = text
                self._payload = payload

            @staticmethod
            def raise_for_status():
                return None

            def json(self):
                return self._payload

        slides = [
            {
                "image_versions2": {
                    "candidates": [
                        {"url": f"https://instagram.example/{number}-small.jpg", "width": 320, "height": 320},
                        {"url": f"https://instagram.example/{number}.jpg", "width": 1080, "height": 1080},
                    ]
                }
            }
            for number in range(1, 5)
        ]

        class FakeSession:
            @staticmethod
            def get(url, **kwargs):
                if url.endswith("/oembed/"):
                    return FakeResponse(payload={"media_id": "123_456", "title": "Carrusel"})
                if "/api/v1/media/" in url:
                    return FakeResponse(payload={"items": [{"carousel_media": slides}]})
                return FakeResponse(text='<meta property="og:image" content="https://instagram.example/1.jpg">')

        info = downloader.extract_instagram_image_post_info(
            "https://www.instagram.com/p/PRIVATECAROUSEL/",
            timeout=5,
            session=FakeSession(),
        )
        self.assertEqual(info["image_count"], 4)
        self.assertEqual(info["xomacito_images"][-1], "https://instagram.example/4.jpg")

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
        source = (ROOT / "src" / "ui" / "download_controller.py").read_text(encoding="utf-8")
        self.assertIn("extract_instagram_image_post_info(url, ydl_options=options)", source)
        self.assertIn('info.get("xomacito_media_type") != "image"', source)
        self.assertIn("def saveThumbnail(self):", source)
        self.assertIn("def _download_image_post", source)

    def test_image_posts_offer_explicit_export_extensions(self):
        qml = (ROOT / "src" / "ui" / "qml" / "pages" / "DownloadPage.qml").read_text(encoding="utf-8")
        controller = (ROOT / "src" / "ui" / "download_controller.py").read_text(encoding="utf-8")
        image_controller = (ROOT / "src" / "ui" / "image_controller.py").read_text(encoding="utf-8")
        self.assertIn('["Original", "JPEG", "JPG", "PNG", "WEBP"]', qml)
        self.assertIn('{"JPEG": ".jpeg", "JPG": ".jpg", "PNG": ".png", "WEBP": ".webp"}', controller)
        self.assertIn('output_format == "JPEG": extension = ".jpeg"', image_controller)

    def test_xomacito_launcher_and_standalone_runtime_are_present(self):
        launcher_exe = ROOT / "Xomacito.exe"
        app_exe = ROOT / "dist" / "Xomacito" / "Xomacito.exe"
        installers = list((ROOT / "release").glob("*Setup*.exe"))
        self.assertTrue(installers)
        installer = max(installers, key=lambda candidate: candidate.stat().st_mtime)
        self.assertGreater(launcher_exe.stat().st_size, 100_000)
        self.assertGreater(app_exe.stat().st_size, 100_000)
        self.assertGreater(installer.stat().st_size, 100_000)

    def test_packaged_runtime_is_present(self):
        self.assertTrue((ROOT / "dist" / "Xomacito" / "_internal" / "python311.dll").exists())
        self.assertTrue((ROOT / "src" / "ui" / "qml" / "Main.qml").exists())
        self.assertTrue((ROOT / "bin" / "ffmpeg" / "ffmpeg.exe").exists())

    def test_recode_profiles_preserve_quality_and_compatibility(self):
        x265_profiles = CODEC_PROFILES["Video"]["H.265 (x265)"]["libx265"]
        for profile_name in (
            "Calidad Máxima (CRF 16)",
            "Calidad Alta (CRF 20)",
            "Calidad Equilibrada (CRF 20)",
            "Calidad Media (CRF 24)",
        ):
            params = x265_profiles[profile_name]
            self.assertEqual(params[params.index("-pix_fmt") + 1], "yuv420p")

        prores_profiles = CODEC_PROFILES["Video"][
            "Apple ProRes (prores_ks) (Precisión)"
        ]["prores_ks"]
        self.assertEqual(
            prores_profiles["4444"][prores_profiles["4444"].index("-pix_fmt") + 1],
            "yuva444p10le",
        )
        light_alpha_params = prores_profiles["4444 Liviano (Alpha 8-bit)"]
        self.assertTrue(recode_parameters_preserve_alpha(light_alpha_params))
        self.assertFalse(recode_parameters_preserve_alpha(prores_profiles["422 Proxy"]))
        self.assertTrue(pixel_format_has_alpha("argb"))
        self.assertTrue(pixel_format_has_alpha("yuva444p12le"))
        self.assertFalse(pixel_format_has_alpha("yuv422p10le"))

        normalized = normalize_recode_parameters(["-c:v", "libx265"], ".mp4")
        self.assertIn("-map_metadata", normalized)
        self.assertIn("-map_chapters", normalized)
        self.assertIn("-movflags", normalized)
        self.assertEqual(normalized.count("-movflags"), 1)
        self.assertEqual(normalized[normalized.index("-f") + 1], "mp4")
        self.assertEqual(normalized.count("-f"), 1)

    def test_old_encoder_cache_cannot_restore_obsolete_recode_profiles(self):
        cache = {
            "ffmpeg_version": "ffmpeg test",
            "app_version": "1.6.3",
            "encoders": {"CPU": {"Video": {"H.265 (x265)": {}}}},
        }
        self.assertFalse(encoder_cache_is_valid(cache, "ffmpeg test", "1.6.3"))

        cache["schema_version"] = ENCODER_CACHE_SCHEMA_VERSION
        self.assertTrue(encoder_cache_is_valid(cache, "ffmpeg test", "1.6.3"))

    def test_recode_result_validation_rejects_incomplete_outputs(self):
        valid = {
            "format": {"duration": "5.0"},
            "streams": [{"codec_type": "video"}],
        }
        self.assertTrue(validate_recode_result_info(valid, "Video+Audio", 5.0))

        with self.assertRaisesRegex(ValueError, "pista de video"):
            validate_recode_result_info(
                {"format": {"duration": "5.0"}, "streams": [{"codec_type": "audio"}]},
                "Video+Audio",
                5.0,
            )
        with self.assertRaisesRegex(ValueError, "duración"):
            validate_recode_result_info(valid, "Video+Audio", 20.0)

    def test_h265_recode_keeps_60_fps_and_generates_a_compatible_mp4(self):
        ffmpeg_path = ROOT / "bin" / "ffmpeg" / "ffmpeg.exe"
        ffprobe_path = ffmpeg_path.with_name("ffprobe.exe")
        if not ffmpeg_path.exists() or not ffprobe_path.exists():
            self.skipTest("FFmpeg no está disponible en este entorno.")

        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "source.mkv"
            output = Path(directory) / "output.mp4.temp"
            generated = subprocess.run(
                [
                    str(ffmpeg_path), "-hide_banner", "-loglevel", "error", "-y",
                    "-f", "lavfi", "-i", "testsrc2=size=180x320:rate=60:duration=1",
                    "-c:v", "ffv1", "-pix_fmt", "yuv444p", str(source),
                ],
                capture_output=True,
                text=True,
                timeout=30,
                check=False,
            )
            self.assertEqual(generated.returncode, 0, generated.stderr)

            processor = FFmpegProcessor(app_version="test")
            profile = CODEC_PROFILES["Video"]["H.265 (x265)"]["libx265"][
                "Calidad Equilibrada (CRF 20)"
            ]
            processor.execute_recode(
                {
                    "input_file": str(source),
                    "output_file": str(output),
                    "output_container": ".mp4",
                    "duration": 1,
                    "ffmpeg_params": [*profile, "-an"],
                    "mode": "Video+Audio",
                    "selected_video_stream_index": 0,
                    "selected_audio_stream_index": None,
                },
                lambda *_args: None,
                threading.Event(),
            )

            probed = subprocess.run(
                [
                    str(ffprobe_path), "-v", "error", "-select_streams", "v:0",
                    "-show_entries", "stream=pix_fmt,avg_frame_rate",
                    "-of", "json", str(output),
                ],
                capture_output=True,
                text=True,
                timeout=20,
                check=False,
            )
            self.assertEqual(probed.returncode, 0, probed.stderr)
            stream = json.loads(probed.stdout)["streams"][0]
            self.assertEqual(stream["pix_fmt"], "yuv420p")
            self.assertEqual(stream["avg_frame_rate"], "60/1")

            mp4_header = output.read_bytes()[:128_000]
            moov_position = mp4_header.find(b"moov")
            mdat_position = mp4_header.find(b"mdat")
            self.assertGreaterEqual(moov_position, 0)
            self.assertGreaterEqual(mdat_position, 0)
            self.assertLess(moov_position, mdat_position)

    def test_prores_4444_light_preserves_alpha_and_422_is_rejected(self):
        ffmpeg_path = ROOT / "bin" / "ffmpeg" / "ffmpeg.exe"
        ffprobe_path = ffmpeg_path.with_name("ffprobe.exe")
        if not ffmpeg_path.exists() or not ffprobe_path.exists():
            self.skipTest("FFmpeg no está disponible en este entorno.")

        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "alpha-source.mov"
            output = Path(directory) / "alpha-output.mov.temp"
            generated = subprocess.run(
                [
                    str(ffmpeg_path), "-hide_banner", "-loglevel", "error", "-y",
                    "-f", "lavfi", "-i", "color=c=red@0.25:s=64x64:r=30:d=0.5,format=rgba",
                    "-c:v", "qtrle", "-pix_fmt", "argb", str(source),
                ],
                capture_output=True,
                text=True,
                timeout=30,
                check=False,
            )
            self.assertEqual(generated.returncode, 0, generated.stderr)

            processor = FFmpegProcessor(app_version="test")
            profiles = CODEC_PROFILES["Video"][
                "Apple ProRes (prores_ks) (Precisión)"
            ]["prores_ks"]
            processor.execute_recode(
                {
                    "input_file": str(source),
                    "output_file": str(output),
                    "output_container": ".mov",
                    "duration": 0.5,
                    "ffmpeg_params": [*profiles["4444 Liviano (Alpha 8-bit)"], "-an"],
                    "mode": "Video+Audio",
                    "selected_video_stream_index": 0,
                    "selected_audio_stream_index": None,
                },
                lambda *_args: None,
                threading.Event(),
            )
            probe = subprocess.run(
                [
                    str(ffprobe_path), "-v", "error", "-select_streams", "v:0",
                    "-show_entries", "stream=pix_fmt", "-of", "default=nw=1:nk=1",
                    str(output),
                ],
                capture_output=True,
                text=True,
                timeout=20,
                check=False,
            )
            self.assertEqual(probe.returncode, 0, probe.stderr)
            self.assertTrue(pixel_format_has_alpha(probe.stdout.strip()))

            with self.assertRaisesRegex(Exception, "perfil seleccionado la eliminaría"):
                processor.execute_recode(
                    {
                        "input_file": str(source),
                        "output_file": str(Path(directory) / "invalid.mov.temp"),
                        "output_container": ".mov",
                        "duration": 0.5,
                        "ffmpeg_params": ["-f", "mov", *profiles["422 Proxy"], "-an"],
                        "mode": "Video+Audio",
                        "selected_video_stream_index": 0,
                        "selected_audio_stream_index": None,
                    },
                    lambda *_args: None,
                    threading.Event(),
                )

    def test_branding_is_xomacito(self):
        main_qml = (ROOT / "src" / "ui" / "qml" / "Main.qml").read_text(encoding="utf-8")
        application_py = (ROOT / "src" / "ui" / "application.py").read_text(encoding="utf-8")
        download_qml = (ROOT / "src" / "ui" / "qml" / "pages" / "DownloadPage.qml").read_text(encoding="utf-8")
        self.assertIn("XOMACITO", main_qml)
        self.assertNotIn(LEGACY_APP_NAME, main_qml + application_py + download_qml)

    def test_legacy_maintenance_panel_is_removed(self):
        ui_source = "\n".join(path.read_text(encoding="utf-8") for path in (ROOT / "src" / "ui").rglob("*.qml"))
        self.assertNotIn('text: "Mantenimiento"', ui_source)
        self.assertNotIn("MarckDP/Xomacito", ui_source)
        self.assertNotIn("app_status_label", ui_source)

    def test_completion_sound_is_installed(self):
        sound = ROOT / "assets" / "download-complete.mp3"
        self.assertTrue(sound.exists())
        self.assertGreater(sound.stat().st_size, 5_000)
        self.assertEqual(sound.read_bytes()[:3], b"ID3")
        self.assertEqual(completion_sound_path(), sound)

    def test_completion_meow_is_attenuated_by_ten_decibels(self):
        with patch("src.core.notification_sound._play_async", return_value=True) as playback:
            self.assertTrue(play_completion_sound())
        playback.assert_called_once_with(completion_sound_path(), volume=316)

    def test_platinum_celebration_has_its_own_sound(self):
        sound = ROOT / "assets" / "sfx" / "platinum-celebration.mp3"
        self.assertTrue(sound.exists())
        self.assertGreater(sound.stat().st_size, 10_000)
        self.assertEqual(sound.read_bytes()[:3], b"ID3")
        self.assertEqual(platinum_sound_path(), sound)

    def test_gacha_reveal_sounds_cover_every_rarity(self):
        self.assertEqual(set(GACHA_SOUND_FILENAMES), {1, 2, 3, 4, 5, 6})
        sizes = []
        for rarity in range(1, 7):
            sound = gacha_sound_path(rarity)
            self.assertIsNotNone(sound)
            self.assertTrue(sound.is_file())
            self.assertGreater(sound.stat().st_size, 2_000)
            sizes.append(sound.stat().st_size)
        self.assertEqual(gacha_sound_path(0), gacha_sound_path(1))
        self.assertEqual(gacha_sound_path(99), gacha_sound_path(6))
        self.assertEqual(sizes, sorted(sizes))
        self.assertEqual(
            set(GACHA_STYLE_SOUND_FILENAMES),
            {"arcane-mage", "playera-prismatic", "zarking-cyber", "blackbull-noir", "strike-apex"},
        )
        self.assertEqual(set(GACHA_EQUIP_SOUND_FILENAMES), set(GACHA_STYLE_SOUND_FILENAMES))
        for style in GACHA_STYLE_SOUND_FILENAMES:
            reveal = gacha_sound_path(6, style)
            equip = gacha_equip_sound_path(style)
            self.assertTrue(reveal and reveal.is_file())
            self.assertTrue(equip and equip.is_file())
            self.assertNotEqual(reveal, equip)

        application = (ROOT / "src" / "ui" / "application.py").read_text(encoding="utf-8")
        self.assertIn("successfulDownload.connect(self._play_download_completion)", application)
        self.assertIn("revealRequested.connect(self._play_cat_reveal)", application)
        self.assertIn("equippedRequested.connect(self._play_cat_equip)", application)

    def test_gacha_sounds_keep_headroom_and_smooth_transients(self):
        sounds = sorted((ROOT / "assets" / "sfx").glob("gacha-*.wav"))
        self.assertGreaterEqual(len(sounds), 13)
        for sound in sounds:
            with wave.open(str(sound), "rb") as reader:
                self.assertEqual(reader.getsampwidth(), 2)
                samples = array.array("h", reader.readframes(reader.getnframes()))
            peak = max(abs(sample) for sample in samples) / 32767
            deltas = sorted(
                abs(samples[index] - samples[index - 1]) / 32767
                for index in range(1, len(samples))
            )
            percentile_99 = deltas[int(len(deltas) * 0.99)]
            self.assertLessEqual(peak, 0.63, sound.name)
            self.assertGreater(peak, 0.50, sound.name)
            self.assertLess(percentile_99, 0.10, sound.name)

    def test_runtime_uses_updatable_ytdlp_zip(self):
        helper = (ROOT / "src" / "core" / "ytdlp_runtime.py").read_text(encoding="utf-8")
        self.assertIn("yt-dlp.zip", helper)
        self.assertIn("configure_ytdlp_options", helper)
        self.assertIn("def lazy_ytdlp", helper)
        for relative in (
            "core/downloader.py",
            "core/batch_processor.py",
        ):
            source = (ROOT / "src" / relative).read_text(encoding="utf-8")
            self.assertIn("lazy_ytdlp", source, relative)
        ui_source = (ROOT / "src" / "ui" / "download_controller.py").read_text(encoding="utf-8")
        self.assertIn("configure_ytdlp_options", ui_source)

        # Abrir el flujo principal no debe cargar el motor antes de que el
        # usuario analice o descargue una URL.
        result = subprocess.run(
            [
                sys.executable,
                "-c",
                "import sys; import src.ui.download_controller; "
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

    def test_console_diagnostics_never_abort_on_windows_legacy_encoding(self):
        raw = io.BytesIO()
        legacy_stream = io.TextIOWrapper(raw, encoding="cp1252", errors="strict")
        with patch("sys.stdout", legacy_stream):
            safe_console_print("📥 Descarga: canción 嬉")
        legacy_stream.flush()
        self.assertIn("Descarga", raw.getvalue().decode("cp1252"))

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
        main_qml = (ROOT / "src" / "ui" / "qml" / "Main.qml").read_text(encoding="utf-8")
        self.assertIn('text: "XOMACITO"', main_qml)
        self.assertIn("appController.catName", main_qml)
        self.assertIn("appController.catRarity", main_qml)
        self.assertIn("DownloadPage", main_qml)
        self.assertIn("ImageStudioPage", main_qml)
        self.assertIn("MediaLibraryPage", main_qml)
        self.assertIn("StackLayout", main_qml)

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
        source = (ROOT / "src" / "ui" / "qml" / "pages" / "SettingsPage.qml").read_text(encoding="utf-8")
        self.assertIn("Strike2911/Xomacito", source)
        self.assertIn("https://www.youtube.com/@ElStrikew", source)
        self.assertIn("https://ko-fi.com/strikepoint", source)
        self.assertNotIn("MarckDBM", source)

    def test_brand_icon_is_canonical_and_legacy_artifacts_are_absent(self):
        self.assertEqual(
            (ROOT / "Xomacito-icon.ico").read_bytes(),
            (ROOT / "assets" / "cat-icons" / "cat-01.ico").read_bytes(),
        )
        obsolete_paths = (
            "Legacy-icon.ico", "XomacitoCore.exe", "XomacitoTitleFixer.exe",
            "XomacitoTitleFixer.spec", "title_fixer.py", "app.py",
            "runtime_bootstrap.py", "_extracted_main.pyc", "_main_extracted.pyc",
            "_internal", "engine", "build",
        )
        for relative in obsolete_paths:
            self.assertFalse((ROOT / relative).exists(), relative)

        build_entries = {path.name for path in (ROOT / ".build").iterdir() if path.is_file()}
        self.assertEqual(
            build_entries,
            {"XomacitoInstaller.spec", "XomacitoLauncher.spec", "XomacitoPublic.spec"},
        )


    def test_eight_daily_cat_icons_are_installed(self):
        cat_dir = ROOT / "assets" / "cat-icons"
        self.assertEqual(CAT_COUNT, 8)
        for number in range(1, 9):
            self.assertGreater((cat_dir / f"cat-{number:02d}.png").stat().st_size, 10_000)
            self.assertGreater((cat_dir / f"cat-{number:02d}.ico").stat().st_size, 10_000)
            self.assertGreater((cat_dir / f"cat-{number:02d}-ui.png").stat().st_size, 10_000)

    def test_daily_cat_changes_once_per_day_and_cycles(self):
        start = date(2026, 1, 1)
        sequence = [daily_cat_number(start + timedelta(days=offset)) for offset in range(9)]
        self.assertEqual(len(set(sequence[:8])), 8)
        self.assertEqual(sequence[0], sequence[8])
        selected = daily_cat_assets(ROOT, start)
        self.assertTrue(selected.png_path.exists())
        self.assertTrue(selected.ico_path.exists())
        self.assertTrue(selected.ui_path.exists())

    def test_gradient_shell_is_integrated_without_replacing_tabs(self):
        source = (ROOT / "src" / "ui" / "qml" / "Main.qml").read_text(encoding="utf-8")
        self.assertIn("Gradient", source)
        self.assertIn("appController.catSource", source)
        self.assertIn("theme.colors.backgroundAlt", source)
        self.assertIn("StackLayout", source)
        for page in ("DownloadPage", "QueuePage", "MediaLibraryPage", "ImageStudioPage", "SettingsPage"):
            self.assertIn(page, source)

    def test_secondary_tabs_and_heavy_engines_are_loaded_on_demand(self):
        qml = (ROOT / "src" / "ui" / "qml" / "Main.qml").read_text(encoding="utf-8")
        image_source = (ROOT / "src" / "ui" / "image_controller.py").read_text(encoding="utf-8")
        workers = (ROOT / "src" / "ui" / "workers.py").read_text(encoding="utf-8")

        self.assertEqual(qml.count("StackLayout"), 1)
        self.assertNotIn("Loader {", qml.split("StackLayout", 1)[1].split("Popup", 1)[0])
        self.assertIn("def _ensure_engines", image_source)
        imports = image_source.split("class ImageController", 1)[0]
        self.assertNotIn("from src.core.image_converter import", imports)
        self.assertNotIn("from src.core.image_processor import", imports)
        self.assertIn("QThreadPool.globalInstance", workers)
        self.assertNotIn("Construyendo Configuración", qml)

    def test_builtin_blue_theme_drives_shell_and_custom_widgets(self):
        theme_source = (ROOT / "src" / "ui" / "theme.py").read_text(encoding="utf-8")
        main_qml = (ROOT / "src" / "ui" / "qml" / "Main.qml").read_text(encoding="utf-8")
        self.assertIn("FALLBACK_DARK", theme_source)
        self.assertIn('"background": "#061522"', theme_source)
        self.assertIn('"primary": "#20C9E8"', theme_source)
        self.assertIn("theme.colors.background", main_qml)
        self.assertIn("theme.colors.primary", main_qml)

    def test_scrollable_panels_use_solid_theme_surfaces(self):
        pages = "\n".join(path.read_text(encoding="utf-8") for path in (ROOT / "src" / "ui" / "qml" / "pages").glob("*.qml"))
        card = (ROOT / "src" / "ui" / "qml" / "components" / "XCard.qml").read_text(encoding="utf-8")
        self.assertGreaterEqual(pages.count("ScrollView"), 5)
        self.assertIn("theme.colors.surface", card)
        self.assertNotIn("MouseWheel", pages)

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
        themes = sorted((ROOT / "src" / "ui" / "themes").glob("*.json"))
        self.assertEqual(len(themes), 12)
        for path in themes:
            data = json.loads(path.read_text(encoding="utf-8-sig"))
            if path.name == "Strike.json":
                self.assertEqual(data["ThemeName"], "Strike")
                self.assertTrue({
                    "background_top", "background_bottom", "glow_primary", "glow_secondary",
                    "header_top", "header_bottom", "header_border", "font_family",
                }.issubset(data["XomacitoVisual"]))
                continue
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

    def test_functional_surfaces_are_derived_from_each_active_theme(self):
        dark_cards = set()
        themes = sorted((ROOT / "src" / "ui" / "themes").glob("*.json"))
        for path in themes:
            data = json.loads(path.read_text(encoding="utf-8-sig"))
            visual = data["XomacitoVisual"]
            for key in ("background_top", "background_bottom", "header_top", "header_bottom", "header_border"):
                self.assertEqual(len(visual[key]), 2, f"{path.name}:{key}")
            self.assertNotEqual(visual["header_top"][1], visual["background_bottom"][1], path.name)
            self.assertNotEqual(visual["header_bottom"][1], visual["header_top"][1], path.name)
            dark_cards.add(visual["header_top"][1])
        self.assertEqual(len(dark_cards), len(themes))

    def test_image_studio_import_survives_missing_native_cairo(self):
        from src.core import image_converter, image_processor

        self.assertIsInstance(image_converter.CAN_SVG, bool)
        self.assertIsInstance(image_processor.CAN_SVG, bool)

    def test_frozen_restart_uses_an_independent_pyinstaller_environment(self):
        environment = clean_restart_environment({"EXAMPLE": "kept"})
        self.assertEqual(environment["EXAMPLE"], "kept")
        self.assertEqual(environment["PYINSTALLER_RESET_ENVIRONMENT"], "1")
        theme_source = (ROOT / "src" / "ui" / "theme.py").read_text(encoding="utf-8")
        application_source = (ROOT / "src" / "ui" / "application.py").read_text(encoding="utf-8")
        self.assertIn("self.reload()", theme_source)
        self.assertNotIn("restart_application", theme_source)
        self.assertIn("deferred_installer_command", application_source)

    def test_explicit_builtin_theme_survives_restart(self):
        source = (ROOT / "src" / "ui" / "theme.py").read_text(encoding="utf-8")
        self.assertIn('self.builtin_dir = self.project_root / "src" / "ui" / "themes"', source)
        self.assertIn('"theme_selection_explicit": True', source)
        self.assertIn('self.settings.set("appearance_mode", appearance)', source)

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
        self.assertIn("OutputBaseFilename=Xomacito-1.0-Setup", installer)
        self.assertIn('#define MyAppVersion "4.0.10"', installer)
        self.assertIn('#define MyAppDisplayVersion "1.0"', installer)
        self.assertIn("shellexec postinstall skipifsilent skipifdoesntexist", installer)
        self.assertIn("CloseApplications=force", installer)
        self.assertIn("CloseApplicationsFilter=Xomacito.exe,ffmpeg.exe,ffprobe.exe", installer)
        self.assertNotIn("CloseApplicationsFilter=*.*", installer)
        self.assertIn("Compression=lzma2/max", installer)
        self.assertIn("SolidCompression=yes", installer)
        self.assertIn("[UninstallRun]", installer)
        self.assertIn('{sys}\\taskkill.exe', installer)
        self.assertIn('/F /IM ""{#MyAppExeName}""', installer)
        self.assertIn("Uninstallable=yes", installer)
        self.assertIn("Desinstalar Xomacito", installer)
        self.assertIn("{uninstallexe}", installer)
        self.assertIn("UninstallDisplayName={#MyAppName} {#MyAppDisplayVersion}", installer)
        self.assertIn("XOMACITOUPDATE", installer)
        self.assertIn("skipifnotsilent", installer)
        self.assertIn("IsAutoUpdate", installer)
        self.assertIn("function PrepareToInstall", installer)
        self.assertIn("ewWaitUntilTerminated", installer)
        self.assertIn("PreparingLabel.Caption", installer)
        self.assertIn("Sleep(150)", installer)
        self.assertIn('Name: "{userappdata}\\Xomacito\\encoder_cache.json"', installer)
        self.assertIn('Name: "{app}\\_internal\\bin\\models"', installer)
        self.assertIn("procedure CurUninstallStepChanged", installer)
        self.assertIn("DelTree(UserDataDir", installer)
        self.assertIn("UninstallSilent", installer)
        self.assertNotIn('Source: "{#ProjectRoot}\\bin\\ffmpeg', installer)
        self.assertNotIn("bin\\models\\*", installer)
        self.assertNotIn("engine\\", installer)

    def test_startup_uses_bundled_ffmpeg_without_auto_installing(self):
        application = (ROOT / "src" / "ui" / "application.py").read_text(encoding="utf-8")
        settings = (ROOT / "src" / "ui" / "settings_controller.py").read_text(encoding="utf-8")
        self.assertNotIn("download_and_install_ffmpeg", application)
        self.assertIn("refreshDependencies(False)", application)
        self.assertIn("def installDependency", settings)

        main_source = (ROOT / "main.py").read_text(encoding="utf-8")
        runtime_source = (ROOT / "src" / "core" / "ytdlp_runtime.py").read_text(encoding="utf-8")
        self.assertIn('BIN_PATH = INTERNAL_DIR / "bin"', main_source)
        self.assertIn('executable_root / "_internal"', runtime_source)
        self.assertGreater((ROOT / "bin" / "ffmpeg" / "ffmpeg.exe").stat().st_size, 100_000_000)

    def test_ai_models_are_kept_outside_the_frozen_installation(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            with patch.object(main, "FROZEN", True), patch.dict(
                os.environ,
                {"LOCALAPPDATA": temp_dir, "XOMACITO_MODELS_DIR": ""},
            ):
                self.assertEqual(
                    main._persistent_models_path(),
                    Path(temp_dir) / "Xomacito" / "models",
                )

    def test_legacy_model_migration_preserves_existing_user_copy(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            legacy = root / "installed" / "models"
            persistent = root / "user" / "models"
            (legacy / "rembg").mkdir(parents=True)
            (legacy / "rembg" / "new.onnx").write_bytes(b"downloaded")
            (legacy / "rembg" / "existing.onnx").write_bytes(b"old-install")
            (persistent / "rembg").mkdir(parents=True)
            (persistent / "rembg" / "existing.onnx").write_bytes(b"user-copy")

            copied = main.migrate_legacy_models(legacy, persistent)

            self.assertEqual(copied, 1)
            self.assertEqual((persistent / "rembg" / "new.onnx").read_bytes(), b"downloaded")
            self.assertEqual((persistent / "rembg" / "existing.onnx").read_bytes(), b"user-copy")

    def test_xomacito_is_standalone_without_editor_plugin_bridge(self):
        source_paths = tuple((ROOT / "src" / "ui").rglob("*.py")) + tuple((ROOT / "src" / "ui" / "qml").rglob("*.qml")) + (ROOT / "src" / "core" / "batch_processor.py",)
        combined_source = "\n".join(path.read_text(encoding="utf-8") for path in source_paths)
        forbidden_bridges = (
            "flask_socketio", "SocketIO", "IntegrationManager", "ACTIVE_TARGET_SID",
            "port=7788", "_check_whats_new", "DaVinci Resolve", "Adobe (Premiere",
        )
        for bridge in forbidden_bridges:
            self.assertNotIn(bridge, combined_source)

        self.assertFalse((ROOT / "src" / "core" / "integration_manager.py").exists())
        self.assertFalse((ROOT / "src" / "core" / "davinci_api.py").exists())
        installer_spec = (ROOT / ".build" / "XomacitoInstaller.spec").read_text(encoding="utf-8")
        self.assertNotIn("engineio.async_drivers", installer_spec)
        for package in ("flask_socketio", "socketio", "engineio", "gevent"):
            self.assertIn(package, installer_spec.split("excludes=", 1)[1])
        download_source = (ROOT / "src" / "ui" / "download_controller.py").read_text(encoding="utf-8")
        self.assertIn("def chooseLocalFile", download_source)

    def test_self_test_does_not_open_the_tk_interface(self):
        source = (ROOT / "main.py").read_text(encoding="utf-8")
        main_body = source.split("def main() -> int:", 1)[1].split("def _run_safely", 1)[0]
        self.assertLess(main_body.index('"--self-test"'), main_body.index("_run_main_window"))
        self.assertIn('INTERNAL_DIR / "src" / "ui" / "qml" / "Main.qml"', source)
        self.assertNotIn("customtkinter", source)
        self.assertNotIn("_tcl_data", source)
        self.assertNotIn("_tk_data", source)

    def test_release_build_and_benchmark_scripts_are_present(self):
        build_script = (ROOT / "scripts" / "build_release.ps1").read_text(encoding="utf-8-sig")
        benchmark_script = (ROOT / "scripts" / "benchmark_startup.ps1").read_text(encoding="utf-8-sig")
        cleanup_script = (ROOT / "scripts" / "clean_project.ps1").read_text(encoding="utf-8-sig")
        uninstall_launcher = ROOT / "installer" / "Desinstalar Xomacito.cmd"

        self.assertIn("XomacitoInstaller.spec", build_script)
        self.assertIn("Xomacito.iss", build_script)
        self.assertIn("release\\Xomacito-1.0-Setup.exe", build_script)
        self.assertIn("Assert-ReadableApplicationSource", build_script)
        self.assertIn("pyarmor_runtime|__pyarmor__|pytransform", build_script)
        self.assertIn('PROJECT_ROOT / "main\\.py"', build_script)
        self.assertNotIn("StableInstaller", build_script)
        self.assertNotIn("release\\setup.exe", build_script)
        installer_spec = (ROOT / ".build" / "XomacitoInstaller.spec").read_text(encoding="utf-8")
        self.assertIn('PROJECT_ROOT / "premiere-panel"', installer_spec)
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
