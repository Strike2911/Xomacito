import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class QueueControllerTests(unittest.TestCase):
    def test_playlist_preview_selection_modes_and_shared_tags(self):
        script = r'''
from pathlib import Path
from PySide6.QtWidgets import QApplication
from src.core.batch_processor import Job
from src.ui.application import AppController

app = QApplication([])
controller = AppController(app, Path.cwd(), "3.0")
batch = controller.batch

controller.settings.update({
    "download_tags": [{"name": "Música", "folder": r"C:\Media\Musica", "color": "#84CC16"}],
    "selected_download_tag": "Música",
})
assert batch.downloadTags == ["Sin etiqueta", "Música"], batch.downloadTags
assert batch.state["selectedTag"] == "Música", batch.state
assert batch.state["effectiveOutputPath"] == r"C:\Media\Musica", batch.state
assert controller.download.state["selectedTag"] == "Música", controller.download.state

entries = [
    {"id": "uno", "title": "Canción uno", "thumbnail": "https://example.test/1.jpg"},
    {"id": "dos", "title": "Video dos", "thumbnail": "https://example.test/2.jpg"},
    {"id": "tres", "title": "Canción tres"},
]
job = Job({
    "title": "Mi playlist",
    "selected_indices": [0, 1, 2],
    "playlist_mode": "Video+Audio",
    "playlist_quality": "Mejor Calidad (Auto)",
    "output_path": batch.state["effectiveOutputPath"],
    "destination_tag": batch.state["selectedTag"],
}, "PLAYLIST")
job.analysis_data = {"entries": entries}
job.total_items = len(entries)
batch._playlist_entries[job.job_id] = entries
batch.manager.add_job(job)
batch._replace_job_model(job, "PENDING", "Listo")
batch.selectJob(job.job_id)

assert [entry["title"] for entry in batch.selectedPlaylistEntries] == [
    "Canción uno", "Video dos", "Canción tres",
]
assert all(entry["selected"] for entry in batch.selectedPlaylistEntries)

batch.setPlaylistEntrySelected(1, False)
assert job.config["selected_indices"] == [0, 2], job.config
assert batch.selected["itemCount"] == 2, batch.selected
assert batch.selectedPlaylistEntries[1]["selected"] is False

batch.setSelectedOption("mode", "Solo Audio")
batch.setSelectedOption("quality", "Solo Audio (Mejor)")
assert job.config["playlist_mode"] == "Solo Audio", job.config
assert job.config["playlist_quality"] == "Solo Audio (Mejor)", job.config
assert "mode" not in job.config

batch.selectAllPlaylistEntries(False)
assert job.config["selected_indices"] == []
batch.selectAllPlaylistEntries(True)
assert job.config["selected_indices"] == [0, 1, 2]
assert batch.runtime.batch_tab.output_path_entry.get() == r"C:\Media\Musica"

rewards = []
sources = []
batch.successfulDownload.connect(lambda count: rewards.append(count))
batch.gachaSourceCompleted.connect(lambda source: sources.append(source))
batch._prepare_reward_session()
job.completed_items = 3
batch._apply_queue_event(job.job_id, "COMPLETED", "Playlist completa", 1.0)
batch._apply_queue_event(job.job_id, "COMPLETED", "Playlist completa", 1.0)
assert rewards == [1], rewards
assert len(sources) == 1 and sources[0].startswith("queue:"), sources
controller.shutdown()
'''
        with tempfile.TemporaryDirectory() as appdata:
            environment = dict(os.environ)
            environment.update({"QT_QPA_PLATFORM": "offscreen", "APPDATA": appdata})
            result = subprocess.run(
                [sys.executable, "-c", script],
                cwd=ROOT,
                env=environment,
                capture_output=True,
                text=True,
                timeout=30,
                check=False,
            )
        self.assertEqual(result.returncode, 0, result.stderr or result.stdout)

    def test_queue_page_exposes_preview_tags_and_progressive_options(self):
        qml = (ROOT / "src/ui/qml/pages/QueuePage.qml").read_text(encoding="utf-8")
        self.assertIn("batchController.selectedPlaylistEntries", qml)
        self.assertIn("setPlaylistEntrySelected", qml)
        self.assertIn("Etiqueta de destino", qml)
        self.assertIn("batchController.downloadTags", qml)
        self.assertIn("Opciones avanzadas", qml)
        self.assertIn("expandedPlaylistJobId", qml)
        self.assertIn("id: playlistPanel", qml)
        self.assertIn("modelData.thumbnail", qml)
        self.assertIn("entryThumbnail", qml)
        self.assertIn("id: advanced", qml)
        self.assertIn("reuseItems: true", qml)
        self.assertNotIn('id: playlistPreview', qml)
        self.assertNotIn("anchors.top: jobHeader.bottom", qml)
        self.assertNotIn("Configurar playlist completa", qml)


if __name__ == "__main__":
    unittest.main()
