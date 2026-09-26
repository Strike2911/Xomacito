import unittest
import sys
from unittest.mock import patch

from src.core import downloader
from src.core.ytdlp_runtime import is_youtube_access_error, youtube_access_fallback_options


class EmbeddedFallbackTests(unittest.TestCase):
    def setUp(self):
        self.options = {
            "format": "bestvideo[height>=720]+bestaudio/best[height>=720]",
            "outtmpl": "chosen.%(ext)s",
            "extractor_args": {"youtube": {"player_client": ["web_embedded"], "lang": ["es"]}},
        }

    def test_embedded_unavailability_retries_once_and_preserves_selection(self):
        attempts = []
        class FakeYoutubeDL:
            def __init__(self, options):
                self.options = options
            def __enter__(self):
                return self
            def __exit__(self, *_):
                return False
            def extract_info(self, url, download=False):
                attempts.append((self.options, download))
                if len(attempts) == 1:
                    raise RuntimeError("ERROR: [youtube] 863rTle6CKY: Video unavailable")
                return {"id": "863rTle6CKY"}
        with patch.object(downloader.yt_dlp, "YoutubeDL", FakeYoutubeDL):
            result = downloader.extract_info_resilient("https://youtu.be/863rTle6CKY", self.options, download=True)
        self.assertEqual(result["id"], "863rTle6CKY")
        self.assertEqual(len(attempts), 2)
        retry, download = attempts[1]
        self.assertTrue(download)
        self.assertNotIn("player_client", retry["extractor_args"]["youtube"])
        self.assertEqual(retry["format"], self.options["format"])
        self.assertEqual(retry["outtmpl"], self.options["outtmpl"])
        self.assertEqual(retry["extractor_args"]["youtube"]["lang"], ["es"])
        self.assertEqual(self.options["extractor_args"]["youtube"]["player_client"], ["web_embedded"])

    def test_unavailability_is_scoped_to_embedded_youtube(self):
        for message in ("Private video", "Video unavailable. This video has been removed", "Video unavailable in your country"):
            self.assertFalse(is_youtube_access_error("https://youtu.be/863rTle6CKY", message, self.options))
        self.assertFalse(is_youtube_access_error("https://vimeo.com/123", "Video unavailable", self.options))
        self.assertFalse(is_youtube_access_error("https://youtu.be/863rTle6CKY", "Video unavailable", {}))

    def test_same_recovery_on_windows_and_macos(self):
        for system in ("win32", "darwin"):
            with self.subTest(platform=system), patch.object(sys, "platform", system):
                self.test_embedded_unavailability_retries_once_and_preserves_selection()

    def test_failed_retry_propagates_without_looping(self):
        with patch.object(downloader.yt_dlp, "YoutubeDL") as ydl:
            ydl.return_value.__enter__.return_value.extract_info.side_effect = RuntimeError("Video unavailable")
            with self.assertRaisesRegex(RuntimeError, "Video unavailable"):
                downloader.extract_info_resilient("https://youtu.be/863rTle6CKY", self.options)
        self.assertEqual(ydl.call_count, 2)

    def test_authenticated_retry_preserves_user_cookie_file(self):
        retry = youtube_access_fallback_options({**self.options, "cookiefile": "local-cookies.txt"})
        self.assertEqual(retry["cookiefile"], "local-cookies.txt")
        self.assertNotEqual(retry["extractor_args"]["youtube"]["player_client"], ["web_embedded"])
