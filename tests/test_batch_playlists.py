import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from src.core.batch_processor import Job, QueueManager, resolve_playlist_entry_url


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
                "entries": [
                    {
                        "webpage_url": "https://example.test/video/1",
                        "title": "Tema",
                    }
                ]
            }
            expected = Path(output) / "Mi Playlist" / "Tema.mp4"
            expected.parent.mkdir(parents=True)
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
            self.assertEqual(Path(job.final_filepath), expected.parent)
            self.assertTrue(any(event[1] == "COMPLETED" for event in events))


if __name__ == "__main__":
    unittest.main()
