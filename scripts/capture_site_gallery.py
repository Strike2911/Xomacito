"""Genera capturas reproducibles de la interfaz para la web de Xomacito.

Usa datos audiovisuales sintéticos y un perfil temporal: nunca publica rutas,
cuentas ni archivos personales del equipo creador.
"""

from __future__ import annotations

import json
import math
import os
import shutil
import struct
import subprocess
import sys
import tempfile
import time
import wave
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def _write_demo_audio(path: Path, seconds: float = 24.0) -> None:
    rate = 44_100
    with wave.open(str(path), "wb") as output:
        output.setnchannels(1)
        output.setsampwidth(2)
        output.setframerate(rate)
        frames = bytearray()
        for index in range(int(rate * seconds)):
            moment = index / rate
            section = int(moment // 3) % 4
            amplitude = (0.0, 0.28, 0.72, 0.42)[section]
            envelope = min(1.0, (moment % 3) * 5, (3 - moment % 3) * 5)
            sample = amplitude * envelope * (
                math.sin(2 * math.pi * 185 * moment)
                + 0.38 * math.sin(2 * math.pi * 370 * moment)
            )
            frames.extend(struct.pack("<h", int(max(-1, min(1, sample)) * 24_000)))
        output.writeframes(frames)


def _write_demo_video(path: Path, audio_path: Path, seconds: float = 24.0) -> bool:
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        return False
    result = subprocess.run(
        [
            ffmpeg, "-hide_banner", "-loglevel", "error", "-y",
            "-f", "lavfi", "-i", f"testsrc2=size=960x540:rate=24:duration={seconds}",
            "-i", str(audio_path), "-shortest", "-c:v", "libx264", "-preset", "ultrafast",
            "-pix_fmt", "yuv420p", "-c:a", "aac", str(path),
        ],
        capture_output=True,
        check=False,
    )
    return result.returncode == 0 and path.is_file()


def _pump(app, milliseconds: int = 250) -> None:
    deadline = time.monotonic() + milliseconds / 1000
    while time.monotonic() < deadline:
        app.processEvents()
        time.sleep(0.01)


def _wait(app, predicate, timeout: float = 12.0) -> bool:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        app.processEvents()
        if predicate():
            return True
        time.sleep(0.025)
    return bool(predicate())


def _capture(app, window, output: Path) -> None:
    _pump(app, 600)
    image = window.screen().grabWindow(int(window.winId())).toImage()
    if image.isNull() or not image.save(str(output), "PNG"):
        raise RuntimeError(f"No se pudo guardar la captura: {output}")
    print(output)


def main() -> int:
    from PySide6.QtCore import QObject, QMetaObject, QUrl
    from PySide6.QtGui import QGuiApplication
    from PySide6.QtQml import QQmlApplicationEngine
    from PySide6.QtWidgets import QApplication

    from src.ui.application import AppController, _qml_root

    destination = Path(sys.argv[1] if len(sys.argv) > 1 else ROOT / ".artifacts" / "site-gallery")
    destination.mkdir(parents=True, exist_ok=True)

    # QtMultimedia puede conservar un descriptor unos milisegundos después de
    # cerrar la ventana en Windows. Las capturas ya son autocontenidas, por lo
    # que ese retraso no debe convertir una ejecución correcta en un fallo.
    with tempfile.TemporaryDirectory(prefix="xomacito-gallery-", ignore_cleanup_errors=True) as temporary:
        temp_root = Path(temporary)
        profile = temp_root / "profile"
        library = temp_root / "Biblioteca Xomacito"
        sfx = library / "SFX"
        music = library / "Música"
        video = library / "Video"
        sfx.mkdir(parents=True)
        music.mkdir(parents=True)
        video.mkdir(parents=True)
        demo_audio = sfx / "Impacto cinematográfico.wav"
        ambient_audio = music / "Ambiente editorial.wav"
        _write_demo_audio(demo_audio)
        _write_demo_audio(ambient_audio, 18.0)
        demo_video = video / "Entrevista editorial.mp4"
        has_demo_video = _write_demo_video(demo_video, demo_audio)

        catalog = json.loads((ROOT / "assets" / "cat-collection" / "catalog.json").read_text(encoding="utf-8"))
        catalog_items = catalog if isinstance(catalog, list) else catalog.get("cats", [])
        unlocked = [str(item["id"]) for item in catalog_items if not item.get("exclusive")]
        strike_id = next(str(item["id"]) for item in catalog_items if item.get("name") == "GATO STRIKE")
        settings_dir = profile / "Xomacito"
        settings_dir.mkdir(parents=True)
        settings = {
            "appearance_mode": "Dark",
            "selected_theme_accent": "Strike",
            "theme_selection_explicit": True,
            "release_notice_seen_version": "4.0.17",
            "guided_tour_seen_version": "4.0.17",
            "social_onboarding_dismissed": True,
            "premiere_library_enabled": True,
            "premiere_library_path": str(library),
            "default_download_path": str(library),
            "batch_download_path": str(library),
            "image_output_path": str(library / "Resultados"),
            "platinum_collection_reward_seen_total": 9999,
            "cat_gacha": {
                "schema": 5,
                "downloadProgress": 7,
                "earnedRolls": 8,
                "totalDownloads": 286,
                "totalRolls": 74,
                "lastDailyRoll": "2026-08-25",
                "unlockedIds": unlocked,
                "equippedId": strike_id,
                "duplicates": {strike_id: 5},
                "rewardedSourceHashes": [],
            },
        }
        (settings_dir / "app_settings.json").write_text(
            json.dumps(settings, indent=2, ensure_ascii=False), encoding="utf-8"
        )
        os.environ["APPDATA"] = str(profile)
        os.environ.setdefault("QT_QUICK_BACKEND", "software")

        app = QApplication.instance() or QApplication(["xomacito-gallery"])
        QGuiApplication.setApplicationDisplayName("Xomacito 1.1")
        controller = AppController(app, ROOT, "1.1", "4.0.17")
        public_library_path = r"C:\Xomacito\Biblioteca"
        engine = QQmlApplicationEngine()
        context = engine.rootContext()
        context.setContextProperty("appController", controller)
        context.setContextProperty("theme", controller.theme)
        context.setContextProperty("downloadController", controller.download)
        context.setContextProperty("batchController", controller.batch)
        context.setContextProperty("mediaLibraryController", controller.media_library)
        context.setContextProperty("imageController", controller.image_studio)
        context.setContextProperty("settingsController", controller.config)
        context.setContextProperty("catController", controller.cats)
        context.setContextProperty("socialController", controller.social)
        context.setContextProperty("presetStore", controller.presets)
        context.setContextProperty("dialogBroker", controller.dialogs)
        qml = _qml_root(ROOT) / "Main.qml"
        engine.addImportPath(str(qml.parent))
        engine.load(QUrl.fromLocalFile(str(qml)))
        if not engine.rootObjects():
            raise RuntimeError("No se pudo cargar Main.qml")
        window = engine.rootObjects()[0]
        window.resize(1360, 820)
        window.show()
        _pump(app, 900)

        strike_avatar = ROOT / "assets" / "cat-collection" / "cat-3645f4659a5e-avatar.webp"
        controller.download._audio_choices = ["WAV · PCM 44.1 kHz · Estéreo"]
        controller.download.audioChoicesChanged.emit()
        controller.download._set_state(
            url="Archivo local · material de entrevista",
            title="Entrevista · corte editorial",
            mode="Video+Audio" if has_demo_video else "Solo Audio",
            localFile=str(demo_video if has_demo_video else demo_audio),
            thumbnailSource=QUrl.fromLocalFile(str(strike_avatar)).toString(),
            status="Enlace analizado · salida WAV",
            analyzed=True,
            hasAudio=True,
            hasVideo=has_demo_video,
            duration=24.0,
            selectedAudio="WAV · PCM 44.1 kHz · Estéreo",
            outputPath=public_library_path,
            effectiveOutputPath=public_library_path,
        )
        controller.download.setOption("startTime", "00:00:06")
        controller.download.setOption("endTime", "00:00:14")
        controller.download._refresh_trim_preview_source()
        controller.download.prepareTrimFilmstrip()
        controller.download.prepareWaveform()
        _wait(app, lambda: not controller.download.state["waveformBusy"], 15)
        _wait(app, lambda: not controller.download.state["trimFilmstripBusy"], 15)
        controller.setPage(0)
        _capture(app, window, destination / "descarga.png")

        popup = window.findChild(QObject, "downloadTrimPopup")
        if popup is None or not QMetaObject.invokeMethod(popup, "open"):
            raise RuntimeError("No se pudo abrir el recortador")
        _pump(app, 600)
        trimmer = window.findChild(QObject, "downloadWaveformTrimmer")
        if trimmer is None:
            raise RuntimeError("No se encontró el recortador")
        QMetaObject.invokeMethod(trimmer, "focusSelection")
        play_button = window.findChild(QObject, "trimPreviewPlayButton")
        if play_button is None or not QMetaObject.invokeMethod(play_button, "click"):
            raise RuntimeError("No se pudo iniciar el monitor del recortador")
        _pump(app, 1200)
        _capture(app, window, destination / "recortador.png")
        QMetaObject.invokeMethod(popup, "close")

        queue_rows = [
            {
                "index": index,
                "title": title,
                "thumbnail": QUrl.fromLocalFile(str(strike_avatar)).toString(),
                "selected": index < 4,
            }
            for index, title in enumerate([
                "Apertura del proyecto", "Entrevista principal", "Planos de recurso",
                "Música de transición", "Créditos y despedida", "Material adicional",
            ])
        ]
        selected_job = {
            "jobId": "demo-playlist", "title": "Proyecto editorial · 6 recursos",
            "status": "PENDING", "detail": "4 de 6 seleccionados", "progress": 0.0,
            "thumbnail": QUrl.fromLocalFile(str(strike_avatar)).toString(),
            "jobType": "PLAYLIST", "mode": "Video+Audio", "quality": "Mejor Calidad (Auto)",
            "recode": False, "preset": "Archivo - H.265 Normal", "keepOriginal": True,
            "downloadThumbnail": False, "embedAudioCover": False, "itemCount": 4,
            "destinationTag": "Proyecto", "outputFormat": "MP4 preferido · alternativa MKV",
        }
        controller.batch.jobs.replace([selected_job])
        controller.batch._selected = dict(selected_job)
        controller.batch._selected_playlist_entries = queue_rows
        controller.batch.playlist_entries_model.replace(queue_rows)
        controller.batch._set_state(
            selectedJobId="demo-playlist", playlistSelectionCount=4, playlistEntryCount=6,
            status="Cola preparada · 4 elementos seleccionados",
            outputPath=public_library_path, effectiveOutputPath=public_library_path,
        )
        controller.batch.selectedChanged.emit()
        controller.batch.selectedPlaylistEntriesChanged.emit()
        controller.setPage(1)
        _pump(app, 300)
        queue_page = window.findChild(QObject, "queuePage")
        queue_page.setProperty("expandedPlaylistJobId", "demo-playlist")
        _capture(app, window, destination / "cola.png")

        controller.setPage(2)
        _wait(app, lambda: not controller.media_library.state["busy"], 18)
        if has_demo_video:
            controller.media_library.selectPath(str(demo_video))
            _wait(app, lambda: not controller.media_library.state["filmstripBusy"], 15)
        else:
            _wait(app, lambda: not controller.media_library.state["waveformBusy"], 15)
        selected_media = dict(controller.media_library.state.get("selected") or {})
        if selected_media:
            selected_media["path"] = (
                public_library_path + r"\Video\Entrevista editorial.mp4"
                if has_demo_video
                else public_library_path + r"\Música\Ambiente editorial.wav"
            )
        controller.media_library._set_state(
            rootPath=public_library_path,
            clipOutputDir=public_library_path + r"\Recortes",
            selected=selected_media,
        )
        _capture(app, window, destination / "biblioteca.png")

        controller.image_studio._set_state(outputPath=public_library_path + r"\Resultados")
        page_files = [
            (3, "estudio.png"),
            (4, "coleccion.png"),
            (5, "comunidad.png"),
            (6, "configuracion.png"),
        ]
        for page, filename in page_files:
            controller.setPage(page)
            _capture(app, window, destination / filename)

        controller.shutdown()
        window.close()
        engine.deleteLater()
        _pump(app, 100)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
