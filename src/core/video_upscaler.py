"""
video_upscaler.py
Modulo de reescalado de video usando motores NCNN (Real-ESRGAN, Waifu2x, RealSR, SRMD).
Flujo: extraer frames (FFmpeg) -> reescalar carpeta (NCNN) -> reensamblar + audio (FFmpeg).
"""

import os
import json
import shutil
import tempfile
import subprocess
import multiprocessing
import math
import time
import threading
from pathlib import Path

from src.core.constants import (
    WAIFU2X_MODELS,
    SRMD_MODELS,
    UPSCALING_TOOLS,
)
from src.core.exceptions import UserCancelledError
from main import UPSCALING_DIR


# ─── Ruta raiz de los binarios ───────────────────────────────────────────────
_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
BIN_DIR = os.path.normpath(os.path.join(_THIS_DIR, "..", "..", "bin"))

# ─── Mapeo de contenedores a codecs video/audio seguros ──────────────────────
CONTAINER_CODECS = {
    ".mp4":  {"vcodec": "libx264",      "acodec": "aac",          "pix_fmt": "yuv420p"},
    ".mkv":  {"vcodec": "libx264",      "acodec": "copy",         "pix_fmt": "yuv420p"},
    ".mov":  {"vcodec": "libx264",      "acodec": "aac",          "pix_fmt": "yuv420p"},
    ".avi":  {"vcodec": "libx264",      "acodec": "libmp3lame",   "pix_fmt": "yuv420p"},
    ".gif":  {"vcodec": "gif",          "acodec": None,           "pix_fmt": "rgb24"}, # GIF no lleva audio
}


class VideoUpscaler:
    """
    Motor de reescalado de video usando ejecutables NCNN.
    """

    def __init__(self, ffmpeg_dir: str, upscaling_dir: str = None, cancellation_event=None, progress_callback=None):
        """
        Args:
            ffmpeg_dir: Carpeta donde vive ffmpeg.exe / ffprobe.exe
            upscaling_dir: Ruta base de los modelos de upscaling (opcional)
            cancellation_event: threading.Event para cancelacion externa
            progress_callback: callable(pct: float, msg: str)
        """
        self.ffmpeg_dir = ffmpeg_dir
        self.ffmpeg_exe = os.path.join(ffmpeg_dir, "ffmpeg.exe")
        self.ffprobe_exe = os.path.join(ffmpeg_dir, "ffprobe.exe")
        self.cancellation_event = cancellation_event
        self.progress_callback = progress_callback or (lambda p, m: None)
        
        if upscaling_dir:
            self.models_root = upscaling_dir
        else:
            self.models_root = UPSCALING_DIR

    # ─── Helpers ────────────────────────────────────────────────────────────

    def _check_dependencies(self):
        """Verifica que FFmpeg y FFprobe existan."""
        for exe in [self.ffmpeg_exe, self.ffprobe_exe]:
            if not os.path.exists(exe):
                raise Exception(f"Dependencia no encontrada: {exe}. Por favor, reinstala FFmpeg.")

    def _check_cancel(self, proc=None):
        if self.cancellation_event and self.cancellation_event.is_set():
            if proc:
                try:
                    print(f"DEBUG [VideoUpscaler] Cancelación detectada. Terminando proceso {proc.pid}...")
                    proc.kill()
                    proc.wait(timeout=2.0)
                except:
                    pass
            raise UserCancelledError("Proceso cancelado por el usuario.")

    def _report(self, pct: float, msg: str):
        self.progress_callback(pct, msg)

    def _creationflags(self):
        return subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0

    def _thread_args(self) -> str:
        """
        Calcula los hilos de carga:proceso:guardado.
        En video somos más conservadores que en imagen para evitar crashes de GPU por saturación.
        """
        n = multiprocessing.cpu_count()
        if n >= 12:
            return "1:2:1" # Máximo balanceado para video
        elif n >= 6:
            return "1:1:1"
        return "1:1:1"

    # ─── Paso 1: Obtener info del video original ─────────────────────────────

    def _get_video_info(self, input_path: str) -> dict:
        """Usa ffprobe para obtener FPS, extension, codec de audio."""
        self._report(2, "Analizando video original...")
        cmd = [
            self.ffprobe_exe,
            "-v", "quiet",
            "-print_format", "json",
            "-show_streams", "-show_format",
            input_path
        ]
        try:
            result = subprocess.run(
                cmd,
                capture_output=True, text=True,
                creationflags=self._creationflags()
            )
            data = json.loads(result.stdout)
        except Exception as e:
            print(f"ADVERTENCIA: ffprobe fallo ({e}), usando valores por defecto.")
            return {"fps": "30", "ext": os.path.splitext(input_path)[1].lower(), "has_audio": False,
                    "duration": 0.0, "width": 0, "height": 0, "estimated_frames": 0}

        fps = "30"
        has_audio = False
        width = 0
        height = 0

        for stream in data.get("streams", []):
            codec_type = stream.get("codec_type", "")
            if codec_type == "video":
                width = int(stream.get("width") or 0)
                height = int(stream.get("height") or 0)
                r_fps = stream.get("r_frame_rate", "30/1")
                try:
                    num, den = r_fps.split("/")
                    fps = str(round(int(num) / int(den), 3))
                except Exception:
                    fps = "30"
            elif codec_type == "audio":
                has_audio = True

        ext = os.path.splitext(input_path)[1].lower()
        try:
            duration = float((data.get("format") or {}).get("duration") or 0)
        except (TypeError, ValueError):
            duration = 0.0
        try:
            estimated_frames = max(0, round(duration * float(fps)))
        except (TypeError, ValueError):
            estimated_frames = 0
        return {
            "fps": fps, "ext": ext, "has_audio": has_audio,
            "duration": duration, "width": width, "height": height,
            "estimated_frames": estimated_frames,
        }

    # ─── Paso 2: Extraer frames ──────────────────────────────────────────────

    def _extract_frames(self, input_path: str, frames_dir: str, fps: str,
                        estimated_frames: int = 0, start_time: float = 0.0,
                        segment_duration: float = 0.0,
                        progress_start: float = 5.0, progress_end: float = 15.0):
        """Extrae todos los frames como PNG con FFmpeg."""
        self._check_cancel()
        self._report(progress_start, "Preparando extracción de fotogramas...")

        pattern = os.path.join(frames_dir, "frame_%08d.png")
        cmd = [
            self.ffmpeg_exe,
        ]
        if start_time > 0:
            cmd += ["-ss", f"{start_time:.6f}"]
        cmd += [
            "-i", input_path,
        ]
        if segment_duration > 0:
            cmd += ["-t", f"{segment_duration:.6f}"]
        cmd += [
            "-vsync", "0",       # Sin duplicar ni omitir frames
            "-compression_level", "1",  # Prioriza velocidad; los temporales se eliminan al terminar.
            "-f", "image2",
            pattern,
            "-y"
        ]
        print(f"DEBUG [VideoUpscaler] Ejecutando FFmpeg: {' '.join(cmd)}")
        
        # Hilo para consumir la salida y evitar el llenado del buffer (Deadlock)
        _logs = []
        def log_reader(pipe):
            try:
                for line in pipe:
                    if line:
                        _logs.append(line)
                        # Imprimir solo errores o warnings en consola para no saturar
                        if "error" in line.lower() or "warning" in line.lower():
                            print(f"FFMPEG LOG: {line.strip()}")
            except: pass

        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            creationflags=self._creationflags(),
            text=True,
            errors="ignore",
            bufsize=1
        )
        
        reader_thread = threading.Thread(target=log_reader, args=(proc.stderr,), daemon=True)
        reader_thread.start()
        
        # Monitorizar el proceso
        start_t = time.time()
        while proc.poll() is None:
            self._check_cancel(proc)
            elapsed = time.time() - start_t
            try:
                extracted = sum(1 for entry in os.scandir(frames_dir) if entry.name.endswith(".png"))
            except OSError:
                extracted = 0
            if estimated_frames:
                p = progress_start + min(1.0, extracted / estimated_frames) * (progress_end - progress_start)
                label = f"Extrayendo: {extracted}/{estimated_frames} fotogramas"
            else:
                p = min(progress_end, progress_start + (elapsed / 2.0))
                label = f"Extrayendo fotogramas ({int(elapsed)}s)"
            self._report(p, label + "…")
            time.sleep(0.35)

        proc.wait() # Asegurar cierre
        reader_thread.join(timeout=1.0)
        
        if proc.returncode != 0:
            stderr_out = "".join(_logs)
            print(f"ERROR FFMPEG EXTRACT: {stderr_out}")
            raise Exception(f"FFmpeg fallo al extraer frames (Codigo {proc.returncode}).\n\n{stderr_out[:200]}")

        frames = [f for f in os.listdir(frames_dir) if f.endswith(".png")]
        total = len(frames)
        print(f"INFO [VideoUpscaler] Extraction completa. Total frames: {total}")
        self._report(progress_end, f"Extracción lista: {total} fotogramas.")
        return total

    # ─── Paso 3: Reescalar con NCNN ─────────────────────────────────────────

    def _build_ncnn_cmd(self, engine: str, model_friendly: str, scale: str,
                        in_dir: str, out_dir: str, tile_size: str = "0", denoise: str = "-1", tta: bool = False, concurrency: str = "Automático") -> list:
        """Construye el comando NCNN para procesar un directorio de frames."""
        if not tile_size: tile_size = "0"
        
        # Mapear concurrencia elegida por el usuario
        if concurrency == "Seguro (Estabilidad)":
            threads_arg = "1:1:1"
        elif concurrency == "Equilibrado":
            threads_arg = "1:2:1"
        elif concurrency == "Máximo (Potente)":
            threads_arg = "2:4:2"
        else:
            # Automático (Lógica interna conservadora para video)
            threads_arg = self._thread_args()

        if engine == "SRMD":
            info = SRMD_MODELS.get(model_friendly, {})
            internal = info.get("model", "models-srmd")
            exe = os.path.join(self.models_root, "srmd", "srmd-ncnn-vulkan.exe")
            model_path = os.path.join(self.models_root, "srmd", internal)
            cmd = [
                exe,
                "-i", in_dir, "-o", out_dir,
                "-m", model_path,
                "-n", denoise,
                "-s", scale,
                "-t", tile_size,
                "-f", "png",
                "-j", threads_arg,
            ]
            if tta: cmd += ["-x"]
            return cmd

        elif engine == "Upscayl":
            from src.core.constants import UPSCAYL_MODELS_MAP
            rev_map = {v: k for k, v in UPSCAYL_MODELS_MAP.items()}
            internal_model = rev_map.get(model_friendly, model_friendly)
            
            exe = os.path.join(self.models_root, "upscayl", "upscayl-bin.exe")
            model_path = os.path.join(self.models_root, "upscayl", "models")
            cmd = [
                exe,
                "-i", in_dir, "-o", out_dir,
                "-n", internal_model,
                "-m", model_path,
                "-s", scale,
                "-f", "png",
                "-j", threads_arg,
            ]
            
            # --- NUEVO: Detectar escala nativa del modelo (-z) ---
            import re
            match = re.search(r"[xX]([2-3])", internal_model)
            if match:
                cmd.extend(["-z", match.group(1)])
                
            # upscayl-bin inherits from realesrgan-ncnn so it supports -t and -x
            if tile_size and tile_size != "0":
                cmd += ["-t", tile_size]
            if tta: cmd += ["-x"]
            return cmd

        else:  # Waifu2x
            info = WAIFU2X_MODELS.get(model_friendly, {})
            internal = info.get("model", "models-cunet")
            exe = os.path.join(self.models_root, "waifu2x", "waifu2x-ncnn-vulkan.exe")
            model_path = os.path.join(self.models_root, "waifu2x", internal)
            cmd = [
                exe,
                "-i", in_dir, "-o", out_dir,
                "-m", model_path,
                "-n", denoise,
                "-s", scale,
                "-t", tile_size,
                "-f", "png",
                "-j", threads_arg,
            ]
            if tta: cmd += ["-x"]
            return cmd

    def _run_ncnn(self, engine: str, model_friendly: str, scale: str,
                  in_dir: str, out_dir: str, total_frames: int, tile_size: str = "0",
                  denoise: str = "-1", tta: bool = False,
                  concurrency: str = "Automático", progress_start: float = 15.0,
                  progress_end: float = 85.0):
        """Ejecuta el proceso NCNN y reporta progreso estimado."""
        self._check_cancel()
        self._report(progress_start, f"Iniciando motor AI ({engine})...")

        cmd = self._build_ncnn_cmd(engine, model_friendly, scale, in_dir, out_dir, tile_size, denoise, tta, concurrency)
        print(f"DEBUG [VideoUpscaler] NCNN cmd: {' '.join(cmd)}")

        exe = cmd[0]
        if not os.path.exists(exe):
            raise Exception(
                f"El motor '{engine}' no está instalado.\n\n"
                f"Búscalo en 'Herramientas de Imagen' y descárgalo desde allí "
                "antes de usar el reescalador de video."
            )

        # Hilo para consumir la salida y evitar el llenado del buffer (Deadlock)
        _logs = []
        def log_reader(pipe):
            try:
                for line in pipe:
                    if line:
                        _logs.append(line)
                        if "error" in line.lower() or "failed" in line.lower():
                            print(f"UPSCALER LOG: {line.strip()}")
            except: pass

        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            creationflags=self._creationflags(),
            text=True,
            errors="ignore",
            bufsize=1
        )

        reader_thread = threading.Thread(target=log_reader, args=(proc.stderr,), daemon=True)
        reader_thread.start()

        # Progreso estimado mientras NCNN trabaja (15% → 85%)
        start_time = time.time()
        last_done = -1
        while proc.poll() is None:
            self._check_cancel(proc)
            
            # Contar PNGs en la carpeta de salida
            try:
                done = len([f for f in os.listdir(out_dir) if f.endswith(".png")])
            except:
                done = last_done

            if done != last_done:
                pct = progress_start + (done / max(total_frames, 1)) * (progress_end - progress_start)
                elapsed = int(time.time() - start_time)
                msg = f"Procesando: {done}/{total_frames} fotogramas ({elapsed}s)"
                self._report(min(pct, progress_end - 0.1), msg)
                print(f"UPSCALER: {msg}")
                last_done = done
            
            time.sleep(1.0) # Esperar un poco mas para no saturar disco contando archivos

        proc.wait()
        reader_thread.join(timeout=1.0)

        stderr_out = "".join(_logs)
        
        # --- NUEVAS VALIDACIONES DE ERROR ---
        
        # Detectar memoria agotada antes del error genérico (Windows suele devolver 3221225477).
        lowered = stderr_out.lower()
        vulkan_errors = ["vkqueuesubmit failed", "vkallocatememory failed", "invalid gpu device", "out of gpu memory", "out of device memory", "error -2"]
        memory_failure = any(err in lowered for err in vulkan_errors) or proc.returncode in {3221225477, -1073741819}
        if memory_failure:
            print(f"CRITICAL ERROR (Vulkan): {stderr_out}")
            raise Exception(
                "GPU_MEMORY: La tarjeta gráfica se quedó sin memoria durante el reescalado.\n\n"
                f"Detalles:\n{stderr_out[:500]}"
            )

        if proc.returncode != 0:
            print(f"ERROR NCNN: {stderr_out}")
            raise Exception(f"El motor AI falló (Código {proc.returncode}).\n\nDetalles:\n{stderr_out[:500]}")

        # 3. Verificar integridad de los frames producidos
        out_frames = [f for f in os.listdir(out_dir) if f.endswith(".png")]
        if not out_frames:
            raise Exception("El motor AI terminó pero no se generó ningún fotograma reescalado.")
            
        # Comprobar si el primer frame es válido (no 0 bytes)
        first_frame = os.path.join(out_dir, out_frames[0])
        if os.path.getsize(first_frame) < 100: # Un PNG real pesa más de 100 bytes
            raise Exception("Error de procesamiento: Los fotogramas generados están vacíos o corruptos (posible incompatibilidad de driver GPU).")

        self._report(progress_end, "Reescalado completado con éxito.")

    # ─── Paso 4: Reensamblar con FFmpeg ─────────────────────────────────────

    def _reassemble(self, upscaled_dir: str, original_path: str,
                    output_path: str, fps: str, container: str, has_audio: bool,
                    transparency: bool = False, options: dict | None = None,
                    duration: float = 0.0, progress_start: float = 86.0,
                    progress_end: float = 100.0, final_message: str = "¡Vídeo reescalado con éxito!"):
        """Ensambla los frames reescalados + audio original en el video final."""
        self._check_cancel()
        self._report(progress_start, "Preparando ensamblado final...")

        ext = container if container.startswith(".") else f".{container}"
        codec_info = CONTAINER_CODECS.get(ext, CONTAINER_CODECS[".mp4"])
        options = options or {}
        encoder_preset = str(options.get("encoder_preset") or "fast")
        encoder_crf = str(options.get("encoder_crf") or 18)

        frame_pattern = os.path.join(upscaled_dir, "frame_%08d.png")

        cmd = [
            self.ffmpeg_exe,
            "-framerate", fps,
            "-i", frame_pattern,
        ]

        if has_audio:
            cmd += ["-i", original_path]

        if ext == ".gif":
            # Para GIFs usamos una lógica de paleta para mayor calidad
            # y evitamos el codec x264 que no es soportado por el muxer gif
            cmd += [
                "-vf", "fps=" + fps + ",scale=trunc(iw/2)*2:trunc(ih/2)*2:flags=lanczos,split[s0][s1];[s0]palettegen[p];[s1][p]paletteuse",
                "-loop", "0"
            ]
        else:
            if transparency and ext == ".mov":
                # Usar codec Animation (qtrle) para preservar Alpha en MOV
                cmd += [
                    "-c:v", "qtrle", 
                    "-pix_fmt", "rgba",
                ]
            else:
                cmd += [
                    "-c:v", codec_info["vcodec"],
                    "-pix_fmt", codec_info["pix_fmt"],
                    "-crf", encoder_crf,
                    "-preset", encoder_preset,
                ]

        if has_audio and ext != ".gif":
            # Copiar audio del segundo input (-i original_path)
            cmd += ["-c:a", codec_info["acodec"], "-map", "0:v:0", "-map", "1:a:0?"]
        else:
            # Solo video (o GIF)
            cmd += ["-map", "0:v:0"]

        cmd += ["-progress", "pipe:1", "-stats_period", "0.35", "-nostats", "-y", output_path]

        print(f"DEBUG [VideoUpscaler] Reensamblando: {' '.join(cmd)}")
        
        _logs = []
        _progress = {"seconds": 0.0}
        def log_reader(pipe):
            try:
                for line in pipe:
                    if line:
                        _logs.append(line)
                        if "error" in line.lower() or "warning" in line.lower():
                            print(f"FFMPEG REASSEMBLE LOG: {line.strip()}")
            except: pass

        def progress_reader(pipe):
            try:
                for line in pipe:
                    key, _, value = line.strip().partition("=")
                    if key in {"out_time_us", "out_time_ms"}:
                        try:
                            # Modern FFmpeg reports microseconds in out_time_us.
                            divisor = 1_000_000.0
                            _progress["seconds"] = float(value) / divisor
                        except ValueError:
                            pass
            except Exception:
                pass

        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            creationflags=self._creationflags(),
            text=True,
            errors="ignore",
            bufsize=1
        )
        
        reader_thread = threading.Thread(target=log_reader, args=(proc.stderr,), daemon=True)
        reader_thread.start()
        progress_thread = threading.Thread(target=progress_reader, args=(proc.stdout,), daemon=True)
        progress_thread.start()
        
        start_t = time.time()
        while proc.poll() is None:
            self._check_cancel(proc)
            elapsed = int(time.time() - start_t)
            if duration > 0:
                ratio = min(1.0, _progress["seconds"] / duration)
                p = progress_start + ratio * (progress_end - progress_start)
                msg = f"Guardando video final… {ratio * 100:.0f}%"
            else:
                p = min(progress_end, progress_start + (elapsed * 1.5))
                msg = "Guardando video final y unificando audio…"
            self._report(p, msg)
            time.sleep(0.35)

        proc.wait()
        reader_thread.join(timeout=1.0)
        progress_thread.join(timeout=1.0)

        if proc.returncode != 0:
            stderr_out = "".join(_logs)
            print(f"ERROR FFMPEG REASSEMBLE: {stderr_out}")
            raise Exception(f"FFmpeg falló al crear el video final (Codigo {proc.returncode}):\n{stderr_out[-500:]}")

        self._report(progress_end, final_message)

    def _concat_chunks(self, chunks: list[str], original_path: str, output_path: str,
                       has_audio: bool, progress_start: float = 92.0):
        """Join equal-codec chunks without re-encoding their video stream."""
        concat_file = Path(chunks[0]).parent / "chunks.txt"
        lines = []
        for chunk in chunks:
            safe_path = Path(chunk).resolve().as_posix().replace("'", "'\\''")
            lines.append(f"file '{safe_path}'")
        concat_file.write_text("\n".join(lines) + "\n", encoding="utf-8")

        cmd = [
            self.ffmpeg_exe, "-f", "concat", "-safe", "0", "-i", str(concat_file),
        ]
        if has_audio:
            cmd += ["-i", original_path, "-map", "0:v:0", "-map", "1:a:0?",
                    "-c:v", "copy", "-c:a", "aac", "-shortest"]
        else:
            cmd += ["-map", "0:v:0", "-c:v", "copy"]
        cmd += ["-movflags", "+faststart", "-nostats", "-y", output_path]
        self._report(progress_start, "Uniendo bloques y recuperando el audio…")
        proc = subprocess.Popen(
            cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE,
            creationflags=self._creationflags(), text=True, errors="ignore", bufsize=1,
        )
        stderr_lines = []

        def read_stderr(pipe):
            try:
                stderr_lines.extend(pipe.readlines())
            except Exception:
                pass

        reader = threading.Thread(target=read_stderr, args=(proc.stderr,), daemon=True)
        reader.start()
        while proc.poll() is None:
            self._check_cancel(proc)
            self._report(min(99.0, progress_start + 3.0), "Uniendo bloques y recuperando el audio…")
            time.sleep(0.35)
        reader.join(timeout=1.0)
        if proc.returncode != 0:
            raise Exception("FFmpeg no pudo unir los bloques:\n" + "".join(stderr_lines)[-700:])
        self._report(100, "¡Vídeo reescalado con éxito!")

    def _chunk_duration(self, info: dict, scale: int) -> float:
        """Keep temporary PNGs near an 8 GB working set."""
        width = max(1, int(info.get("width") or 1))
        height = max(1, int(info.get("height") or 1))
        try:
            fps = max(1.0, float(info.get("fps") or 30))
        except (TypeError, ValueError):
            fps = 30.0
        free = shutil.disk_usage(tempfile.gettempdir()).free
        estimated_png_bytes_per_second = width * height * fps * 2.2 * (1 + scale ** 2)
        minimum_working_set = estimated_png_bytes_per_second * 1.5
        if minimum_working_set > free * 0.72:
            need_gb = minimum_working_set / (1024 ** 3)
            free_gb = free / (1024 ** 3)
            raise Exception(
                f"No hay espacio temporal para un bloque mínimo: se necesitan ~{need_gb:.1f} GB "
                f"y hay {free_gb:.1f} GB libres. Libera espacio o reduce la escala."
            )
        budget = min(8 * 1024 ** 3, max(int(minimum_working_set), int(free * 0.18)))
        seconds = budget / max(1.0, estimated_png_bytes_per_second)
        return max(1.5, min(15.0, seconds))

    def _upscale_video_chunked(self, input_path: str, output_path: str, info: dict,
                               options: dict, engine: str, model: str, scale: str,
                               ext_out: str) -> str:
        """Bound disk usage by processing and deleting one short segment at a time."""
        duration = float(info.get("duration") or 0)
        scale_number = max(1, int(scale or 1))
        chunk_seconds = self._chunk_duration(info, scale_number)
        chunk_count = max(1, int(math.ceil(duration / chunk_seconds)))
        root = Path(tempfile.mkdtemp(prefix="xomacito_video_chunks_"))
        chunks: list[str] = []
        try:
            for index in range(chunk_count):
                self._check_cancel()
                start_time = index * chunk_seconds
                segment_duration = min(chunk_seconds, duration - start_time)
                if segment_duration <= 0:
                    break
                segment_start = 4.0 + (index / chunk_count) * 86.0
                segment_end = 4.0 + ((index + 1) / chunk_count) * 86.0
                span = segment_end - segment_start
                frames_dir = root / f"in_{index:05d}"
                upscaled_dir = root / f"out_{index:05d}"
                frames_dir.mkdir(); upscaled_dir.mkdir()
                expected = max(1, round(segment_duration * float(info.get("fps") or 30)))
                total = self._extract_frames(
                    input_path, str(frames_dir), info["fps"], expected,
                    start_time=start_time, segment_duration=segment_duration,
                    progress_start=segment_start, progress_end=segment_start + span * 0.12,
                )
                if not total:
                    raise Exception(f"El bloque {index + 1} no produjo fotogramas.")

                tile = options.get("upscale_tile", "0")
                concurrency = options.get("upscale_concurrency", "Automático")
                attempts = [(tile, concurrency), ("128", "Seguro (Estabilidad)"),
                            ("64", "Seguro (Estabilidad)")]
                unique_attempts = list(dict.fromkeys(attempts))
                for attempt_index, (attempt_tile, attempt_concurrency) in enumerate(unique_attempts):
                    try:
                        self._run_ncnn(
                            engine, model, scale, str(frames_dir), str(upscaled_dir), total,
                            tile_size=attempt_tile,
                            denoise=options.get("upscale_denoise", "-1"),
                            tta=options.get("upscale_tta", False),
                            concurrency=attempt_concurrency,
                            progress_start=segment_start + span * 0.12,
                            progress_end=segment_start + span * 0.88,
                        )
                        break
                    except Exception as error:
                        if "GPU_MEMORY:" not in str(error) or attempt_index == len(unique_attempts) - 1:
                            raise
                        for frame in upscaled_dir.glob("*.png"):
                            frame.unlink(missing_ok=True)

                chunk_path = root / f"chunk_{index:05d}.mp4"
                self._reassemble(
                    str(upscaled_dir), input_path, str(chunk_path), info["fps"], ".mp4", False,
                    options=options, duration=segment_duration,
                    progress_start=segment_start + span * 0.88, progress_end=segment_end,
                    final_message=f"Bloque {index + 1}/{chunk_count} listo.",
                )
                chunks.append(str(chunk_path))
                shutil.rmtree(frames_dir, ignore_errors=True)
                shutil.rmtree(upscaled_dir, ignore_errors=True)

            if not chunks:
                raise Exception("No se generó ningún bloque de video.")
            self._concat_chunks(chunks, input_path, output_path, bool(info.get("has_audio")), 91.0)
            return output_path
        finally:
            shutil.rmtree(root, ignore_errors=True)

    # ─── Orquestador principal ───────────────────────────────────────────────

    def upscale_video(self, input_path: str, output_path: str, options: dict) -> str:
        """
        Proceso completo: extraer -> reescalar -> reensamblar.
        """
        self._check_dependencies()
        
        engine = options.get("upscale_engine", "Real-ESRGAN")
        model = options.get("upscale_model_friendly", "")
        if not model:
            if engine == "Upscayl":
                upscayl_models_dir = os.path.join(self.models_root, "upscayl", "models")
                if os.path.exists(upscayl_models_dir):
                    models = [f[:-6] for f in os.listdir(upscayl_models_dir) if f.endswith(".param")]
                    model = sorted(models)[0] if models else "realesrgan-x4plus"
                else:
                    model = "realesrgan-x4plus"
            else:
                model_map = {
                    "Waifu2x":     WAIFU2X_MODELS,
                    "SRMD":        SRMD_MODELS,
                }
                model = list(model_map.get(engine, WAIFU2X_MODELS).keys())[0]

        scale = options.get("upscale_scale", "2").replace("x", "")
        container_choice = options.get("upscale_container", "")

        # Info del video original
        info = self._get_video_info(input_path)
        fps = info["fps"]
        has_audio = info["has_audio"]

        # Refuse work that would fill the disk halfway through a long video.
        if (float(info.get("duration") or 0) <= 18 and info.get("estimated_frames")
                and info.get("width") and info.get("height")):
            scale_number = max(1, int(scale or 1))
            input_temp = info["estimated_frames"] * info["width"] * info["height"] * 2.2
            output_temp = input_temp * (scale_number ** 2)
            required = int((input_temp + output_temp) * 1.15)
            free = shutil.disk_usage(tempfile.gettempdir()).free
            if required > free:
                need_gb = required / (1024 ** 3)
                free_gb = free / (1024 ** 3)
                raise Exception(
                    f"No hay espacio temporal suficiente para este video: se estiman {need_gb:.1f} GB "
                    f"y hay {free_gb:.1f} GB libres. Usa 2x, un fragmento más corto o libera espacio."
                )

        # Determinar extension de salida
        if not container_choice or container_choice.lower() == "mismo que el original":
            ext_out = info["ext"] if info["ext"] else ".mp4"
        else:
            ext_out = container_choice if container_choice.startswith(".") else f".{container_choice}"

        # Ajustar output_path con la extension elegida
        base, _ = os.path.splitext(output_path)
        output_path = base + ext_out

        if float(info.get("duration") or 0) > 18:
            return self._upscale_video_chunked(
                input_path, output_path, info, options, engine, model, scale, ext_out
            )

        frames_dir = None
        upscaled_dir = None
        try:
            # Crear directorios temporales
            frames_dir = tempfile.mkdtemp(prefix="xomacito_upscale_in_")
            upscaled_dir = tempfile.mkdtemp(prefix="xomacito_upscale_out_")

            # Paso 1: Extraer frames
            total = self._extract_frames(
                input_path, frames_dir, fps, int(info.get("estimated_frames") or 0)
            )
            if total == 0:
                raise Exception("No se pudieron extraer fotogramas del video.")

            # Paso 2: Reescalar con NCNN (Pasamos el tile size y denoise desde opciones)
            tile_size = options.get("upscale_tile", "0")
            denoise = options.get("upscale_denoise", "-1")
            tta = options.get("upscale_tta", False)
            concurrency = options.get("upscale_concurrency", "Automático")
            transparency = options.get("upscale_transparency", False)
            
            attempts = [(tile_size, concurrency)]
            for fallback in (("128", "Seguro (Estabilidad)"), ("64", "Seguro (Estabilidad)")):
                if fallback not in attempts:
                    attempts.append(fallback)
            for attempt_index, (attempt_tile, attempt_concurrency) in enumerate(attempts):
                if attempt_index:
                    for frame in Path(upscaled_dir).glob("*.png"):
                        frame.unlink(missing_ok=True)
                    self._report(
                        15,
                        f"Memoria de GPU limitada; reintentando en modo seguro (tile {attempt_tile})...",
                    )
                try:
                    self._run_ncnn(
                        engine, model, scale, frames_dir, upscaled_dir, total,
                        tile_size=attempt_tile, denoise=denoise, tta=tta,
                        concurrency=attempt_concurrency,
                    )
                    break
                except Exception as error:
                    if "GPU_MEMORY:" not in str(error) or attempt_index == len(attempts) - 1:
                        if "GPU_MEMORY:" in str(error):
                            raise Exception(
                                "La GPU no tiene memoria suficiente. Xomacito ya probó los modos "
                                "seguros de 128 y 64. Intenta 2x, cierra aplicaciones que usen la "
                                "GPU o utiliza un video más corto."
                            ) from error
                        raise

            # Paso 3: Reensamblar
            self._reassemble(
                upscaled_dir, input_path, output_path, fps, ext_out, has_audio,
                transparency=transparency, options=options,
                duration=float(info.get("duration") or 0),
            )

        finally:
            # Limpieza garantizada
            for d in [frames_dir, upscaled_dir]:
                if d and os.path.exists(d):
                    try:
                        shutil.rmtree(d, ignore_errors=True)
                    except:
                        pass

        return output_path
