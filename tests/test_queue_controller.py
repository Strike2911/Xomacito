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
assert job.config["recode_preset_name"] in controller.presets.audioPresets, job.config
assert batch.selected["outputFormat"] == "MP3", batch.selected
assert "mode" not in job.config

batch.setPlaylistSelectionCount(2)
assert job.config["selected_indices"] == [0, 1], job.config
assert batch.selected["itemCount"] == 2, batch.selected
assert [entry["selected"] for entry in batch.selectedPlaylistEntries] == [True, True, False]

batch.selectAllPlaylistEntries(False)
assert job.config["selected_indices"] == []
batch.selectAllPlaylistEntries(True)
assert job.config["selected_indices"] == [0, 1, 2]
assert batch.runtime.batch_tab.output_path_entry.get() == r"C:\Media\Musica"

batch.setValue("globalMode", "Solo Audio")
assert batch.state["globalPreset"] in controller.presets.audioPresets, batch.state
assert batch.state["globalPreset"] not in controller.presets.videoPresets, batch.state
batch.setValue("globalMode", "Video+Audio")
assert batch.state["globalPreset"] in controller.presets.videoPresets, batch.state

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

    def test_playlist_count_slider_can_be_dragged_and_updates_the_selection(self):
        script = r'''
from pathlib import Path
from PySide6.QtCore import QObject, QPoint, QPointF, Qt, QUrl
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtQuick import QQuickItem
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication
from src.core.batch_processor import Job
from src.ui.application import AppController

app = QApplication([])
root = Path.cwd()
controller = AppController(app, root, "4.0")
batch = controller.batch
entries = [
    {"id": f"item-{index}", "title": f"Elemento {index + 1}"}
    for index in range(12)
]
job = Job({"title": "Lista de prueba", "selected_indices": list(range(12))}, "PLAYLIST")
job.analysis_data = {"entries": entries}
job.total_items = len(entries)
batch._playlist_entries[job.job_id] = entries
batch.manager.add_job(job)
batch._replace_job_model(job, "PENDING", "Listo")
batch.selectJob(job.job_id)

engine = QQmlApplicationEngine()
context = engine.rootContext()
for name, value in (
    ("appController", controller), ("theme", controller.theme),
    ("downloadController", controller.download), ("batchController", controller.batch),
    ("imageController", controller.image_studio), ("mediaLibraryController", controller.media_library),
    ("settingsController", controller.config),
    ("catController", controller.cats), ("presetStore", controller.presets),
    ("dialogBroker", controller.dialogs),
):
    context.setContextProperty(name, value)
qml = f"""
import QtQuick
import QtQuick.Controls
import "src/ui/qml/pages"
ApplicationWindow {{
    visible: true
    width: 1180
    height: 700
    QueuePage {{ anchors.fill: parent }}
}}
"""
engine.loadData(qml.encode("utf-8"), QUrl.fromLocalFile(str(root) + "/"))
window = engine.rootObjects()[0]
page = window.findChild(QObject, "queuePage")
page.setProperty("expandedPlaylistJobId", job.job_id)
QTest.qWait(250)

slider = window.findChild(QQuickItem, "playlistCountSlider")
assert slider is not None and slider.property("visible") and slider.property("enabled"), slider
assert round(slider.property("value")) == 12, slider.property("value")
origin = slider.mapToItem(window.contentItem(), QPointF(0, 0))
y = round(origin.y() + slider.height() / 2)
start = QPoint(round(origin.x() + slider.width() - 10), y)
target = QPoint(round(origin.x() + slider.width() * 0.34), y)
QTest.mousePress(window, Qt.LeftButton, Qt.NoModifier, start)
QTest.mouseMove(window, target, 120)
QTest.mouseRelease(window, Qt.LeftButton, Qt.NoModifier, target)
QTest.qWait(180)

selected_count = batch.selected["itemCount"]
assert 3 <= selected_count <= 5, (selected_count, slider.property("value"), slider.width())
assert batch.state["playlistSelectionCount"] == selected_count
assert batch.state["playlistEntryCount"] == 12
assert len(job.config["selected_indices"]) == selected_count
assert job.config["selected_indices"] == list(range(selected_count))
controller.shutdown()
'''
        with tempfile.TemporaryDirectory() as appdata:
            environment = dict(os.environ)
            environment.update({"QT_QPA_PLATFORM": "offscreen", "APPDATA": appdata})
            result = subprocess.run(
                [sys.executable, "-c", script], cwd=ROOT, env=environment,
                capture_output=True, text=True, timeout=30, check=False,
            )
        self.assertEqual(result.returncode, 0, result.stderr or result.stdout)

    def test_queue_page_exposes_preview_tags_and_progressive_options(self):
        qml = (ROOT / "src/ui/qml/pages/QueuePage.qml").read_text(encoding="utf-8")
        self.assertIn("batchController.selectedPlaylistEntriesModel", qml)
        self.assertIn("setPlaylistEntrySelected", qml)
        self.assertIn("Etiqueta de destino", qml)
        self.assertIn("batchController.downloadTags", qml)
        self.assertIn("Opciones avanzadas", qml)
        self.assertIn("expandedPlaylistJobId", qml)
        self.assertIn("id: playlistPanel", qml)
        self.assertIn("source: thumbnail", qml)
        self.assertIn("entryThumbnail", qml)
        self.assertIn("id: jobThumbnail", qml)
        self.assertIn("id: playlistCountSlider", qml)
        self.assertIn('objectName: "playlistCountSlider"', qml)
        self.assertIn("ELEGIR CANTIDAD", qml)
        self.assertIn("setPlaylistSelectionCount", qml)
        self.assertIn("presetStore.audioPresets : presetStore.videoPresets", qml)
        self.assertIn("salida \" + outputFormat", qml)
        self.assertIn("id: advanced", qml)
        self.assertIn("reuseItems: true", qml)
        self.assertNotIn('id: playlistPreview', qml)
        self.assertNotIn("anchors.top: jobHeader.bottom", qml)
        self.assertNotIn("Configurar playlist completa", qml)


if __name__ == "__main__":
    unittest.main()
