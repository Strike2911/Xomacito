import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from src.core.processor import FFmpegProcessor
from src.ui.download_controller import DownloadController
from src.ui.filmstrip import render_filmstrip
from src.ui.media_library_controller import MediaLibraryController
from src.ui.waveform import render_waveform


ROOT = Path(__file__).resolve().parents[1]


class MemorySettings:
    def __init__(self, root: Path):
        self.values = {"premiere_library_path": str(root)}

    def get(self, key, default=None):
        return self.values.get(key, default)

    def set(self, key, value):
        self.values[key] = value


class IdlePool:
    def submit(self, *_args, **_kwargs):
        return None


class ImmediatePool:
    def submit(self, function, *args, on_result=None, on_error=None, **_kwargs):
        try:
            result = function(*args)
        except Exception as exc:  # pragma: no cover - la aserción reporta el detalle
            if on_error:
                on_error(str(exc), repr(exc))
        else:
            if on_result:
                on_result(result)
        return None


class MediaLibraryTests(unittest.TestCase):
    def test_download_filmstrip_result_uses_the_same_revision_key(self):
        captured = {}
        fake_controller = SimpleNamespace(
            _current_filmstrip_key=lambda: "video-activo",
            _set_state=lambda **values: captured.update(values),
        )

        DownloadController._download_filmstrip_ready(
            fake_controller,
            "video-activo|filmstrip-v4-64",
            r"C:\cache\filmstrip.png",
        )

        self.assertTrue(captured["trimFilmstripSource"].startswith("file:"))
        self.assertFalse(captured["trimFilmstripBusy"])
        self.assertEqual(captured["trimFilmstripError"], "")

    def test_remote_waveform_recovers_through_a_temporary_ytdlp_download(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "waveform.png"
            render_calls = []

            def fake_render(_ffmpeg, source, destination, _headers=None):
                render_calls.append(str(source))
                if str(source) == "https://media.invalid/expired":
                    raise RuntimeError("HTTP 403")
                Path(destination).write_bytes(b"PNG" * 200)
                return str(destination)

            def fake_extract(_url, options, download=False):
                self.assertTrue(download)
                preview = Path(options["outtmpl"].replace("%(ext)s", "m4a"))
                preview.write_bytes(b"audio-temporal")
                return {"filepath": str(preview)}

            fake_controller = SimpleNamespace(
                ffmpeg=SimpleNamespace(ffmpeg_path="ffmpeg-test"),
            )
            with (
                patch("src.ui.download_controller.render_waveform", side_effect=fake_render),
                patch("src.ui.download_controller.extract_info_resilient", side_effect=fake_extract),
            ):
                output = DownloadController._remote_waveform_worker(
                    fake_controller,
                    "https://example.test/watch?v=1",
                    "https://media.invalid/expired",
                    "140",
                    target,
                    {},
                    {},
                    False,
                )
            self.assertEqual(Path(output), target)
            self.assertTrue(target.is_file())
            self.assertEqual(len(render_calls), 2)
            self.assertTrue(render_calls[1].endswith("audio.m4a"))

    def test_library_rows_are_compact_groups_that_can_collapse(self):
        with tempfile.TemporaryDirectory() as directory:
            library = Path(directory)
            nested = library / "Proyecto" / "Audio"
            nested.mkdir(parents=True)
            controller = MediaLibraryController(
                ROOT, MemorySettings(library), IdlePool(), FFmpegProcessor("test"),
            )
            rows = [
                {role: "" for role in controller.ROLES},
                {role: "" for role in controller.ROLES},
            ]
            rows[0].update({"path": str(nested / "uno.mp3"), "name": "uno.mp3", "kind": "Audio"})
            rows[1].update({"path": str(nested / "dos.mp3"), "name": "dos.mp3", "kind": "Audio"})
            controller.items.replace(rows)
            controller._rebuild_library_rows()
            self.assertEqual(controller.library_rows.count(), 3)
            grouped = library / "Proyecto"
            self.assertEqual(controller.library_rows.item(0)["folderPath"], str(grouped))
            self.assertRegex(controller.library_rows.item(0)["folderColor"], r"^#[0-9A-F]{6}$")
            self.assertEqual(
                controller.library_rows.item(0)["folderColor"],
                controller.library_rows.item(1)["folderColor"],
            )
            controller.toggleFolder(str(grouped))
            self.assertEqual(controller.library_rows.count(), 1)
            self.assertFalse(controller.library_rows.item(0)["expanded"])

    def test_folder_can_be_hidden_as_one_group_without_deleting_files(self):
        with tempfile.TemporaryDirectory() as directory:
            library = Path(directory)
            imported = library / "Importados" / "Proyecto grande"
            nested = imported / "Audio" / "SFX"
            nested.mkdir(parents=True)
            controller = MediaLibraryController(
                ROOT, MemorySettings(library), IdlePool(), FFmpegProcessor("test"),
            )
            rows = [{role: "" for role in controller.ROLES} for _ in range(2)]
            rows[0].update({"path": str(nested / "uno.wav"), "name": "uno.wav", "kind": "Audio"})
            rows[1].update({"path": str(imported / "Video" / "dos.mp4"), "name": "dos.mp4", "kind": "Video"})
            controller.items.replace(rows)
            controller._rebuild_library_rows()
            self.assertEqual(controller.library_rows.item(0)["folderPath"], str(imported))
            self.assertTrue(controller.library_rows.item(0)["canRemove"])
            controller._state["busy"] = False
            controller.removeFolder(str(imported))
            self.assertEqual(controller.library_rows.count(), 0)
            self.assertTrue(imported.is_dir())
            self.assertEqual(controller.state["hiddenFolderCount"], 1)
            controller.restoreHiddenFolders()
            self.assertEqual(controller.library_rows.count(), 3)

    def test_editorial_filters_search_and_favorites_keep_files_intact(self):
        with tempfile.TemporaryDirectory() as directory:
            library = Path(directory)
            sfx = library / "Audio" / "SFX"
            green = library / "Video" / "Green Screen"
            sfx.mkdir(parents=True)
            green.mkdir(parents=True)
            impact = sfx / "impacto.wav"
            impact.write_bytes(b"audio-de-prueba")
            controller = MediaLibraryController(
                ROOT, MemorySettings(library), IdlePool(), FFmpegProcessor("test"),
            )
            rows = [{role: "" for role in controller.ROLES} for _ in range(3)]
            rows[0].update({
                "path": str(impact), "name": "impacto.wav", "kind": "Audio",
                "category": "SFX", "searchText": "impacto audio sfx", "isFavorite": False,
            })
            rows[1].update({
                "path": str(green / "humo.mp4"), "name": "humo.mp4", "kind": "Video",
                "category": "Green screen", "searchText": "humo video green screen", "isFavorite": False,
            })
            rows[2].update({
                "path": str(library / "portada.png"), "name": "portada.png", "kind": "Imagen",
                "category": "Imágenes", "searchText": "portada imagen", "isFavorite": False,
            })
            controller.items.replace(rows)
            controller._rebuild_library_rows()
            controller.setCategoryFilter("Green screen")
            self.assertEqual(controller.state["visibleCount"], 1)
            controller.setCategoryFilter("Todos")
            controller.setSearchText("impacto")
            self.assertEqual(controller.state["visibleCount"], 1)
            controller.toggleFavorite(str(impact))
            controller.setSearchText("")
            controller.setCategoryFilter("Favoritos")
            self.assertEqual(controller.state["visibleCount"], 1)
            self.assertEqual(controller.library_rows.item(1)["name"], "impacto.wav")
            self.assertTrue(impact.is_file())
            self.assertEqual(impact.read_bytes(), b"audio-de-prueba")

    def test_premiere_panel_declares_narrow_permission_and_real_timeline_actions(self):
        panel = ROOT / "premiere-panel"
        manifest = json.loads((panel / "manifest.json").read_text(encoding="utf-8"))
        script = (panel / "index.js").read_text(encoding="utf-8")
        self.assertEqual(manifest["manifestVersion"], 5)
        self.assertEqual(manifest["host"], {"app": "premierepro", "minVersion": "25.6.0"})
        self.assertEqual(manifest["requiredPermissions"]["localFileSystem"], "request")
        self.assertNotIn("network", manifest["requiredPermissions"])
        self.assertIn("createPersistentToken", script)
        self.assertIn("project.importFiles", script)
        self.assertIn("createInsertProjectItemAction", script)
        self.assertIn("sequence.getPlayerPosition", script)
        self.assertIn("executeTransaction", script)
        self.assertIn('IMPORT_BIN_NAME = "Xomacito Import"', script)
        self.assertIn("parent.createBinAction(name, false)", script)
        self.assertIn("project.importFiles([mediaPath], true, targetBin, false)", script)
        self.assertIn('AUTO_SYNC_KEY = "xomacito-auto-sync-v1"', script)
        self.assertIn("setInterval(() => syncProject(false), SYNC_INTERVAL_MS)", script)
        self.assertIn("async function stableItems(items)", script)
        self.assertIn("if (count >= 2) stable.push(item)", script)
        self.assertIn("async function ensureCategoryBin", script)
        self.assertIn('return "Recortes"', script)
        self.assertIn('return "Imágenes"', script)
        html = (panel / "index.html").read_text(encoding="utf-8")
        styles = (panel / "styles.css").read_text(encoding="utf-8")
        self.assertIn("Conectar proyecto abierto", html)
        self.assertIn("No se crearán duplicados", html)
        self.assertIn('data-kind="Audio"', html)
        self.assertIn("@media (max-width: 310px)", styles)

    def test_library_page_is_intentionally_empty(self):
        qml = (ROOT / "src/ui/qml/pages/MediaLibraryPage.qml").read_text(encoding="utf-8")
        self.assertEqual(qml.strip(), "import QtQuick\n\nItem {\n}")

    def test_waveform_renderer_creates_a_cached_editorial_preview(self):
        ffmpeg_path = ROOT / "bin" / "ffmpeg" / ("ffmpeg.exe" if os.name == "nt" else "ffmpeg")
        if not ffmpeg_path.is_file():
            self.skipTest("FFmpeg portable no disponible")
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            source = folder / "silencio-y-tono.wav"
            target = folder / "onda.png"
            created = subprocess.run(
                [
                    str(ffmpeg_path), "-y", "-f", "lavfi", "-i",
                    "aevalsrc=if(lt(t\\,1)\\,0\\,0.45*sin(2*PI*440*t)):s=48000:d=2",
                    str(source),
                ],
                capture_output=True, timeout=30, check=False,
            )
            self.assertEqual(created.returncode, 0, created.stderr.decode(errors="ignore"))
            output = Path(render_waveform(str(ffmpeg_path), str(source), target))
            self.assertEqual(output, target)
            self.assertTrue(output.is_file())
            self.assertGreater(output.stat().st_size, 256)

    def test_filmstrip_renderer_samples_the_whole_video_as_a_horizontal_gallery(self):
        ffmpeg_path = ROOT / "bin" / "ffmpeg" / ("ffmpeg.exe" if os.name == "nt" else "ffmpeg")
        if not ffmpeg_path.is_file():
            self.skipTest("FFmpeg portable no disponible")
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            source = folder / "galeria.mp4"
            target = folder / "filmstrip.png"
            created = subprocess.run(
                [
                    str(ffmpeg_path), "-y", "-f", "lavfi", "-i",
                    "testsrc2=size=320x180:rate=12:duration=3",
                    "-c:v", "libx264", "-pix_fmt", "yuv420p", str(source),
                ],
                capture_output=True, timeout=30, check=False,
            )
            self.assertEqual(created.returncode, 0, created.stderr.decode(errors="ignore"))
            output = Path(render_filmstrip(str(ffmpeg_path), str(source), target, 3.0))
            self.assertEqual(output, target)
            self.assertGreater(output.stat().st_size, 256)
            from PIL import Image
            with Image.open(output) as image:
                self.assertGreater(image.width, 7000)
                self.assertGreater(image.width, image.height * 50)

    def test_accurate_clip_is_created_as_premiere_ready_mp4_and_original_survives(self):
        ffmpeg_path = ROOT / "bin" / "ffmpeg" / ("ffmpeg.exe" if os.name == "nt" else "ffmpeg")
        if not ffmpeg_path.is_file():
            self.skipTest("FFmpeg portable no disponible")
        with tempfile.TemporaryDirectory() as directory:
            library = Path(directory)
            source = library / "original.mp4"
            result = subprocess.run(
                [
                    str(ffmpeg_path), "-y", "-f", "lavfi", "-i", "testsrc2=size=320x180:rate=30",
                    "-f", "lavfi", "-i", "sine=frequency=440:sample_rate=48000", "-t", "2",
                    "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", str(source),
                ],
                capture_output=True, timeout=30, check=False,
            )
            self.assertEqual(result.returncode, 0, result.stderr.decode(errors="ignore"))
            original_size = source.stat().st_size
            controller = MediaLibraryController(
                ROOT, MemorySettings(library), IdlePool(), FFmpegProcessor("test"),
            )
            rows = controller._scan_worker()
            original = next(row for row in rows if row["name"] == source.name)
            self.assertEqual(original["dimensions"], "320 × 180")
            self.assertEqual(original["extension"], "MP4")
            self.assertGreater(original["sizeBytes"], 0)
            self.assertIn("bytes", original["sizeBytesLabel"])
            self.assertIn("QuickTime", original["formatLongName"])
            self.assertEqual(original["frameRate"], "30 fps")
            self.assertEqual(original["pixelFormat"], "YUV420P")
            self.assertEqual(original["sampleRate"], "48 000 Hz")
            clip = Path(controller._clip_worker(original, 0.35, 1.25, "Video + audio"))
            self.assertTrue(clip.is_file())
            self.assertEqual(clip.suffix.lower(), ".mp4")
            self.assertTrue(source.is_file())
            self.assertEqual(source.stat().st_size, original_size)
            info = controller.ffmpeg.get_local_media_info(str(clip))
            streams = info.get("streams") or []
            self.assertTrue(any(stream.get("codec_name") == "h264" for stream in streams))
            self.assertTrue(any(stream.get("codec_name") == "aac" for stream in streams))
            duration = float((info.get("format") or {}).get("duration") or 0)
            self.assertGreater(duration, 0.75)
            self.assertLess(duration, 1.1)
            manifest = json.loads((library / ".xomacito-library.json").read_text(encoding="utf-8"))
            self.assertEqual(manifest["library"], "Xomacito")

    def test_create_clip_action_reports_the_exact_output_folder(self):
        ffmpeg_path = ROOT / "bin" / "ffmpeg" / ("ffmpeg.exe" if os.name == "nt" else "ffmpeg")
        if not ffmpeg_path.is_file():
            self.skipTest("FFmpeg portable no disponible")
        with tempfile.TemporaryDirectory() as directory:
            library = Path(directory)
            source = library / "dialogo.wav"
            created = subprocess.run(
                [str(ffmpeg_path), "-y", "-f", "lavfi", "-i", "sine=frequency=440:duration=2", str(source)],
                capture_output=True, timeout=30, check=False,
            )
            self.assertEqual(created.returncode, 0, created.stderr.decode(errors="ignore"))
            controller = MediaLibraryController(
                ROOT, MemorySettings(library), ImmediatePool(), FFmpegProcessor("test"),
            )
            rows = controller._scan_worker()
            controller.items.replace(rows)
            controller.select(0)
            controller.setValue("clipIn", 0.25)
            controller.setValue("clipOut", 1.25)
            notices = []
            controller.notificationRequested.connect(lambda kind, title, message: notices.append((kind, title, message)))
            controller.createClip()
            output = Path(controller.state["lastClipPath"])
            self.assertTrue(output.is_file())
            self.assertEqual(output.parent, library / "Recortes")
            self.assertIn(str(output.parent), controller.state["status"])
            self.assertTrue(any(str(output.parent) in message for _kind, _title, message in notices))

    def test_dropped_folder_is_copied_non_destructively_into_imports(self):
        with tempfile.TemporaryDirectory() as directory:
            workspace = Path(directory)
            library = workspace / "library"
            incoming = workspace / "material-del-editor"
            incoming.mkdir(parents=True)
            source = incoming / "audio.wav"
            source.write_bytes(b"RIFF-datos-de-prueba")
            ignored = incoming / "notas.txt"
            ignored.write_text("no copiar", encoding="utf-8")
            controller = MediaLibraryController(
                ROOT, MemorySettings(library), IdlePool(), FFmpegProcessor("test"),
            )
            count = controller._import_paths_worker([incoming])
            copied = list((library / "Importados").rglob("audio.wav"))
            self.assertEqual(count, 1)
            self.assertEqual(len(copied), 1)
            self.assertEqual(copied[0].read_bytes(), source.read_bytes())
            self.assertTrue(source.is_file())
            self.assertFalse(list((library / "Importados").rglob("notas.txt")))

    def test_empty_library_qml_keeps_user_media_backend_intact(self):
        script = r'''
import os
import subprocess
import tempfile
from pathlib import Path
from PySide6.QtCore import QObject, QUrl
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtQuick import QQuickItem
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication
from src.ui.application import AppController
from src.ui.settings_store import SettingsStore

app = QApplication([])
root = Path.cwd()
library = Path(os.environ["APPDATA"]) / "library"
library.mkdir(parents=True, exist_ok=True)
settings = SettingsStore()
settings.set("premiere_library_path", str(library))
ffmpeg = root / "bin" / "ffmpeg" / ("ffmpeg.exe" if os.name == "nt" else "ffmpeg")
source = library / "clip-de-prueba.mp4"
created = subprocess.run([
    str(ffmpeg), "-y", "-f", "lavfi", "-i", "testsrc2=size=320x180:rate=24",
    "-f", "lavfi", "-i", "sine=frequency=330:sample_rate=48000", "-t", "2",
    "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", str(source),
], capture_output=True, timeout=30)
assert created.returncode == 0, created.stderr
controller = AppController(app, root, "4.0")
engine = QQmlApplicationEngine()
context = engine.rootContext()
for name, value in (
    ("appController", controller), ("theme", controller.theme),
    ("downloadController", controller.download), ("batchController", controller.batch),
    ("mediaLibraryController", controller.media_library), ("imageController", controller.image_studio),
    ("settingsController", controller.config), ("catController", controller.cats),
    ("socialController", controller.social), ("presetStore", controller.presets),
    ("dialogBroker", controller.dialogs),
):
    context.setContextProperty(name, value)
engine.load(QUrl.fromLocalFile(str(root / "src/ui/qml/Main.qml")))
window = engine.rootObjects()[0]
window.setProperty("width", 1280)
window.setProperty("height", 760)
controller.setPage(2)
for _ in range(40):
    QTest.qWait(100)
    if controller.media_library.state["itemCount"]:
        break
assert controller.media_library.state["itemCount"] >= 1
media_list = window.findChild(QQuickItem, "premiereMediaList")
clip_range = window.findChild(QObject, "mediaClipRange")
assert media_list is None
assert clip_range is None
assert controller.media_library.state["selected"]["videoCodec"] == "H264"
assert controller.media_library.state["selected"]["sizeBytes"] > 0
assert "bytes" in controller.media_library.state["selected"]["sizeBytesLabel"]
window.setProperty("width", 960)
window.setProperty("height", 720)
QTest.qWait(250)
assert bool(window.property("visible"))
assert int(window.property("width")) == 960
controller.shutdown()
'''
        with tempfile.TemporaryDirectory() as appdata:
            environment = dict(os.environ)
            environment.update({"QT_QPA_PLATFORM": "offscreen", "APPDATA": appdata})
            result = subprocess.run(
                [str(ROOT / ".tools/python311full/python.exe"), "-c", script],
                cwd=ROOT, env=environment, capture_output=True, text=True, timeout=45, check=False,
            )
        self.assertEqual(result.returncode, 0, result.stderr or result.stdout)


if __name__ == "__main__":
    unittest.main()
