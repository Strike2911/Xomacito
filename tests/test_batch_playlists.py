import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from src.core.batch_processor import (
    Job,
    QueueManager,
    build_batch_analysis_options,
    playlist_audio_postprocessors,
    resolve_playlist_entry_url,
)


class _Value:
    def __init__(self, value):
        self.value = value

    def get(self):
        return self.value


def _runtime(output_path: str):
    batch_tab = SimpleNamespace(
        thumbnail_mode_var=_Value("normal"),
        conflict_policy_menu=_Value("Renombrar"),
        output_path_entry=_Value(output_path),
        auto_send_to_it_checkbox=_Value(0),
    )
    return SimpleNamespace(
        batch_tab=batch_tab,
        single_tab=SimpleNamespace(sanitize_filename=lambda value: str(value).replace("/", "_")),
        cookies_mode_saved="No usar",
        cookies_path="",
        selected_browser_saved="chrome",
        browser_profile_saved="",
    )


class PlaylistDownloadTests(unittest.TestCase):
    def test_full_playlist_analysis_is_progressive_even_without_fast_toggle(self):
        options = build_batch_analysis_options(
            "https://www.youtube.com/watch?v=abc123XYZ09&list=PL123",
            playlist_enabled=True,
            fast_requested=False,
        )
        self.assertEqual(options["extract_flat"], "in_playlist")
        self.assertNotIn("lazy_playlist", options)
        self.assertFalse(options["noplaylist"])

    def test_fast_playlist_analysis_keeps_lazy_playlist_hint(self):
        options = build_batch_analysis_options(
            "https://www.youtube.com/playlist?list=PL123",
            playlist_enabled=True,
            fast_requested=True,
        )
        self.assertEqual(options["extract_flat"], "in_playlist")
        self.assertTrue(options["lazy_playlist"])

    def test_playlist_audio_is_always_extracted_to_mp3(self):
        postprocessors = playlist_audio_postprocessors()
        self.assertEqual(postprocessors[0]["key"], "FFmpegExtractAudio")
        self.assertEqual(postprocessors[0]["preferredcodec"], "mp3")
        self.assertEqual(postprocessors[0]["preferredquality"], "192")

        high = playlist_audio_postprocessors("mp3", "320")
        aac = playlist_audio_postprocessors("m4a", "256")
        opus = playlist_audio_postprocessors("opus", "0")
        self.assertEqual(high[0]["preferredquality"], "320")
        self.assertEqual(aac[0]["preferredcodec"], "m4a")
        self.assertEqual(opus[0]["preferredcodec"], "opus")

    def test_audio_quality_options_select_real_audio_outputs(self):
        manager = QueueManager(_runtime("."), lambda *_args: None)
        cases = {
            "MP3 · 320 kbps": ("mp3", "320"),
            "MP3 · 192 kbps": ("mp3", "192"),
            "M4A · AAC": ("m4a", "256"),
            "OPUS · Original": ("opus", "0"),
        }
        for label, expected in cases.items():
            with self.subTest(label=label):
                options = {}
                manager._apply_playlist_quality(options, "Solo Audio", label)
                self.assertEqual(
                    (options["audio_output_codec"], options["audio_output_quality"]),
                    expected,
                )
                self.assertTrue(options["format_selector"].startswith("bestaudio"))

    def test_playlist_video_prefers_mp4_and_announces_mkv_fallback(self):
        with tempfile.TemporaryDirectory() as output:
            manager = QueueManager(_runtime(output), lambda *_args: None)
            options = {}
            manager._apply_playlist_quality(options, "Video+Audio", "Mejor Calidad (Auto)")

        self.assertTrue(options["format_selector"].startswith("bestvideo[ext=mp4]"))
        self.assertIn("bestvideo+bestaudio/best", options["format_selector"])
        self.assertEqual(options["merge_output_format"], "mp4/mkv")

    def test_flat_youtube_entry_is_rebuilt_as_a_watch_url(self):
        entry = {"id": "abc123XYZ09", "url": "abc123XYZ09", "title": "Tema"}
        playlist = {"extractor_key": "YoutubeTab"}
        self.assertEqual(
            resolve_playlist_entry_url(entry, playlist),
            "https://www.youtube.com/watch?v=abc123XYZ09",
        )

    def test_empty_playlist_result_is_failed_and_empty_folder_is_removed(self):
        with tempfile.TemporaryDirectory() as output:
            events = []
            manager = QueueManager(_runtime(output), lambda *args: events.append(args))
            manager.pause_event.clear()
            job = Job(
                {
                    "title": "Mi Playlist",
                    "selected_indices": [0],
                    "playlist_mode": "Video+Audio",
                    "playlist_quality": "Mejor Calidad (Auto)",
                },
                job_type="PLAYLIST",
            )
            job.analysis_data = {
                "extractor_key": "YoutubeTab",
                "entries": [{"id": "abc123XYZ09", "url": "abc123XYZ09", "title": "Tema"}],
            }

            with patch.object(
                manager,
                "_download_single_video_in_playlist",
                side_effect=RuntimeError("fallo simulado"),
            ):
                with self.assertRaisesRegex(RuntimeError, "No se descargó ningún elemento"):
                    manager._execute_playlist_job(job)

            self.assertEqual(job.completed_items, 0)
            self.assertEqual(job.failed_items, 1)
            self.assertFalse((Path(output) / "Mi Playlist").exists())
            self.assertFalse(any(event[1] == "COMPLETED" for event in events))

    def test_playlist_is_completed_only_after_a_real_file_exists(self):
        with tempfile.TemporaryDirectory() as output:
            events = []
            old_default = Path(output) / "destino-anterior"
            chosen = Path(output) / "Horror music"
            chosen.mkdir()
            manager = QueueManager(_runtime(str(old_default)), lambda *args: events.append(args))
            manager.pause_event.clear()
            job = Job(
                {
                    "title": "Mi Playlist",
                    "selected_indices": [0],
                    "playlist_mode": "Video+Audio",
                    "playlist_quality": "Mejor Calidad (Auto)",
                    "output_path": str(chosen),
                },
                job_type="PLAYLIST",
            )
            job.analysis_data = {
                "entries": [
                    {
                        "webpage_url": "https://example.test/video/1",
                        "title": "Tema",
                    }
                ]
            }
            expected = chosen / "Tema.mp4"
            expected.write_bytes(b"video")

            with patch.object(
                manager,
                "_download_single_video_in_playlist",
                return_value=str(expected),
            ):
                manager._execute_playlist_job(job)

            self.assertEqual(job.status, "COMPLETED")
            self.assertEqual(job.completed_items, 1)
            self.assertEqual(job.failed_items, 0)
            self.assertEqual(Path(job.final_filepath), chosen)
            self.assertFalse((chosen / "Mi Playlist").exists())
            self.assertFalse(old_default.exists())
            self.assertTrue(any(event[1] == "COMPLETED" for event in events))


if __name__ == "__main__":
    unittest.main()
