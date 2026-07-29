import tempfile
import unittest
from pathlib import Path

from src.core.file_naming import next_available_media_stem, next_available_path


class FileNamingTests(unittest.TestCase):
    def test_media_stem_checks_every_extension_and_increments_parentheses(self):
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            (folder / "jorge origen.mp4").touch()
            (folder / "jorge origen (1).webm").touch()

            self.assertEqual(
                next_available_media_stem(folder, "jorge origen"),
                "jorge origen (2)",
            )

    def test_available_path_uses_windows_copy_style(self):
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            desired = folder / "cancion.mp3"
            desired.touch()
            (folder / "cancion (1).mp3").touch()

            self.assertEqual(
                next_available_path(desired),
                folder / "cancion (2).mp3",
            )


if __name__ == "__main__":
    unittest.main()
