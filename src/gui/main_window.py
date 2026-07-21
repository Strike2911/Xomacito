"""Ventana principal de Xomacito como aplicación independiente."""
import threading
import webbrowser
from tkinter import messagebox
import tkinter
import customtkinter as ctk
from customtkinter import filedialog
from PIL import Image
import requests
from io import BytesIO
import queue
import gc
import os
import re
import sys
from pathlib import Path
import subprocess
import json
import time
import shutil
import platform
from src.core.daily_icon import daily_cat_assets
from src.core.restart import clean_restart_environment

import io
from packaging import version

try:
    from tkinterdnd2 import TkinterDnD, DND_FILES
    TKDND_AVAILABLE = True
    
    # ✅ CORRECCIÓN: Heredar de CTk y usar el Wrapper de DnD
    # Esto asegura que la ventana tenga los atributos de escalado de CTk
    class TkBase(ctk.CTk, TkinterDnD.DnDWrapper):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self.TkdndVersion = TkinterDnD._require(self)
    
except ImportError:
    TKDND_AVAILABLE = False
    print("ADVERTENCIA: tkinterdnd2 no instalado. Drag & Drop deshabilitado.")
    
    # Fallback a CTk normal
    TkBase = ctk.CTk

from datetime import datetime, timedelta
from src.core.inkscape_service import InkscapeService
from src.core.processor import FFmpegProcessor
from contextlib import redirect_stdout
from .single_download_tab import SingleDownloadTab
from .visual_shell import DailyBrandHeader, GradientBackdrop
from src.core.text_utils import clean_filename_text
from .dialogs import (
    ConflictDialog, LoadingWindow, CompromiseDialog, 
    SimpleMessageDialog, SavePresetDialog, PlaylistErrorDialog,
    Tooltip, apply_icon
)
from src.core.constants import (
    VIDEO_EXTENSIONS, AUDIO_EXTENSIONS, SINGLE_STREAM_AUDIO_CONTAINERS,
    FORMAT_MUXER_MAP, LANG_CODE_MAP, LANGUAGE_ORDER, DEFAULT_PRIORITY,
    EDITOR_FRIENDLY_CRITERIA, COMPATIBILITY_RULES
)

def resource_path(relative_path):
    """Obtiene recursos externos tanto en desarrollo como junto al ejecutable."""
    candidates = []
    if getattr(sys, "frozen", False):
        executable_root = Path(sys.executable).resolve().parent
        candidates.extend((executable_root / "_internal", executable_root))
    candidates.extend((Path(__file__).resolve().parents[2], Path.cwd()))
    for base_path in candidates:
        candidate = base_path / relative_path
        if candidate.exists():
            return str(candidate)
    return str(candidates[0] / relative_path)

from main import PROJECT_ROOT, BIN_DIR, FFMPEG_BIN_DIR, DENO_BIN_DIR, POPPLER_BIN_DIR


# ══════════════════════════════════════════════════════════════════════════════
#  ConsoleLogger — Redirige sys.stdout/stderr a la consola embebida de Xomacito
# ══════════════════════════════════════════════════════════════════════════════
class _TeeStream:
    """
    Stream que escribe simultáneamente en el stream original (terminal de VS Code)
    y encola líneas para la consola embebida cuando está activa.
    Thread-safe: usa un Lock para proteger el buffer.
    """
    MAX_LINES = 2500  # Límite de líneas en el textbox antes de recortar

    def __init__(self, original_stream):
        self._original = original_stream
        self._enabled = False
        self._callback = None       # func(text) → llamada desde hilo principal
        self._lock = threading.Lock()
        self._pending = []          # Buffer de texto pendiente de enviar a la UI
        self._flush_scheduled = False

    def enable(self, callback):
        """Activa la captura y registra el callback de UI."""
        with self._lock:
            self._callback = callback
            self._enabled = True

    def disable(self):
        """Desactiva la captura. El callback deja de recibir nuevas líneas."""
        with self._lock:
            self._enabled = False

    def write(self, text):
        # Siempre al stream original (terminal del IDE) — tolerante a errores de encoding
        try:
            self._original.write(text)
        except (UnicodeEncodeError, UnicodeDecodeError):
            try:
                safe = text.encode(self._original.encoding or 'utf-8', errors='replace').decode(self._original.encoding or 'utf-8', errors='replace')
                self._original.write(safe)
            except Exception:
                pass
        except Exception:
            pass
        # Si está activo, acumular en buffer para envío batched
        if self._enabled and text:
            with self._lock:
                self._pending.append(text)

    def flush(self):
        try:
            self._original.flush()
        except Exception:
            pass

    def pop_pending(self):
        """Devuelve y vacía el buffer pendiente de forma thread-safe."""
        with self._lock:
            data = "".join(self._pending)
            self._pending.clear()
        return data


class ConsoleLogger:
    """
    Gestor de consola: instala/deinstala los TeeStreams en sys.stdout y sys.stderr.
    Debe crearse ANTES de que la UI esté lista; se conecta a la UI después
    llamando a connect_ui().
    """
    def __init__(self):
        self._stdout_tee = _TeeStream(sys.stdout)
        self._stderr_tee = _TeeStream(sys.stderr)
        # Instalar inmediatamente (modo pasivo: captura desactivada hasta enable())
        sys.stdout = self._stdout_tee
        sys.stderr = self._stderr_tee
        self._ui_callback = None
        self._after_func = None   # referencia a app.after()

    def connect_ui(self, after_func, ui_callback):
        """
        Conecta la UI después de que la ventana esté lista.
        after_func: app.after  •  ui_callback: config_tab.append_to_console
        """
        self._after_func = after_func
        self._ui_callback = ui_callback
        # Arrancar el ciclo de flush a la UI
        self._schedule_flush()

    def enable(self):
        if self._ui_callback:
            self._stdout_tee.enable(self._ui_callback)
            self._stderr_tee.enable(self._ui_callback)

    def disable(self):
        self._stdout_tee.disable()
        self._stderr_tee.disable()

    def _schedule_flush(self):
        """Ciclo de 150 ms que vacía el buffer al textbox."""
        if self._after_func is None:
            return
        self._after_func(150, self._flush_to_ui)

    def _flush_to_ui(self):
        """Recoge el texto acumulado y lo manda a la UI de una sola vez."""
        try:
            text = self._stdout_tee.pop_pending()
            text += self._stderr_tee.pop_pending()
            if text and self._ui_callback:
                self._ui_callback(text)
        except Exception:
            pass
        finally:
            self._schedule_flush()  # Reprogramar siempre

if getattr(sys, 'frozen', False):
    APP_BASE_PATH = os.path.dirname(sys.executable)
else:
    APP_BASE_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))

class LoadingWindow(ctk.CTkToplevel):
    def __init__(self, master):
        super().__init__(master)
        self.title("Iniciando...")
        apply_icon(self)
        self.geometry("350x120")
        self.resizable(False, False)
        self.protocol("WM_DELETE_WINDOW", lambda: None) 
        self.transient(master) 
        self.lift()
        self.error_state = False
        win_width = 350
        win_height = 120
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()
        pos_x = (screen_width // 2) - (win_width // 2)
        pos_y = (screen_height // 2) - (win_height // 2)
        self.geometry(f"{win_width}x{win_height}+{pos_x}+{pos_y}")
        self.label = ctk.CTkLabel(self, text="Preparando la aplicación, por favor espera...", wraplength=320)
        self.label.pack(pady=(20, 10), padx=20)
        self.progress_bar = ctk.CTkProgressBar(self)
        self.progress_bar.set(0)
        self.progress_bar.pack(pady=10, padx=20, fill="x")
        self.grab_set() 

    def update_progress(self, text, value):
        if not self.winfo_exists():
            return
        self.label.configure(text=text)
        if value >= 0:
            self.progress_bar.set(value)
        else: 
            self.error_state = True 
            self.progress_bar.configure(progress_color="red")
            self.progress_bar.set(1)

class MainWindow(TkBase):
    def _apply_daily_icon(self, schedule_retry=True):
        """Aplica el gatito del día a la ventana y lo reafirma tras iniciar Tk."""
        try:
            icon_path = self.daily_cat.ico_path
            if icon_path.exists():
                self.iconbitmap(str(icon_path))
            else:
                self.iconbitmap(resource_path("Xomacito-icon.ico"))
        except (OSError, tkinter.TclError):
            pass
        if schedule_retry:
            self.after(350, lambda: self._apply_daily_icon(schedule_retry=False))

        
    def _get_best_available_info(self, url, options):
        """
        Ejecuta una simulación usando la API de yt-dlp para obtener información
        sobre el mejor formato disponible cuando la selección del usuario falla.
        """
        try:
            from src.core.downloader import extract_info_resilient

            mode = options.get("mode", "Video+Audio")
            
            ydl_opts = {
                'no_warnings': True,
                'noplaylist': True,
                'quiet': True,
                'ffmpeg_location': self.ffmpeg_processor.ffmpeg_path
            }
            
            # Determinar el selector según el modo
            if mode == "Solo Audio":
                ydl_opts['format'] = 'ba/best'
            else:
                # Intentar con audio si está disponible, sino solo video
                ydl_opts['format'] = 'bv+ba/bv/best'

            # Configurar cookies
            cookie_mode = options.get("cookie_mode")
            if cookie_mode == "Archivo Manual..." and options.get("cookie_path"):
                ydl_opts['cookiefile'] = options["cookie_path"]
            elif cookie_mode != "No usar":
                browser_arg = options.get("selected_browser", "chrome")
                if options.get("browser_profile"):
                    browser_arg += f":{options['browser_profile']}"
                ydl_opts['cookiesfrombrowser'] = (browser_arg,)

            info = extract_info_resilient(url, ydl_opts, download=False)

            if not info:
                return "No se pudo obtener información del video."

            # Construir mensaje detallado según el modo
            if mode == "Solo Audio":
                abr = info.get('abr') or info.get('tbr', 0)
                acodec = info.get('acodec', 'desconocido')
                if acodec and acodec != 'none':
                    acodec = acodec.split('.')[0].upper()
                
                ext = info.get('ext', 'N/A')
                filesize = info.get('filesize') or info.get('filesize_approx')
                
                message = f"🎵 Mejor audio disponible:\n\n"
                message += f"• Bitrate: ~{abr:.0f} kbps\n"
                message += f"• Códec: {acodec}\n"
                message += f"• Formato: {ext}\n"
                
                if filesize:
                    size_mb = filesize / (1024 * 1024)
                    message += f"• Tamaño: ~{size_mb:.1f} MB\n"
                
                return message
            
            else:  # Video+Audio
                # Información de video
                width = info.get('width', 'N/A')
                height = info.get('height', 'N/A')
                vcodec = info.get('vcodec', 'desconocido')
                if vcodec and vcodec != 'none':
                    vcodec = vcodec.split('.')[0].upper()
                
                fps = info.get('fps', 'N/A')
                vext = info.get('ext', 'N/A')
                
                # Información de audio
                acodec = info.get('acodec', 'desconocido')
                if acodec and acodec != 'none':
                    acodec = acodec.split('.')[0].upper()
                else:
                    acodec = "Sin audio"
                
                abr = info.get('abr') or info.get('tbr', 0)
                
                # Tamaño
                filesize = info.get('filesize') or info.get('filesize_approx')
                
                message = f"🎬 Mejor calidad disponible:\n\n"
                message += f"📹 Video:\n"
                message += f"   • Resolución: {width}x{height}\n"
                message += f"   • Códec: {vcodec}\n"
                
                if fps != 'N/A':
                    message += f"   • FPS: {fps}\n"
                
                message += f"   • Formato: {vext}\n\n"
                
                message += f"🔊 Audio:\n"
                message += f"   • Códec: {acodec}\n"
                
                if acodec != "Sin audio":
                    message += f"   • Bitrate: ~{abr:.0f} kbps\n"
                
                if filesize:
                    size_mb = filesize / (1024 * 1024)
                    message += f"\n📦 Tamaño estimado: ~{size_mb:.1f} MB"
                
                return message

        except Exception as e:
            error_msg = str(e)
            print(f"ERROR: Falló la simulación de descarga: {error_msg}")
            
            # Mensaje más amigable para el usuario
            return (
                "❌ No se pudieron obtener los detalles del formato alternativo.\n\n"
                f"Razón: {error_msg[:100]}...\n\n"
                "Puedes intentar:\n"
                "• Verificar la URL\n"
                "• Configurar cookies si el video es privado\n"
                "• Intentar más tarde si hay límite de peticiones"
            )

    def __init__(self, launch_target=None, project_root=None, poppler_path=None, inkscape_path=None, splash_screen=None, app_version="0.0.0", theme_data=None, theme_warnings=None):
        super().__init__()
        
        # 1. Configuración de ventana inicial (Ocultar y poner icono)
        self.withdraw()  # Mantener oculta hasta que todo esté listo
        self.daily_cat = daily_cat_assets(project_root or PROJECT_ROOT)
        self._apply_daily_icon()
            
        self.theme_data = theme_data or {}
        self.theme_warnings = theme_warnings or []
        
        # Guardamos la versión que recibimos de main.py
        self.APP_VERSION = app_version 
        print(f"DEBUG: MainWindow recibió la versión: {self.APP_VERSION}")

        # --- CORRECCIÓN CRÍTICA: Registrar este Root INMEDIATAMENTE ---
        import tkinter
        tkinter._default_root = self

        self.splash_screen = splash_screen 
        if self.splash_screen:
            self.splash_screen.update_status("Inicializando componentes...")
        
        # 📏 ESCALADO INTELIGENTE PARA MONITORES PEQUEÑOS
        # Si la altura de la pantalla es menor a 900px (ej: laptops 1366x768),
        # reducimos la interfaz al 85% para que quepa todo.
        screen_height = self.winfo_screenheight()
        if screen_height < 900:
            print(f"INFO: Monitor pequeño detectado ({screen_height}px). Aplicando escala 0.85x.")
            ctk.set_widget_scaling(0.85)  # Reduce el tamaño de los widgets
            ctk.set_window_scaling(0.85)  # Reduce el tamaño de la ventana
        else:
            ctk.set_widget_scaling(1.0)
            ctk.set_window_scaling(1.0)

        # Aplicar estilos de CustomTkinter manualmente
        # Nota: main.py ya aplicó el modo de apariencia guardado del usuario
        # antes de crear MainWindow, así que NO lo sobreescribimos aquí.
        if TKDND_AVAILABLE:
            if ctk.get_appearance_mode().lower() == "dark":
                self.configure(bg="#2B2B2B")

        self.VIDEO_EXTENSIONS = VIDEO_EXTENSIONS
        self.AUDIO_EXTENSIONS = AUDIO_EXTENSIONS
        self.SINGLE_STREAM_AUDIO_CONTAINERS = SINGLE_STREAM_AUDIO_CONTAINERS
        self.FORMAT_MUXER_MAP = FORMAT_MUXER_MAP
        self.LANG_CODE_MAP = LANG_CODE_MAP
        self.LANGUAGE_ORDER = LANGUAGE_ORDER
        self.DEFAULT_PRIORITY = DEFAULT_PRIORITY
        self.EDITOR_FRIENDLY_CRITERIA = EDITOR_FRIENDLY_CRITERIA
        self.COMPATIBILITY_RULES = COMPATIBILITY_RULES

        # --- ¡AQUÍ ESTÁ LA CORRECCIÓN! ---
        # 2. Determina la ruta base (PARA LOS BINARIOS)
        if getattr(sys, 'frozen', False):
            # Modo .exe: la ruta es el directorio del ejecutable
            self.APP_BASE_PATH = os.path.dirname(sys.executable)
        elif project_root:
            # Modo Dev: usamos la ruta pasada desde main.py
            self.APP_BASE_PATH = project_root
        else:
            # Fallback (no debería usarse, pero es seguro tenerlo)
            self.APP_BASE_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))

        # 3. Define las rutas de configuración (PARA LOS DATOS DE USUARIO)
        
        # --- INICIO DE LA MODIFICACIÓN (LA BUENA) ---
        # 1. Definir la carpeta de datos del usuario en %APPDATA%
        appdata_path = os.getenv('APPDATA')
        if not appdata_path:  # Fallback si APPDATA no existe (Raro en Windows, pero seguro)
            appdata_path = os.path.expanduser('~\\AppData\\Roaming')
            
        self.APP_DATA_DIR = os.path.join(appdata_path, 'Xomacito')

        # 2. Asegurarse de que esa carpeta exista
        try:
            os.makedirs(self.APP_DATA_DIR, exist_ok=True)
        except Exception as e:
            print(f"ERROR: No se pudo crear la carpeta de datos en %APPDATA%: {e}")
            self.APP_DATA_DIR = self.APP_BASE_PATH

        self.SETTINGS_FILE = os.path.join(self.APP_DATA_DIR, "app_settings.json")
        self.PRESETS_FILE = os.path.join(self.APP_DATA_DIR, "presets.json") 
        self.USER_THEMES_DIR = os.path.join(self.APP_DATA_DIR, "themes")
        os.makedirs(self.USER_THEMES_DIR, exist_ok=True)
        
        print(f"DEBUG: Carpeta de datos de usuario: {self.APP_DATA_DIR}")
        print(f"DEBUG: Archivo de configuración: {self.SETTINGS_FILE}")
        
        # 4. MIGRACIÓN AUTOMÁTICA (Para evitar que los usuarios pierdan configuraciones antiguas)
        import shutil
        old_settings = os.path.join(self.APP_BASE_PATH, "app_settings.json")
        old_presets = os.path.join(self.APP_BASE_PATH, "presets.json")
        
        if self.APP_DATA_DIR != self.APP_BASE_PATH:
            if os.path.exists(old_settings) and not os.path.exists(self.SETTINGS_FILE):
                try:
                    shutil.move(old_settings, self.SETTINGS_FILE)
                    print("INFO: Opciones antiguas migradas a AppData.")
                except Exception as e:
                    print(f"ERROR: Falló la migración de app_settings.json: {e}")
                    
            if os.path.exists(old_presets) and not os.path.exists(self.PRESETS_FILE):
                try:
                    shutil.move(old_presets, self.PRESETS_FILE)
                    print("INFO: Presets antiguos migrados a AppData.")
                except Exception as e:
                    print(f"ERROR: Falló la migración de presets.json: {e}")
        # --- FIN DE LA MODIFICACIÓN ---

        self.ui_update_queue = queue.Queue()
        self._process_ui_queue()

        self.is_shutting_down = False
        self._update_in_progress = False
        self.cancellation_event = threading.Event()
        self.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.title(f"Xomacito {self.APP_VERSION}")
        
        # Obtener dimensiones de pantalla
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()

        # Margen de seguridad para Barra de Tareas (abajo) y Barra de Título (arriba)
        # 100px es seguro para Windows/Mac/Linux
        safe_height = screen_height - 100

        # --- LÓGICA DE ADAPTACIÓN DE PANTALLA ---
        # Umbral subido a 1020px para capturar resoluciones 1440x900 y 1280x1024
        if screen_height < 1020:  
            print(f"INFO: Pantalla compacta detectada ({screen_width}x{screen_height}). Ajustando.")
            
            # 1. Escalado: Si es muy pequeña (768p), 0.75x. Si es mediana (900p), 0.85x.
            if screen_height < 800:
                scale_factor = 0.75
            else:
                scale_factor = 0.85 # Un poco más grande para 900p
            
            ctk.set_widget_scaling(scale_factor)  
            ctk.set_window_scaling(scale_factor)
            
            # 2. Dimensiones: Usar el ALTO SEGURO calculado
            win_width = min(max(980, screen_width - 120), 1180)
            win_height = safe_height # <--- ESTO GARANTIZA QUE NO SE CORTE
            
            # 3. Posición: Pegado arriba (Y=10) para aprovechar espacio
            pos_x = (screen_width // 2) - (win_width // 2)
            pos_y = 10 
            
            # 4. Minsize permisivo
            min_w, min_h = 900, 560
            
        else: # Monitores grandes (1080p o más)
            win_width = min(1120, screen_width - 100)
            win_height = min(900, safe_height)
            
            # Centrado vertical estándar
            pos_x = (screen_width // 2) - (win_width // 2)
            pos_y = (screen_height // 2) - (win_height // 2)
            
            min_w, min_h = 960, 680
            
            # Escalado normal
            ctk.set_widget_scaling(1.0)
            ctk.set_window_scaling(1.0)

        # Aplicar
        self.geometry(f"{win_width}x{win_height}+{int(pos_x)}+{int(pos_y)}")
        self.minsize(min_w, min_h)
        
        self.is_updating_dimension = False
        self.current_aspect_ratio = None
        
        # Aplicar límite mínimo calculado
        self.minsize(min_w, min_h)
        
        # Nota: No llamar ctk.set_appearance_mode aquí — main.py ya lo hizo.
        
        self.ui_request_event = threading.Event()
        self.ui_request_data = {}
        self.ui_response_event = threading.Event()
        self.ui_response_data = {}
        
        # --- INICIALIZAR VALORES POR DEFECTO ---
        # Define todos los atributos ANTES del bloque try
        self.default_download_path = ""
        self.batch_download_path = ""
        self.image_output_path = ""
        self.cookies_path = ""
        self.cookies_mode_saved = "No usar"
        self.selected_browser_saved = "firefox"
        self.browser_profile_saved = ""
        self.ffmpeg_update_snooze_until = None
        self.custom_presets = []
        self.batch_playlist_analysis_saved = True
        self.batch_fast_mode_saved = True 
        self.quick_preset_saved = ""
        self.recode_settings = {}
        self.apply_quick_preset_checkbox_state = False
        self.keep_original_quick_saved = True
        self.image_settings = {}
        self.upscayl_custom_models = {}  # Mapeo: nombre_real -> apodo
        self.console_enabled = False   # Consola de diagnóstico desactivada por defecto
        self.console_wrap = False      # Ajuste de línea desactivado por defecto
        self.keep_ai_models_in_memory = False # Optimización de VRAM
        self.show_onnx_warning = True # Mostrar aviso de rendimiento de ONNX por defecto
        self.vector_dpi = 300 # Calidad de renderizado para PDF/AI/EPS (Estándar: 300)
        self.preview_vector_dpi = 100 # Calidad de previsualización para vectores (Rápida: 100)
        self.vector_force_background = False # Fondo blanco para vectores (Default: False/Transparente)
        
        self.inkscape_enabled = False
        self.inkscape_path = r"C:\Program Files\Inkscape"
        self.inkscape_version = ""
        self.selected_theme_accent = "midnight_ocean"
        self.theme_selection_explicit = False
        self.appearance_mode = "Dark" # Default profesional
        self.clean_titles = False # Limpieza de emojis en títulos
        self.release_notice_seen_version = ""
        
        # --- INTENTAR CARGAR CONFIGURACIÓN GUARDADA ---
        try:
            print(f"DEBUG: Intentando cargar configuración desde: {self.SETTINGS_FILE}")
            if os.path.exists(self.SETTINGS_FILE):
                with open(self.SETTINGS_FILE, 'r') as f:
                    settings = json.load(f)
                    # Sobrescribe los valores por defecto con los que están guardados
                    self.default_download_path = settings.get("default_download_path", self.default_download_path)
                    self.batch_download_path = settings.get("batch_download_path", self.batch_download_path)
                    self.image_output_path = settings.get("image_output_path", self.image_output_path)
                    self.cookies_path = settings.get("cookies_path", self.cookies_path)
                    self.cookies_mode_saved = settings.get("cookies_mode", self.cookies_mode_saved)
                    self.selected_browser_saved = settings.get("selected_browser", self.selected_browser_saved)
                    self.browser_profile_saved = settings.get("browser_profile", self.browser_profile_saved)
                    snooze_str = settings.get("ffmpeg_update_snooze_until")
                    self.batch_playlist_analysis_saved = settings.get("batch_playlist_analysis", self.batch_playlist_analysis_saved)
                    self.batch_fast_mode_saved = settings.get("batch_fast_mode", self.batch_fast_mode_saved)
                    self.quick_preset_saved = settings.get("quick_preset_saved", self.quick_preset_saved)
                    if snooze_str:
                        self.ffmpeg_update_snooze_until = datetime.fromisoformat(snooze_str)
                    self.recode_settings = settings.get("recode_settings", self.recode_settings)
                
                    self.apply_quick_preset_checkbox_state = settings.get("apply_quick_preset_enabled", self.apply_quick_preset_checkbox_state)
                    self.keep_original_quick_saved = settings.get("keep_original_quick_enabled", self.keep_original_quick_saved)
                    self.image_settings = settings.get("image_settings", {})
                    self.upscayl_custom_models = settings.get("upscayl_custom_models", {})
                    self.console_enabled = settings.get("console_enabled", False)
                    self.console_wrap = settings.get("console_wrap", False)
                    self.keep_ai_models_in_memory = settings.get("keep_ai_models_in_memory", False)
                    self.show_onnx_warning = settings.get("show_onnx_warning", True)
                    self.vector_dpi = settings.get("vector_dpi", 300)
                    self.preview_vector_dpi = settings.get("preview_vector_dpi", 100)
                    self.vector_force_background = settings.get("vector_force_background", False)
                    
                    # Cargar ajustes de Inkscape externo
                    self.inkscape_enabled = settings.get("inkscape_enabled", False)
                    self.inkscape_path = settings.get("inkscape_path", r"C:\Program Files\Inkscape")
                    self.inkscape_version = settings.get("inkscape_version", "")
                    self.selected_theme_accent = settings.get("selected_theme_accent", "midnight_ocean")
                    self.theme_selection_explicit = settings.get("theme_selection_explicit", False)
                    self.appearance_mode = settings.get("appearance_mode", "System")

                    self.clean_titles = settings.get("clean_titles", False)
                    self.release_notice_seen_version = settings.get(
                        "release_notice_seen_version", ""
                    )

                print(f"DEBUG: Configuración cargada exitosamente.")
            else:
                print("DEBUG: Archivo de configuración no encontrado. Usando valores por defecto.")
            
            # Inicializar servicio de Inkscape
            self.inkscape_service = InkscapeService(self.inkscape_path) if self.inkscape_enabled else None
            
            # --- NUEVO: Crear plantilla de tema si no existe ---
            self._ensure_theme_template()
            
        except (json.JSONDecodeError, IOError) as e:
            print(f"ERROR: Fallo al cargar configuración: {e}. Usando valores por defecto.")
            # No se necesita 'pass' porque los valores por defecto ya están establecidos

        self.ffmpeg_processor = FFmpegProcessor(app_version=self.APP_VERSION, cache_dir=self.APP_DATA_DIR)
        self.gradient_backdrop = GradientBackdrop(self, self.theme_data)
        self.gradient_backdrop.place(x=0, y=0, relwidth=1, relheight=1)

        self.brand_header = DailyBrandHeader(self, self.daily_cat, self.APP_VERSION, self.theme_data)
        self.brand_header.pack(fill="x", padx=14, pady=(12, 4))

        self.tab_view = ctk.CTkTabview(self, anchor="nw", command=self._on_tab_view_change, corner_radius=12)
        self.tab_view.pack(expand=True, fill="both", padx=14, pady=(0, 10))
        
        # --- NUEVO: MOSTRAR ADVERTENCIAS DEL TEMA AL INICIO ---
        if self.theme_warnings:
            self.after(1000, self._show_theme_warnings)

        # (Cargará la clase de nuestro nuevo archivo)
        self.tab_view.add("Descargar")
        self.single_tab = SingleDownloadTab(master=self.tab_view.tab("Descargar"), app=self)

        # Las pestañas secundarias se importan y construyen cuando se abren.
        # Esto evita crear cientos de widgets invisibles durante el arranque.
        self._lazy_tabs = {}
        self._poppler_path = poppler_path
        self._inkscape_path = inkscape_path
        self._register_lazy_tab("Cola", "batch_tab", "src.gui.batch_download_tab")
        self._register_lazy_tab("Estudio de Imagen", "image_tab", "src.gui.image_tools_tab")
        self._register_lazy_tab("Configuración", "config_tab", "src.gui.config_tab")

        # La consola permanece pasiva hasta que Configuración se construya.
        self.console_logger = ConsoleLogger()

        # Se lanza con un delay para que MainWindow esté mapeada y evitar errores de hilos
        self.after(200, self.run_initial_setup)
        self._check_for_ui_requests()
        self._last_clipboard_check = ""
        self._clipboard_after_id = None
        self.bind("<FocusIn>", self._on_app_focus)
        self.after(100, self._show_window_when_ready)
        self.after(180000, self._start_memory_cleaner)
        self.after(5000, lambda: threading.Thread(target=self._check_ytdlp_update_bg, daemon=True).start())

    def _register_lazy_tab(self, tab_name, attribute_name, module_name):
        """Crea un contenedor ligero y difiere la pestaña real hasta su uso."""
        self.tab_view.add(tab_name)
        container = self.tab_view.tab(tab_name)
        # El panel real se construye en un host todavía oculto. Así CustomTkinter
        # puede crear sus widgets sin mezclar una interfaz parcial con el aviso.
        host = ctk.CTkFrame(container, fg_color="transparent")
        placeholder = ctk.CTkFrame(container, fg_color="transparent")
        placeholder.pack(expand=True, fill="both")
        content = ctk.CTkFrame(
            placeholder,
            width=360,
            height=128,
            corner_radius=16,
            border_width=1,
            border_color=("gray78", "gray28"),
            fg_color=("gray94", "gray17"),
        )
        content.pack_propagate(False)
        content.place(relx=0.5, rely=0.48, anchor="center")
        label = ctk.CTkLabel(
            content,
            text=f"Abriendo {tab_name}…",
            font=ctk.CTkFont(size=15, weight="bold"),
            text_color=("gray25", "gray82"),
        )
        label.pack(pady=(24, 4))
        detail = ctk.CTkLabel(
            content,
            text="Solo tardará la primera vez.",
            font=ctk.CTkFont(size=12),
            text_color=("gray45", "gray62"),
        )
        detail.pack(pady=(0, 12))
        progress = ctk.CTkProgressBar(content, width=250, height=6, mode="indeterminate")
        progress.set(0)
        progress.pack()
        self._lazy_tabs[tab_name] = {
            "attribute": attribute_name,
            "module": module_name,
            "state": "pending",
            "container": container,
            "host": host,
            "placeholder": placeholder,
            "label": label,
            "detail": detail,
            "progress": progress,
            "retry": None,
        }

    def _ensure_lazy_tab(self, tab_name):
        spec = self._lazy_tabs.get(tab_name)
        if not spec or spec["state"] in {"loading", "building", "loaded"}:
            return
        if spec["state"] == "ready":
            self._finish_lazy_tab(tab_name)
            return

        spec["state"] = "loading"
        retry = spec.get("retry")
        if retry and retry.winfo_exists():
            retry.destroy()
        spec["retry"] = None
        spec["label"].configure(text=f"Abriendo {tab_name}…")
        spec["detail"].configure(text="Solo tardará la primera vez.")
        spec["progress"].start()

        threading.Thread(
            target=self._import_lazy_tab,
            args=(tab_name, spec["module"]),
            daemon=True,
        ).start()

    def _import_lazy_tab(self, tab_name, module_name):
        try:
            import importlib

            importlib.import_module(module_name)
        except Exception as error:
            self.ui_update_queue.put((self._fail_lazy_tab, (tab_name, str(error))))
            return
        self.ui_update_queue.put((self._finish_lazy_tab, (tab_name,)))

    def _finish_lazy_tab(self, tab_name):
        if self.is_shutting_down:
            return
        spec = self._lazy_tabs[tab_name]
        if spec["state"] == "loaded":
            return
        if self.tab_view.get() != tab_name:
            spec["state"] = "ready"
            spec["progress"].stop()
            spec["label"].configure(text="Lista para abrir.")
            spec["detail"].configure(text="Selecciona la pestaña para mostrarla.")
            return
        spec["state"] = "building"
        spec["label"].configure(text=f"Abriendo {tab_name}…")
        spec["detail"].configure(text="Preparando la interfaz.")
        try:
            host = spec["host"]
            if tab_name == "Cola":
                from .batch_download_tab import BatchDownloadTab

                widget = BatchDownloadTab(master=host, app=self)
            elif tab_name == "Estudio de Imagen":
                from .image_tools_tab import ImageToolsTab

                widget = ImageToolsTab(
                    master=host,
                    app=self,
                    poppler_path=self._poppler_path,
                    inkscape_path=self._inkscape_path,
                )
            else:
                from .config_tab import ConfigTab

                widget = ConfigTab(master=host, app=self)
        except Exception as error:
            self._fail_lazy_tab(tab_name, str(error))
            return

        setattr(self, spec["attribute"], widget)
        spec["progress"].stop()
        spec["placeholder"].destroy()
        spec["host"].pack(expand=True, fill="both")
        spec["state"] = "loaded"

        if tab_name == "Configuración":
            self.console_logger.connect_ui(
                after_func=self.after,
                ui_callback=self.config_tab.append_to_console,
            )
            if self.console_enabled:
                self.console_logger.enable()

    def _fail_lazy_tab(self, tab_name, error_message):
        spec = self._lazy_tabs[tab_name]
        spec["state"] = "error"
        spec["progress"].stop()
        host = spec.get("host")
        if host and host.winfo_exists():
            host.destroy()
        spec["host"] = ctk.CTkFrame(spec["container"], fg_color="transparent")
        spec["label"].configure(
            text=f"No se pudo abrir {tab_name}.\n{error_message[:180]}",
            text_color=("#B42318", "#FF8A80"),
        )
        spec["detail"].configure(text="Puedes volver a intentarlo.")
        spec["retry"] = ctk.CTkButton(
            spec["label"].master,
            text="Reintentar",
            width=120,
            command=lambda: self._ensure_lazy_tab(tab_name),
        )
        spec["retry"].pack(pady=(12, 0))

    def _on_tab_view_change(self):
        """Carga bajo demanda la pestaña elegida sin penalizar el arranque."""
        self._ensure_lazy_tab(self.tab_view.get())

    def _check_ytdlp_update_bg(self):
        """Busca actualizaciones exclusivas de yt-dlp silenciosamente al iniciar."""
        from src.core.setup import get_latest_ytdlp_info
        from main import BIN_DIR
        import os
        from packaging import version
        
        ytdlp_path = os.path.join(BIN_DIR, "ytdlp", "ytdlp_version.txt")
        local_ytdlp = "No encontrado"
        if os.path.exists(ytdlp_path):
            with open(ytdlp_path, 'r') as f:
                local_ytdlp = f.read().strip()
                
        if local_ytdlp == "No encontrado":
            return
            
        latest_ytdlp, download_url = get_latest_ytdlp_info(lambda t, v: None)
        if not latest_ytdlp or not download_url:
            return
            
        try:
            local_v = version.parse(local_ytdlp)
            latest_v = version.parse(latest_ytdlp)
            if latest_v > local_v:
                self.ui_update_queue.put((self._prompt_ytdlp_update, (local_ytdlp, latest_ytdlp, download_url)))
        except Exception:
            pass

    def _prompt_ytdlp_update(self, local_v, latest_v, url):
        from tkinter import messagebox
        Tooltip.hide_all()
        response = messagebox.askyesno(
            "Nueva versión del motor",
            f"Se ha detectado una nueva versión del motor yt-dlp.\n\n"
            f"Versión actual: {local_v}\n"
            f"Versión nueva: {latest_v}\n\n"
            "Es altamente recomendable mantenerlo al día. ¿Deseas descargarla e instalarla ahora?"
        )
        self.lift()
        if response:
            self._start_ytdlp_download(latest_v, url)

    def _start_ytdlp_download(self, latest_v, url):
        self.single_tab.update_progress(0, f"Iniciando descarga de yt-dlp {latest_v}...")
        self.single_tab.download_button.configure(state="disabled")
        
        def download_task():
            from src.core.setup import download_and_install_ytdlp
            
            def progress_safe(text, val, *args):
                self.ui_update_queue.put((self.single_tab.update_progress, (val, text)))

            success = download_and_install_ytdlp(latest_v, url, progress_safe)
            self.ui_update_queue.put((self._on_ytdlp_download_complete, (success, latest_v)))

        import threading
        threading.Thread(target=download_task, daemon=True).start()

    def _on_ytdlp_download_complete(self, success, latest_v):
        self.single_tab.update_progress(100 if success else 0, "✅ yt-dlp actualizado. Requiere reinicio." if success else "Error descargando yt-dlp.")
        self.single_tab.download_button.configure(state="normal")
        
        if success:
            config_tab = getattr(self, "config_tab", None)
            if config_tab and "ytdlp" in config_tab.dep_labels:
                config_tab.dep_labels["ytdlp"].configure(text=f"Versión: {latest_v} \n(Actualizado)", text_color="gray50")
                if "ytdlp" in config_tab.dep_buttons:
                    config_tab.dep_buttons["ytdlp"].configure(state="disabled", text="Actualizado")
                
            from tkinter import messagebox
            Tooltip.hide_all()
            if messagebox.askyesno("Reinicio Necesario", "Se actualizó yt-dlp exitosamente.\n\nEs OBLIGATORIO reiniciar Xomacito para evitar fallos. ¿Reiniciar ahora?"):
                self.restart_application()

    def _process_ui_queue(self):
        """Procesa trabajo de UI con un presupuesto corto para no bloquear frames."""
        deadline = time.monotonic() + 0.008
        processed = 0
        try:
            while processed < 48 and time.monotonic() < deadline:
                task = self.ui_update_queue.get_nowait()
                func, args = task
                try:
                    func(*args)
                except Exception as e:
                    print(f"ERROR al procesar tarea de UI: {e}")
                processed += 1
        except queue.Empty:
            pass
        finally:
            # Si quedó trabajo, continuar pronto; en reposo basta con ~30 FPS.
            delay = 8 if not self.ui_update_queue.empty() else 34
            if not getattr(self, "is_shutting_down", False):
                self.after(delay, self._process_ui_queue)
    
    def run_initial_setup(self):
        """
        Inicia la aplicación, configura la UI y lanza las comprobaciones de dependencias.
        """
        print("INFO: Configurando UI y lanzando comprobaciones de inicio...")

        # La versión se consulta en segundo plano. Si ya está al día, la UI no
        # muestra nada; únicamente se pregunta cuando GitHub publica una mayor.
        from src.core.app_updater import check_for_app_update
        threading.Thread(
            target=lambda: self.ui_update_queue.put((
                self.on_update_check_complete,
                (check_for_app_update(self.APP_VERSION),),
            )),
            daemon=True,
        ).start()

        # 3. COMPROBACIÓN DE DEPENDENCIAS OBLIGATORIAS
        import platform
        exe_ext = ".exe" if platform.system() == "Windows" else ""
        
        mandatory_deps = {
            "ffmpeg": os.path.join(FFMPEG_BIN_DIR, f"ffmpeg{exe_ext}"),
            "deno": os.path.join(DENO_BIN_DIR, f"deno{exe_ext}"),
            "poppler": os.path.join(POPPLER_BIN_DIR, f"pdfinfo{exe_ext}"),
            "ytdlp": os.path.join(BIN_DIR, "ytdlp", "yt-dlp.zip")
        }
        
        missing_deps = [name for name, path in mandatory_deps.items() if not os.path.isfile(path)]
        if missing_deps:
            print(
                "ADVERTENCIA: Faltan componentes empaquetados: "
                f"{', '.join(missing_deps)}. Xomacito no descargará dependencias al iniciar; "
                "pueden repararse manualmente desde Configuración > Dependencias."
            )

        # 4. Finalizar carga: Poblar versiones y detectar códecs (En segundo plano para no congelar la UI)
        def finalize_setup_thread():
            try:
                from src.core.setup import check_environment_status 
                
                # Hacemos una verificación rápida (offline) para llenar las etiquetas de la UI
                env_status = check_environment_status(lambda t, v: None, check_updates=False)
                
                # Enviamos la actualización de la UI a la cola principal
                self.ui_update_queue.put((self.on_status_check_complete, (env_status,)))
                
                # Detección de códecs FFmpeg
                self.ffmpeg_processor.run_detection_async(self.on_ffmpeg_detection_complete)

                # Gestión de rembg (Lazy loading)
                self.ui_update_queue.put((
                    lambda: self.single_tab.rembg_status_label.configure(text="Modelos IA: Bajo Demanda\n(Se descargarán al usar)"),
                    ()
                ))
            except Exception as e:
                print(f"ERROR en hilo de finalización de carga: {e}")

        threading.Thread(target=finalize_setup_thread, daemon=True).start()
        self.after(900, self._show_release_notice_once)

    def _show_release_notice_once(self):
        """Muestra las novedades de esta versión una sola vez por instalación."""
        if self.is_shutting_down or self.release_notice_seen_version == self.APP_VERSION:
            return

        from src.core.app_updater import release_notice_for_version

        notice = release_notice_for_version(self.APP_VERSION)
        if not notice:
            return

        # Persistir antes del diálogo evita repetirlo si Windows cierra la app
        # mientras la ventana está abierta.
        self.release_notice_seen_version = self.APP_VERSION
        self.save_settings()
        Tooltip.hide_all()
        messagebox.showinfo(notice["title"], notice["message"], parent=self)
        self.lift()
        self.focus_force()
        
    def on_update_check_complete(self, update_info):
        """Ofrece una actualización solamente cuando la versión remota es mayor."""
        if self.is_shutting_down or getattr(self, "_update_in_progress", False):
            return

        if update_info.get("error"):
            print(f"ADVERTENCIA: {update_info['error']}")
            return

        if not update_info.get("update_available"):
            latest = update_info.get("latest_version", self.APP_VERSION)
            print(f"INFO: Xomacito {self.APP_VERSION} está al día (última: {latest}).")
            return

        latest_version = update_info.get("latest_version", "nueva")
        if not update_info.get("installer_url"):
            print("ADVERTENCIA: La versión nueva no tiene un instalador válido.")
            return

        from src.core.app_updater import build_update_prompt

        Tooltip.hide_all()
        accepted = messagebox.askyesno(
            "Nueva versión de Xomacito",
            build_update_prompt(update_info, self.APP_VERSION),
            parent=self,
        )
        self.lift()
        self.focus_force()
        if accepted:
            self._iniciar_auto_actualizacion(update_info)
        else:
            print(f"INFO: El usuario pospuso la actualización {latest_version}.")


    def on_status_check_complete(self, status_info, force_check=False):
        """
        Callback FINAL que gestiona el estado de FFmpeg.
        """
        # El arranque es estrictamente offline y nunca instala componentes.
        # Las descargas solo pueden iniciarse desde una comprobación manual.
        if not force_check:
            if status_info.get("status") == "error":
                print(f"ADVERTENCIA: Verificación local incompleta: {status_info.get('message')}")
                return

            missing = [
                label
                for key, label in (
                    ("ffmpeg_path_exists", "FFmpeg"),
                    ("deno_path_exists", "Deno"),
                    ("poppler_path_exists", "Poppler"),
                    ("ytdlp_path_exists", "yt-dlp"),
                )
                if not status_info.get(key)
            ]
            if missing:
                print(
                    "ADVERTENCIA: Componentes no disponibles al iniciar: "
                    f"{', '.join(missing)}. No se realizará ninguna descarga automática."
                )
            return

        status = status_info.get("status")
        
        if status == "error":
            Tooltip.hide_all()
            messagebox.showerror("Error Crítico de Entorno", status_info.get("message"))
            return

        # --- Variables de FFmpeg ---
        local_version = status_info.get("local_version") or "No encontrado"
        latest_version = status_info.get("latest_version")
        download_url = status_info.get("download_url")
        ffmpeg_exists = status_info.get("ffmpeg_path_exists")
        
        # --- Variables de Deno ---
        local_deno_version = status_info.get("local_deno_version") or "No encontrado"
        latest_deno_version = status_info.get("latest_deno_version")
        deno_download_url = status_info.get("deno_download_url")
        deno_exists = status_info.get("deno_path_exists")
        
        should_download = False
        should_download_deno = False

        # --- Variables de Poppler ---
        local_poppler_version = status_info.get("local_poppler_version") or "No encontrado"
        latest_poppler_version = status_info.get("latest_poppler_version")
        poppler_download_url = status_info.get("poppler_download_url")
        poppler_exists = status_info.get("poppler_path_exists")
        
        should_download_poppler = False # <--- IMPORTANTE
        
        # --- Variables de yt-dlp ---
        local_ytdlp_version = status_info.get("local_ytdlp_version") or "No encontrado"
        latest_ytdlp_version = status_info.get("latest_ytdlp_version")
        ytdlp_download_url = status_info.get("ytdlp_download_url")
        ytdlp_exists = status_info.get("ytdlp_path_exists")

        should_download_ytdlp = False
        
        # Desde aquí solo se procesan comprobaciones manuales.
        if not ffmpeg_exists:
            print("INFO: Comprobación manual de FFmpeg. No está instalado.")
            Tooltip.hide_all()
            user_response = messagebox.askyesno(
                "FFmpeg no está instalado",
                f"No se encontró FFmpeg. Es necesario para todas las descargas y recodificaciones.\n\n"
                f"Versión más reciente disponible: {latest_version}\n\n"
                "¿Deseas descargarlo e instalarlo ahora?"
            )
            self.lift()
            if user_response:
                should_download = True
            else:
                print("INFO: Instalación de FFmpeg cancelada por el usuario.")

        if not deno_exists:
            print("INFO: Comprobación manual de Deno. No está instalado.")
            Tooltip.hide_all()
            user_response = messagebox.askyesno(
                "Deno no está instalado",
                f"No se encontró Deno. Es necesario para algunas descargas.\n\n"
                f"Versión más reciente disponible: {latest_deno_version}\n\n"
                "¿Deseas descargarlo e instalarlo ahora?"
            )
            self.lift()
            if user_response:
                should_download_deno = True
            else:
                print("INFO: Instalación de Deno cancelada por el usuario.")

        # --- Lógica de descarga de Poppler ---
        if not poppler_exists:
            print("INFO: Comprobación manual de Poppler. No está instalado.")
            Tooltip.hide_all()
            user_response = messagebox.askyesno(
                "Poppler no está instalado",
                f"No se encontró Poppler. Es necesario para procesar imágenes.\n\n"
                f"Versión disponible: {latest_poppler_version}\n\n"
                "¿Deseas descargarlo e instalarlo ahora?"
            )
            self.lift()
            if user_response:
                should_download_poppler = True
            else:
                print("INFO: Instalación de Poppler cancelada por el usuario.")

        # --- Lógica de descarga de yt-dlp ---
        if not ytdlp_exists:
            print("INFO: Comprobación manual de yt-dlp. No está instalado.")
            Tooltip.hide_all()
            user_response = messagebox.askyesno(
                "yt-dlp no está instalado",
                f"No se encontró yt-dlp. Es necesario para procesar descargas.\n\n"
                f"Versión disponible: {latest_ytdlp_version}\n\n"
                "¿Deseas descargarlo e instalarlo ahora?"
            )
            self.lift()
            if user_response:
                should_download_ytdlp = True
            else:
                print("INFO: Instalación de yt-dlp cancelada por el usuario.")

        # --- Hilo de Descarga de FFmpeg (Sin cambios) ---
        if should_download:
            if not download_url:
                Tooltip.hide_all()
                messagebox.showerror("Error", "No se pudo obtener la URL de descarga para FFmpeg.")
                return

            self.config_tab.update_setup_download_progress('ffmpeg', f"Iniciando descarga de FFmpeg {latest_version}...", 0.01)
            from src.core.setup import download_and_install_ffmpeg

            def download_task():
                # Usar un callback seguro para el progreso
                def progress_safe(text, val):
                    self.ui_update_queue.put((self.config_tab.update_setup_download_progress, ('ffmpeg', text, val)))

                success = download_and_install_ffmpeg(latest_version, download_url, progress_safe) 

                if success:
                    ffmpeg_bin_path = os.path.join(BIN_DIR, "ffmpeg")
                    if ffmpeg_bin_path not in os.environ['PATH']:
                        os.environ['PATH'] = ffmpeg_bin_path + os.pathsep + os.environ['PATH']

                    # USAR COLA PARA TODO
                    self.ui_update_queue.put((
                        self.ffmpeg_processor.run_detection_async, 
                        (lambda s, m: self.on_ffmpeg_detection_complete(s, m, show_ready_message=True),)
                    ))
                    self.ui_update_queue.put((
                        self.config_tab.update_setup_download_progress, 
                        ('ffmpeg', f"✅ FFmpeg {latest_version} instalado.", 100)
                    ))
                    # Recargamos su versión de UI
                    self.ui_update_queue.put((self.config_tab._load_local_versions, ()))
                else:
                    self.ui_update_queue.put((
                        self.config_tab.update_setup_download_progress, 
                        ('ffmpeg', "Falló la descarga de FFmpeg.", 0)
                    ))

            threading.Thread(target=download_task, daemon=True).start()

        # --- Hilo de Descarga de Deno (MODIFICADO) ---
        if should_download_deno:
            if not deno_download_url:
                Tooltip.hide_all()
                messagebox.showerror("Error", "No se pudo obtener la URL de descarga para Deno.")
                return

            self.config_tab.update_setup_download_progress('deno', f"Iniciando descarga de Deno {latest_deno_version}...", 0.01)
            from src.core.setup import download_and_install_deno

            def download_deno_task():
                def progress_safe(text, val):
                    self.ui_update_queue.put((self.config_tab.update_setup_download_progress, ('deno', text, val)))

                success = download_and_install_deno(latest_deno_version, deno_download_url, progress_safe) 

                if success:
                    deno_bin_path = os.path.join(BIN_DIR, "deno")
                    if deno_bin_path not in os.environ['PATH']:
                        os.environ['PATH'] = deno_bin_path + os.pathsep + os.environ['PATH']

                    self.ui_update_queue.put((
                        lambda: self.config_tab.dep_labels["deno"].configure(text=f"Versión: {latest_deno_version} \n(Instalado)"), 
                        ()
                    ))
                    self.ui_update_queue.put((
                        self.config_tab.update_setup_download_progress, 
                        ('deno', f"✅ Deno {latest_deno_version} instalado.", 100)
                    ))
                else:
                    self.ui_update_queue.put((
                        self.config_tab.update_setup_download_progress, 
                        ('deno', "Falló la descarga de Deno.", 0)
                    ))

            threading.Thread(target=download_deno_task, daemon=True).start()

        # --- Hilo de Descarga de Poppler ---
        if should_download_poppler:
            if not poppler_download_url:
                if force_check:
                    Tooltip.hide_all()
                    messagebox.showerror("Error", "No se pudo obtener la URL de Poppler.")
                return

            self.config_tab.update_setup_download_progress('poppler', f"Descargando Poppler {latest_poppler_version}...", 0.01)
            from src.core.setup import download_and_install_poppler

            def download_poppler_task():
                def progress_safe(text, val):
                    self.ui_update_queue.put((self.config_tab.update_setup_download_progress, ('poppler', text, val)))

                success = download_and_install_poppler(latest_poppler_version, poppler_download_url, progress_safe) 
                
                if success:
                    poppler_bin_path = os.path.join(BIN_DIR, "poppler")
                    if poppler_bin_path not in os.environ['PATH']:
                        os.environ['PATH'] = poppler_bin_path + os.pathsep + os.environ['PATH']
                    
                    self.ui_update_queue.put((
                        lambda: self.config_tab.dep_labels["poppler"].configure(text=f"Versión: {latest_poppler_version} \n(Instalado)"),
                        ()
                    )) 
                    self.ui_update_queue.put((
                        self.config_tab.update_setup_download_progress, 
                        ('poppler', f"✅ Poppler instalado.", 100)
                    ))
                else:
                    self.ui_update_queue.put((
                        self.config_tab.update_setup_download_progress, 
                        ('poppler', "Falló la descarga de Poppler.", 0)
                    ))

            threading.Thread(target=download_poppler_task, daemon=True).start()

    def on_ytdlp_check_complete(self, status_info, force_check=False):
        """Callback que gestiona el estado de la actualización de yt-dlp."""
        status = status_info.get("status")

        self.config_tab.dep_buttons["ytdlp"].configure(state="normal", text="Buscar Actualización")

        if status == "error":
            Tooltip.hide_all()
            messagebox.showerror("Error de yt-dlp", status_info.get("message"))
            return

        local_version = status_info.get("local_ytdlp_version") or "No encontrado"
        latest_version = status_info.get("latest_ytdlp_version")
        download_url = status_info.get("ytdlp_download_url")
        ytdlp_exists = status_info.get("ytdlp_path_exists")

        should_download = False

        if not ytdlp_exists:
            if not force_check:
                should_download = True
            else:
                Tooltip.hide_all()
                user_response = messagebox.askyesno(
                    "yt-dlp no está instalado",
                    f"No se encontró el ejecutable/zip de yt-dlp.\n\n"
                    f"Versión más reciente disponible: {latest_version}\n\n"
                    "¿Deseas descargarlo ahora?"
                )
                self.lift()
                if user_response:
                    should_download = True
                else:
                    self.config_tab.dep_labels["ytdlp"].configure(text=f"Versión: {local_version} (Instalación cancelada)")
        else:
            update_available = False
            try:
                if latest_version and local_version != latest_version:
                    update_available = True
            except Exception as e:
                update_available = False

            if update_available and force_check:
                Tooltip.hide_all()
                user_response = messagebox.askyesno(
                    "Actualización Disponible",
                    f"Hay una nueva versión de yt-dlp disponible.\n\n"
                    f"Actual: {local_version} -> Nueva: {latest_version}\n\n"
                    "¿Actualizar ahora?"
                )
                self.lift()
                if user_response:
                    should_download = True
            elif update_available:
                self.config_tab.dep_labels["ytdlp"].configure(text=f"Versión: {local_version} (Update disp.)", text_color="#E5A04B")
            else:
                self.config_tab.dep_labels["ytdlp"].configure(text=f"Versión: {local_version} (Instalado)")
                if force_check:
                    messagebox.showinfo("yt-dlp", "yt-dlp está actualizado.")
        # --- Hilo de Descarga de FFmpeg (Sin cambios) ---

    def on_ffmpeg_detection_complete(self, success, message, show_ready_message=False):
        # 1. Definir la lógica de actualización
        def update_ui():
            if success:
                self.single_tab.recode_video_checkbox.configure(text="Recodificar Video", state="normal") 
                self.single_tab.recode_audio_checkbox.configure(text="Recodificar Audio", state="normal")
                self.single_tab.apply_quick_preset_checkbox.configure(text="Activar recodificación Rápida", state="normal")
                
                if self.ffmpeg_processor.gpu_vendor:
                    self.single_tab.gpu_radio.configure(text="GPU", state="normal")
                    self.single_tab.cpu_radio.pack_forget() 
                    self.single_tab.gpu_radio.pack_forget() 
                    self.single_tab.gpu_radio.pack(side="left", padx=10) 
                    self.single_tab.cpu_radio.pack(side="left", padx=20) 
                else:
                    self.single_tab.gpu_radio.configure(text="GPU (No detectada)")
                    self.single_tab.proc_type_var.set("CPU") 
                    self.single_tab.gpu_radio.configure(state="disabled") 
                
                self.single_tab.update_codec_menu()
                
                if show_ready_message:
                    self.single_tab.update_progress(100, "✅ FFmpeg instalado correctamente. Listo para usar.") 
            else:
                print(f"FFmpeg detection error: {message}")
                self.single_tab.recode_video_checkbox.configure(text="Recodificación no disponible", state="disabled") 
                self.single_tab.recode_audio_checkbox.configure(text="(Error FFmpeg)", state="disabled") 
                self.single_tab.apply_quick_preset_checkbox.configure(text="Recodificación no disponible (Error FFmpeg)", state="disabled") 
                self.single_tab.apply_quick_preset_checkbox.deselect() 

        # 2. SOLUCIÓN: Usar la cola en lugar de self.after
        self.ui_update_queue.put((update_ui, ()))

    def _iniciar_auto_actualizacion(self, update_info):
        """Descarga y verifica el setup; el usuario ya autorizó la instalación."""
        active_thread = getattr(self.single_tab, "active_operation_thread", None)
        if active_thread and active_thread.is_alive():
            Tooltip.hide_all()
            messagebox.showwarning(
                "Actualización pendiente",
                "Espera a que termine la operación activa y vuelve a abrir Xomacito "
                "para actualizar.",
                parent=self,
            )
            return

        from src.core.app_updater import download_installer

        version_str = update_info.get("latest_version", "nueva")
        self._update_in_progress = True
        self.single_tab.update_progress(0, f"Descargando Xomacito {version_str}...")
        try:
            self.attributes("-disabled", True)
        except tkinter.TclError:
            pass

        def report_progress(downloaded, total):
            percentage = (downloaded / total * 100.0) if total else -1
            message = (
                f"Actualizando: {downloaded / (1024 * 1024):.1f} de "
                f"{total / (1024 * 1024):.1f} MB"
            )
            self.ui_update_queue.put((self.single_tab.update_progress, (percentage, message)))

        def download_worker():
            try:
                installer_path = download_installer(update_info, progress_callback=report_progress)
                self.ui_update_queue.put((
                    self._ejecutar_instalador_actualizacion,
                    (installer_path, version_str),
                ))
            except Exception as error:
                self.ui_update_queue.put((self._fallo_auto_actualizacion, (str(error),)))

        threading.Thread(target=download_worker, daemon=True).start()

    def _ejecutar_instalador_actualizacion(self, installer_path, version_str):
        """Cierra Xomacito y deja que un lanzador independiente inicie el setup."""
        from src.core.app_updater import deferred_installer_command

        try:
            self.single_tab.update_progress(100, "Instalador verificado. Actualizando...")
            self.save_settings()
            creationflags = 0
            if os.name == "nt":
                creationflags = subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.CREATE_NO_WINDOW
            subprocess.Popen(
                deferred_installer_command(installer_path, os.getpid()),
                cwd=str(Path(installer_path).parent),
                creationflags=creationflags,
                close_fds=True,
            )
        except OSError as error:
            self._fallo_auto_actualizacion(str(error))
            return

        print(f"INFO: Instalador de Xomacito {version_str} iniciado.")
        self.is_shutting_down = True
        self.after(100, self.destroy)

    def _fallo_auto_actualizacion(self, error_message):
        self._update_in_progress = False
        try:
            self.attributes("-disabled", False)
        except tkinter.TclError:
            pass
        self.single_tab.update_progress(0, "No se pudo completar la actualización.")
        Tooltip.hide_all()
        messagebox.showerror(
            "No se pudo actualizar Xomacito",
            f"La aplicación seguirá abierta y no se modificó.\n\n{error_message}",
            parent=self,
        )

    def _check_for_ui_requests(self):
        """
        Verifica si un hilo secundario ha solicitado una acción de UI.
        """
        if self.ui_request_event.is_set(): # CORREGIDO
            self.ui_request_event.clear() # CORREGIDO
            request_type = self.ui_request_data.get("type") # CORREGIDO

            if request_type == "ask_yes_no":
                title = self.ui_request_data.get("title", "Confirmar") # CORREGIDO
                message = self.ui_request_data.get("message", "¿Estás seguro?") # CORREGIDO
                
                Tooltip.hide_all()
                result = messagebox.askyesno(title, message)
                
                self.ui_response_data["result"] = result # CORREGIDO
                self.lift() # CORREGIDO
                self.ui_response_event.set() # CORREGIDO

            elif request_type == "ask_conflict":
                filename = self.ui_request_data.get("filename", "") # CORREGIDO
                dialog = ConflictDialog(self, filename)


                self.wait_window(dialog) # CORREGIDO
                self.lift() # CORREGIDO
                self.focus_force() # CORREGIDO
                self.ui_response_data["result"] = dialog.result # CORREGIDO
                self.ui_response_event.set() # CORREGIDO
                
            elif request_type == "ask_compromise":
                details = self.ui_request_data.get("details", "Detalles no disponibles.") 
                dialog = CompromiseDialog(self, details)
                self.wait_window(dialog) 
                self.lift() 
                self.focus_force() 
                self.ui_response_data["result"] = dialog.result 
                self.ui_response_event.set() 
            
            elif request_type == "ask_playlist_error":
                url_fragment = self.ui_request_data.get("filename", "esta URL")
                dialog = PlaylistErrorDialog(self, url_fragment)
                
                self.wait_window(dialog)
                self.lift()
                self.focus_force()
                self.ui_response_data["result"] = dialog.result
                self.ui_response_event.set()
                
        self.after(100, self._check_for_ui_requests) # CORREGIDO

    def save_settings(self):
        """
        Recopila todos los ajustes de la app y los guarda en app_settings.json.
        Esta es la ÚNICA función que debe escribir en el archivo.
        """
        # en los ajustes globales (como default_download_path).
        current_tab = self.tab_view.get()
        if current_tab == "Descargar":
             if hasattr(self, 'batch_tab'): self.batch_tab.save_settings()
             if hasattr(self, 'image_tab'): self.image_tab.save_settings() # <--- AÑADIR
             if hasattr(self, 'single_tab'): self.single_tab.save_settings()
        elif current_tab == "Cola":
             if hasattr(self, 'single_tab'): self.single_tab.save_settings()
             if hasattr(self, 'image_tab'): self.image_tab.save_settings() # <--- AÑADIR
             if hasattr(self, 'batch_tab'): self.batch_tab.save_settings()
        else: # <--- AÑADIR ESTE BLOQUE ELSE
             if hasattr(self, 'single_tab'): self.single_tab.save_settings()
             if hasattr(self, 'batch_tab'): self.batch_tab.save_settings()
             if hasattr(self, 'image_tab'): self.image_tab.save_settings()

        # 3. Crear el diccionario de configuración final
        settings_to_save = {
            "default_download_path": self.default_download_path,
            "batch_download_path": self.batch_download_path,
            "image_output_path": self.image_output_path,
            "ffmpeg_update_snooze_until": self.ffmpeg_update_snooze_until.isoformat() if self.ffmpeg_update_snooze_until else None,
            "custom_presets": self.custom_presets,

            # Cookies
            "cookies_path": self.cookies_path,
            "cookies_mode": self.cookies_mode_saved,
            "vector_dpi": self.vector_dpi,
            "preview_vector_dpi": self.preview_vector_dpi,
            "selected_browser": self.selected_browser_saved,
            "browser_profile": self.browser_profile_saved,

            # Pestaña Individual (Modo Rápido)
            "apply_quick_preset_enabled": self.apply_quick_preset_checkbox_state,
            "keep_original_quick_enabled": self.keep_original_quick_saved,
            "quick_preset_saved": self.quick_preset_saved,

            # Pestaña Individual (Modo Manual)
            "recode_settings": self.recode_settings,

            # Pestaña de Lotes
            "batch_playlist_analysis": self.batch_playlist_analysis_saved,
            "batch_fast_mode": self.batch_fast_mode_saved,

            # Herramientas de Imagen
            "image_settings": self.image_settings,
            "upscayl_custom_models": self.upscayl_custom_models,

            # Consola de Diagnóstico
            "console_enabled": self.console_enabled,
            "console_wrap": self.console_wrap,

            # Optimización de VRAM
            "keep_ai_models_in_memory": self.keep_ai_models_in_memory,
            "show_onnx_warning": self.show_onnx_warning,

            # Inkscape Externo
            "inkscape_enabled": self.inkscape_enabled,
            "inkscape_path": self.inkscape_path,
            "inkscape_version": getattr(self, 'inkscape_version', ""),
            "vector_force_background": getattr(self, 'vector_force_background', False),
            "selected_theme_accent": self.selected_theme_accent,
            "theme_selection_explicit": self.theme_selection_explicit,
            "appearance_mode": self.appearance_mode,
            "clean_titles": self.clean_titles,
            "release_notice_seen_version": self.release_notice_seen_version
        }

        # 4. Escribir en el archivo
        try:
            with open(self.SETTINGS_FILE, 'w') as f:
                json.dump(settings_to_save, f, indent=4)
        except IOError as e:
            print(f"ERROR: Fallo al guardar configuración central: {e}")

    def restart_application(self):
        """Inicia una instancia independiente antes de cerrar la actual."""
        active_thread = getattr(self.single_tab, "active_operation_thread", None)
        if active_thread and active_thread.is_alive():
            Tooltip.hide_all()
            messagebox.showwarning(
                "Reinicio pendiente",
                "Espera a que termine la operación activa antes de reiniciar Xomacito.",
            )
            return False

        self.save_settings()
        if getattr(sys, "frozen", False):
            command = [sys.executable]
            working_directory = str(Path(sys.executable).resolve().parent)
        else:
            command = [sys.executable, str(Path(PROJECT_ROOT) / "main.py")]
            working_directory = str(PROJECT_ROOT)

        try:
            subprocess.Popen(
                command,
                cwd=working_directory,
                env=clean_restart_environment(),
                close_fds=True,
            )
        except OSError as error:
            messagebox.showerror(
                "No se pudo reiniciar",
                f"Xomacito no pudo abrir una nueva instancia:\n\n{error}",
            )
            return False

        self.is_shutting_down = True
        self.after(250, self.destroy)
        return True

    def _on_restart_app(self):
        """Alias conservado para acciones antiguas de Configuración."""
        return self.restart_application()

    def on_closing(self):
        """
        Se ejecuta cuando el usuario intenta cerrar la ventana.
        Gestiona la cancelación, limpieza y confirmación de forma robusta.
        """
        if self.single_tab.active_operation_thread and self.single_tab.active_operation_thread.is_alive():
            Tooltip.hide_all()
            if messagebox.askokcancel("Confirmar Salida", "Hay una operación en curso. ¿Estás seguro de que quieres salir?"):
                self.is_shutting_down = True 
                self.attributes("-disabled", True)
                self.single_tab.progress_label.configure(text="Cancelando y limpiando, por favor espera...")
                self.cancellation_event.set()
                self.after(100, self._wait_for_thread_to_finish_and_destroy)
        else:
            self.save_settings() 
            self.destroy()

    def _wait_for_thread_to_finish_and_destroy(self):
        """
        Vigilante que comprueba si el hilo de trabajo ha terminado.
        Una vez que termina (después de su limpieza), cierra la ventana.
        """
        if self.single_tab.active_operation_thread and self.single_tab.active_operation_thread.is_alive():
            self.after(100, self._wait_for_thread_to_finish_and_destroy)
        else:
            self.save_settings() 
            self.destroy()

    def _on_app_focus(self, event=None):
        """
        Se llama cuando la ventana gana el foco.
        Protegido para no congelar si el portapapeles está ocupado.
        """
        # Solo chequear si la app no está ocupada procesando
        if self.single_tab.active_operation_thread and self.single_tab.active_operation_thread.is_alive():
            return

        # FocusIn también llega desde widgets hijos. Agrupar esos eventos evita
        # múltiples lecturas y repintados por un único clic del usuario.
        if self._clipboard_after_id:
            try:
                self.after_cancel(self._clipboard_after_id)
            except tkinter.TclError:
                pass
        self._clipboard_after_id = self.after(140, self._check_clipboard_and_paste)

    def _start_memory_cleaner(self):
        """Hace mantenimiento ligero sin expulsar páginas útiles de memoria."""
        if self.is_shutting_down:
            return
        active_thread = getattr(self.single_tab, "active_operation_thread", None)
        if not active_thread or not active_thread.is_alive():
            try:
                gc.collect(1)
            except Exception:
                pass
        self.after(180000, self._start_memory_cleaner)

    # --- ESTA ES LA FUNCIÓN ANTERIOR RENOMBRADA ---
    def _check_clipboard_and_paste(self, retry_count=0):
        """
        Comprueba el portapapeles y pega automáticamente si es una URL.
        Los reintentos usan ``after`` para no detener el hilo gráfico.
        """
        self._clipboard_after_id = None
        try:
            clipboard_content = self.clipboard_get()
        except tkinter.TclError:
            return
        except Exception as error:
            if retry_count < 3:
                self._clipboard_after_id = self.after(
                    25 * (retry_count + 1),
                    self._check_clipboard_and_paste,
                    retry_count + 1,
                )
            else:
                print(f"DEBUG: Portapapeles bloqueado o inaccesible: {error}")
            return

        # 1. Evitar re-pegar si el contenido no ha cambiado
        if not clipboard_content or clipboard_content == self._last_clipboard_check:
            return

        # 2. Actualizar el contenido "visto"
        self._last_clipboard_check = clipboard_content

        # 3. Validar si es una URL (regex simple)
        url_regex = re.compile(r'^(https|http)://[^\s/$.?#].[^\s]*$')
        if not url_regex.match(clipboard_content):
            return # No es una URL válida

        # 4. Determinar qué pestaña está activa (AHORA SÍ FUNCIONA)
        active_tab_name = self.tab_view.get()
        target_entry = None

        if active_tab_name == "Descargar":
            target_entry = self.single_tab.url_entry
        elif active_tab_name == "Cola":
            batch_tab = getattr(self, "batch_tab", None)
            target_entry = batch_tab.url_entry if batch_tab else None
        elif active_tab_name == "Estudio de Imagen":
            image_tab = getattr(self, "image_tab", None)
            target_entry = image_tab.url_entry if image_tab else None

        # 5. Pegar la URL, REEMPLAZANDO el contenido
        if target_entry:
            # Si el texto ya es el mismo, no hacer nada (evita re-pegar)
            if target_entry.get() == clipboard_content:
                return

            print(f"DEBUG: URL detectada en portapapeles. Reemplazando en '{active_tab_name}'.")
            target_entry.delete(0, 'end') # BORRAR contenido actual
            target_entry.insert(0, clipboard_content) # INSERTAR nuevo contenido
            
            # Actualizar el estado del botón en la pestaña individual
            if active_tab_name == "Descargar":
                self.single_tab.update_download_button_state()

    def on_ffmpeg_check_complete(self, status_info):
        """
        Callback que maneja la comprobación MANUAL de FFmpeg.
        """
        self.config_tab.dep_buttons["ffmpeg"].configure(state="normal", text="Buscar Actualización")

        status = status_info.get("status")
        if status == "error":
            Tooltip.hide_all()
            messagebox.showerror("Error Crítico de FFmpeg", status_info.get("message"))
            return

        local_version = status_info.get("local_version") or "No encontrado"
        latest_version = status_info.get("latest_version")
        download_url = status_info.get("download_url")
        ffmpeg_exists = status_info.get("ffmpeg_path_exists")
        force_safe = status_info.get("force_safe", False)
        should_download = False

        if force_safe:
            should_download = True
        elif not ffmpeg_exists:
            print("INFO: Comprobación manual de FFmpeg. No está instalado.")
            Tooltip.hide_all()
            user_response = messagebox.askyesno(
                "FFmpeg no está instalado",
                f"No se encontró FFmpeg. Es necesario para todas las descargas y recodificaciones.\n\n"
                f"Versión más reciente disponible: {latest_version}\n\n"
                "¿Deseas descargarlo e instalarlo ahora?"
            )
            self.lift()
            if user_response:
                should_download = True
            else:
                self.config_tab.dep_labels["ffmpeg"].configure(text=f"Versión: {local_version[:45] + '...' if len(local_version) > 45 else local_version} (Instalación cancelada)")
        else:
            update_available = False
            try:
                if latest_version:
                    local_v_str = re.search(r'v?(\d+\.\d+(\.\d+)?)', local_version).group(1) if local_version and re.search(r'v?(\d+\.\d+(\.\d+)?)', local_version) else "0"
                    latest_v_str = re.search(r'v?(\d+\.\d+(\.\d+)?)', latest_version).group(1) if latest_version and re.search(r'v?(\d+\.\d+(\.\d+)?)', latest_version) else "0"
                    local_v = version.parse(local_v_str)
                    latest_v = version.parse(latest_v_str)
                    if latest_v > local_v:
                        update_available = True
            except (version.InvalidVersion, AttributeError):
                update_available = local_version != latest_version

            snoozed = self.ffmpeg_update_snooze_until and datetime.now() < self.ffmpeg_update_snooze_until

            if update_available and not snoozed:
                Tooltip.hide_all()
                user_response = messagebox.askyesno(
                    "Actualización Disponible",
                    f"Hay una nueva versión de FFmpeg disponible.\n\n"
                    f"Versión Actual: {local_version}\n"
                    f"Versión Nueva: {latest_version}\n\n"
                    "¿Deseas actualizar ahora?"
                )
                self.lift() 
                if user_response:
                    should_download = True
                    self.ffmpeg_update_snooze_until = None 
                else:
                    self.ffmpeg_update_snooze_until = datetime.now() + timedelta(days=15)
                    self.config_tab.dep_labels["ffmpeg"].configure(text=f"Versión: {local_version[:45] + '...' if len(local_version) > 45 else local_version} (Actualización pospuesta)") 
                self.save_settings()
            elif update_available and snoozed:
                self.config_tab.dep_labels["ffmpeg"].configure(text=f"Versión: {local_version[:45] + '...' if len(local_version) > 45 else local_version} (Actualización pospuesta)") 
                Tooltip.hide_all()
                messagebox.showinfo("Actualización Pos puesta", "Hay una nueva versión de FFmpeg, pero la pospusiste. Puedes volver a comprobarla más tarde.")
            else:
                self.config_tab.dep_labels["ffmpeg"].configure(text=f"Versión: {local_version[:45] + '...' if len(local_version) > 45 else local_version} (Actualizado)")
                Tooltip.hide_all()
                messagebox.showinfo("FFmpeg", "Ya tienes la última versión de FFmpeg instalada.")

        if should_download:
            if not download_url:
                Tooltip.hide_all()
                messagebox.showerror("Error", "No se pudo obtener la URL de descarga para FFmpeg.")
                return

            self.config_tab.update_setup_download_progress('ffmpeg', f"Iniciando descarga de FFmpeg {latest_version}...", 0.01)
            from src.core.setup import download_and_install_ffmpeg

            def download_task():
                success = download_and_install_ffmpeg(latest_version, download_url, 
                    lambda text, val: self.config_tab.update_setup_download_progress('ffmpeg', text, val)) 
                if success:
                    ffmpeg_bin_path = os.path.join(BIN_DIR, "ffmpeg")
                    if ffmpeg_bin_path not in os.environ['PATH']:
                        os.environ['PATH'] = ffmpeg_bin_path + os.pathsep + os.environ['PATH']
                    self.after(0, self.ffmpeg_processor.run_detection_async,  
                            lambda s, m: self.on_ffmpeg_detection_complete(s, m, show_ready_message=True))
                    self.after(0, lambda: self.config_tab.dep_labels["ffmpeg"].configure(text=f"Versión: {latest_version[:45] + '...' if len(latest_version) > 45 else latest_version} (Instalado)")) 
                    self.after(0, self.config_tab.update_setup_download_progress, 'ffmpeg', f"✅ FFmpeg {latest_version[:20]} instalado.", 100)
                else:
                    self.after(0, self.config_tab.update_setup_download_progress, 'ffmpeg', "Falló la descarga de FFmpeg.", 0)

            threading.Thread(target=download_task, daemon=True).start()

    def on_deno_check_complete(self, status_info):
        """
        Callback que maneja la comprobación MANUAL de Deno.
        """
        self.config_tab.dep_buttons["deno"].configure(state="normal", text="Buscar Actualización")

        status = status_info.get("status")
        if status == "error":
            Tooltip.hide_all()
            messagebox.showerror("Error Crítico de Deno", status_info.get("message"))
            return

        local_deno_version = status_info.get("local_deno_version") or "No encontrado"
        latest_deno_version = status_info.get("latest_deno_version")
        deno_download_url = status_info.get("deno_download_url")
        deno_exists = status_info.get("deno_path_exists")
        should_download_deno = False

        if not deno_exists:
            print("INFO: Comprobación manual de Deno. No está instalado.")
            Tooltip.hide_all()
            user_response = messagebox.askyesno(
                "Deno no está instalado",
                f"No se encontró Deno. Es necesario para algunas descargas.\n\n"
                f"Versión más reciente disponible: {latest_deno_version}\n\n"
                "¿Deseas descargarlo e instalarlo ahora?"
            )
            self.lift()
            if user_response:
                should_download_deno = True
            else:
                self.config_tab.dep_labels["deno"].configure(text=f"Versión: {local_deno_version} \n(Instalación cancelada)")
        else:
            deno_update_available = False
            try:
                if latest_deno_version:
                    local_v = version.parse(local_deno_version.lstrip('v'))
                    latest_v = version.parse(latest_deno_version.lstrip('v'))
                    if latest_v > local_v:
                        deno_update_available = True
            except version.InvalidVersion:
                deno_update_available = local_deno_version != latest_deno_version

            if deno_update_available:
                Tooltip.hide_all()
                user_response = messagebox.askyesno(
                    "Actualización de Deno Disponible",
                    f"Hay una nueva versión de Deno disponible.\n\n"
                    f"Versión Actual: {local_deno_version}\n"
                    f"Versión Nueva: {latest_deno_version}\n\n"
                    "¿Deseas actualizar ahora?"
                )
                self.lift() 
                if user_response:
                    should_download_deno = True
            else:
                self.config_tab.dep_labels["deno"].configure(text=f"Versión: {local_deno_version} \n(Actualizado)")
                Tooltip.hide_all()
                messagebox.showinfo("Deno", "Ya tienes la última versión de Deno instalada.")

        if should_download_deno:
            if not deno_download_url:
                Tooltip.hide_all()
                messagebox.showerror("Error", "No se pudo obtener la URL de descarga para Deno.")
                return

            self.config_tab.update_setup_download_progress('deno', f"Iniciando descarga de Deno {latest_deno_version}...", 0.01)
            from src.core.setup import download_and_install_deno 

            def download_deno_task():
                success = download_and_install_deno(latest_deno_version, deno_download_url, 
                    lambda text, val: self.config_tab.update_setup_download_progress('deno', text, val)) 
                if success:
                    deno_bin_path = os.path.join(BIN_DIR, "deno")
                    if deno_bin_path not in os.environ['PATH']:
                        os.environ['PATH'] = deno_bin_path + os.pathsep + os.environ['PATH']
                    self.after(0, lambda: self.config_tab.dep_labels["deno"].configure(text=f"Versión: {latest_deno_version} \n(Instalado)")) 
                    self.after(0, self.config_tab.update_setup_download_progress, 'deno', f"✅ Deno {latest_deno_version} instalado.", 100)
                else:
                    self.after(0, self.config_tab.update_setup_download_progress, 'deno', "Falló la descarga de Deno.", 0)

            threading.Thread(target=download_deno_task, daemon=True).start()

    def _show_window_when_ready(self):
        """
        Muestra la ventana principal cuando todo está listo.
        Previene el parpadeo negro inicial.
        """
        try:
            # Forzar actualización de la geometría
            self.update_idletasks()
            
            # Mostrar la ventana principal
            self.deiconify()
            
            # 1. Cerrar la Splash Screen AHORA
            if self.splash_screen:
                self.splash_screen.destroy()
                self.splash_screen = None
            
            # (Ya no necesitamos reasignar el root aquí, lo hicimos en __init__)

            # Llevar al frente
            self.lift()
            self.focus_force()
            
            print("DEBUG: ✅ Ventana principal mostrada y Splash cerrado")
            
        except Exception as e:
            if self.splash_screen:
                try: self.splash_screen.destroy()
                except: pass
            print(f"ERROR mostrando ventana: {e}")
            self.deiconify()

    def on_poppler_check_complete(self, status_info):
        """Callback que maneja la comprobación MANUAL de Poppler."""
        self.config_tab.dep_buttons["poppler"].configure(state="normal", text="Buscar Actualización")

        status = status_info.get("status")
        if status == "error":
            Tooltip.hide_all()
            messagebox.showerror("Error Crítico de Poppler", status_info.get("message"))
            return

        local_version = status_info.get("local_poppler_version") or "No encontrado"
        latest_version = status_info.get("latest_poppler_version")
        download_url = status_info.get("poppler_download_url")
        poppler_exists = status_info.get("poppler_path_exists")
        should_download = False

        if not poppler_exists:
            print("INFO: Comprobación manual de Poppler. No está instalado.")
            Tooltip.hide_all()
            user_response = messagebox.askyesno(
                "Poppler no está instalado",
                f"No se encontró Poppler. Es necesario para procesar imágenes y PDFs.\n\n"
                f"Versión más reciente disponible: {latest_version}\n\n"
                "¿Deseas descargarlo e instalarlo ahora?"
            )
            self.lift()
            if user_response: should_download = True
            else: self.config_tab.dep_labels["poppler"].configure(text=f"Versión: {local_version} \n(Instalación cancelada)")
        else:
            # Lógica simple de comparación de strings para Poppler (sus tags son vXX.XX.X-X)
            update_available = local_version != latest_version
            
            if update_available:
                Tooltip.hide_all()
                user_response = messagebox.askyesno(
                    "Actualización de Poppler Disponible",
                    f"Hay una nueva versión de Poppler disponible.\n\n"
                    f"Versión Actual: {local_version}\n"
                    f"Versión Nueva: {latest_version}\n\n"
                    "¿Deseas actualizar ahora?"
                )
                self.lift()
                if user_response: should_download = True
            else:
                self.config_tab.dep_labels["poppler"].configure(text=f"Versión: {local_version} \n(Actualizado)")
                Tooltip.hide_all()
                messagebox.showinfo("Poppler", "Ya tienes la última versión de Poppler instalada.")

        if should_download:
            if not download_url:
                Tooltip.hide_all()
                messagebox.showerror("Error", "No se pudo obtener la URL de descarga para Poppler.")
                return

            self.config_tab.update_setup_download_progress('poppler', f"Iniciando descarga de Poppler {latest_version}...", 0.01)
            from src.core.setup import download_and_install_poppler 

            def download_task():
                success = download_and_install_poppler(latest_version, download_url, 
                    lambda text, val: self.config_tab.update_setup_download_progress('poppler', text, val)) 
                if success:
                    poppler_bin_path = os.path.join(BIN_DIR, "poppler")
                    if poppler_bin_path not in os.environ['PATH']:
                        os.environ['PATH'] = poppler_bin_path + os.pathsep + os.environ['PATH']
                    self.after(0, lambda: self.config_tab.dep_labels["poppler"].configure(text=f"Versión: {latest_version} \n(Instalado)")) 
                    self.after(0, self.config_tab.update_setup_download_progress, 'poppler', f"✅ Poppler {latest_version} instalado.", 100)
                else:
                    self.after(0, self.config_tab.update_setup_download_progress, 'poppler', "Falló la descarga de Poppler.", 0)

            threading.Thread(target=download_task, daemon=True).start()

    def on_inkscape_check_complete(self, status_info):
        """Callback tras verificar Inkscape."""
        # 1. Rehabilitar el botón de verificación
        if hasattr(self.config_tab, "ink_verify_btn"):
            self.config_tab.ink_verify_btn.configure(state="normal")
        
        # 2. Manejar errores de ejecución (fallos reales del comando)
        if status_info.get("status") == "error":
            if hasattr(self.config_tab, "ink_status_label"):
                self.config_tab.ink_status_label.configure(text="Versión: Error al verificar", text_color="red")
            print(f"INFO Inkscape: {status_info.get('message')}")
            return

        # 3. Actualizar estado según presencia
        exists = status_info.get("exists")
        version = status_info.get("version", "")
        self.inkscape_version = version

        if exists:
            if hasattr(self.config_tab, "ink_status_label"):
                self.config_tab.ink_status_label.configure(
                    text=f"✅ Detectado: {version}", text_color="#28a745"
                )
        else:
            if hasattr(self.config_tab, "ink_status_label"):
                # Si no existe, es INFO, no ERROR (es opcional)
                self.config_tab.ink_status_label.configure(
                    text="No encontrado (Opcional)", text_color="gray50"
                )
            if self.inkscape_enabled:
                print("INFO: Inkscape no encontrado en la ruta especificada. Se usarán motores nativos.")

    def on_ghostscript_check_complete(self, status_info):
        """Callback tras verificar Ghostscript."""
        if "ghostscript" in self.config_tab.dep_buttons:
            self.config_tab.dep_buttons["ghostscript"].configure(state="normal")
        
        if status_info.get("status") == "error":
            if "ghostscript" in self.config_tab.dep_labels:
                self.config_tab.dep_labels["ghostscript"].configure(text="Estado: Error al verificar", text_color="red")
            print(f"INFO Ghostscript: {status_info.get('message')}")
            return

        exists = status_info.get("exists")
        if exists:
            if "ghostscript" in self.config_tab.dep_labels:
                self.config_tab.dep_labels["ghostscript"].configure(
                    text="Estado: Detectado ✅", text_color="#28a745"
                )
        else:
            if "ghostscript" in self.config_tab.dep_labels:
                self.config_tab.dep_labels["ghostscript"].configure(
                    text="Estado: No encontrado (Opcional)", text_color="gray50"
                )

    def update_setup_progress(self, text, value):
        """
        Actualiza la ventana emergente de carga (LoadingWindow).
        Recibe texto y valor (0-100).
        """
        # Verificar que la ventana de carga exista antes de actualizarla
        if hasattr(self, 'loading_window') and self.loading_window and self.loading_window.winfo_exists():
            # Usamos lambda para asegurar que se ejecute en el hilo de la UI
            self.after(0, lambda: self.loading_window.update_progress(text, value / 100.0))
        
        # Si llega al 100%, cerrar
        if value >= 100:
            self.after(500, self.on_setup_complete)

    def on_setup_complete(self):
        """
        Se ejecuta cuando la configuración inicial (hilos) ha terminado.
        Cierra la ventana de carga y habilita la UI principal.
        """
        # 1. Gestionar la ventana de carga
        if hasattr(self, 'loading_window') and self.loading_window and self.loading_window.winfo_exists():
            if not self.loading_window.error_state:
                self.loading_window.update_progress("Configuración completada.", 1.0)
                # Dar un momento para leer "Completado" antes de cerrar
                self.after(800, self.loading_window.destroy)
            else:
                # Si hubo error crítico, quizás quieras dejarla abierta, 
                # pero por defecto la cerramos para no bloquear.
                self.loading_window.destroy()

        # 2. Habilitar la ventana principal
        self.attributes('-disabled', False)
        self.lift()
        self.focus_force()

        # 3. Aplicar configuraciones guardadas a la UI de la pestaña Single
        # (Como la lógica ahora está en MainWindow, debemos empujar los datos a single_tab)
        try:
            # Rutas
            self.single_tab.output_path_entry.delete(0, 'end')
            self.single_tab.output_path_entry.insert(0, self.default_download_path)
            
            # Cookies
            # La UI global en Ajustes ya usa `self.cookies_mode_saved` y compañía
            
            # Recodificación
            if self.recode_settings.get("keep_original", True):
                self.single_tab.keep_original_checkbox.select()
            else:
                self.single_tab.keep_original_checkbox.deselect()

            self.single_tab.recode_video_checkbox.deselect()
            self.single_tab.recode_audio_checkbox.deselect()
            self.single_tab._toggle_recode_panels()
            
        except Exception as e:
            print(f"ADVERTENCIA: Error al restaurar configuración en UI: {e}")

        # 4. Detección final de códecs (si no se ha hecho)
        self.ffmpeg_processor.run_detection_async(self.on_ffmpeg_detection_complete)

    def refresh_custom_models_across_tabs(self):
        """Notifica a todas las pestañas pertinentes que la lista de modelos ha cambiado."""
        # 1. Refrescar lista en Ajustes
        if hasattr(self, 'config_tab'):
            self.config_tab._refresh_custom_models_list()
            
        # 2. Refrescar menús en Proceso Único
        if hasattr(self, 'single_tab'):
            if self.single_tab.upscale_engine_menu.get() == "Upscayl":
                models = self.single_tab._scan_upscayl_models()
                if not models: models = ["- No hay modelos -"]
                self.single_tab.upscale_model_menu.configure(values=models)
                
        # 3. Refrescar menús en Herramientas de Imagen
        if hasattr(self, 'image_tab'):
            if self.image_tab.upscale_engine_menu.get() == "Upscayl":
                models = self.image_tab._scan_upscayl_models()
                if not models: models = ["- No hay modelos -"]
                self.image_tab.upscale_model_menu.configure(values=models)

    def _ensure_theme_template(self):
        """Crea o actualiza el archivo de plantilla basándose en dorado_premium.json como modelo de referencia."""
        template_path = os.path.join(self.USER_THEMES_DIR, "plantilla_tema.json")
        TEMPLATE_VERSION = "5.2"
        
        should_update = not os.path.exists(template_path)
        
        if not should_update:
            try:
                import json
                with open(template_path, 'r', encoding='utf-8-sig') as f:
                    existing_data = json.load(f)
                    version = existing_data.get("_INSTRUCCIONES_XOMACITO", {}).get("VERSION", "0.0")
                    if version != TEMPLATE_VERSION:
                        should_update = True
                        print(f"INFO: Plantilla de tema antigua ({version}) detectada. Actualizando a v{TEMPLATE_VERSION}...")
            except:
                should_update = True

        if should_update:
            try:
                import json
                from collections import OrderedDict
                base_path = getattr(sys, '_MEIPASS', self.APP_BASE_PATH)
                
                # Usar dorado.json como modelo base (tema de referencia probado y pulido)
                premium_path = os.path.join(base_path, "src", "gui", "themes", "dorado.json")
                
                if not os.path.exists(premium_path):
                    print(f"ADVERTENCIA: No se encontró dorado.json en {premium_path}. No se puede crear plantilla.")
                    return
                
                with open(premium_path, 'r', encoding='utf-8-sig') as f:
                    premium_data = json.load(f)
                
                # Construir la plantilla basada en la estructura exacta del dorado premium
                final_template = OrderedDict()
                
                # Instrucciones propias de la plantilla (reemplazan las del dorado)
                final_template["_INSTRUCCIONES_XOMACITO"] = {
                    "VERSION": TEMPLATE_VERSION,
                    "INFO_1": "GUIA DE TEMAS XOMACITO: Edita este archivo para crear tu propio estilo.",
                    "INFO_2": "FORMATO DUAL: Casi todos los valores aceptan una lista: ['Color Modo Claro', 'Color Modo Oscuro'].",
                    "INFO_3": "MODO CLARO: Si el texto o botones no se ven bien en modo claro, ajusta el PRIMER valor de la lista.",
                    "INFO_4": "FONDO GENERAL: Puedes cambiar 'CTkFrame' y 'CTk' en este JSON para cambiar el color de las ventanas y paneles.",
                    "INFO_5": "NOMBRE INTERNO: Agrega 'ThemeName': 'Mi Tema' en la raíz para que aparezca así en el menú.",
                    "AVISO_IMPORTANTE": "No uses 'transparent' en 'border_color', causará errores. Usa un color sólido.",
                    "CONSEJO": "Usa códigos Hexadecimales (ej: #AF52DE) para máxima precisión.",
                    "CUSTOM_COLORS": "Usa la sección 'CustomColors' para botones específicos (Descargar, Analizar, etc).",
                    "COMO_USAR": "1. Copia este archivo con otro nombre (ej: mi_tema.json). 2. Edita los colores. 3. En Xomacito, Ajustes > Tema > Importar."
                }
                
                # Copiar TODAS las secciones del dorado premium (CustomColors, CTk, CTkButton, etc.)
                # Esto garantiza coherencia total entre CustomColors y los widgets CTk
                for key, value in premium_data.items():
                    if key == "_INSTRUCCIONES_XOMACITO":
                        continue  # Ya pusimos las instrucciones de plantilla arriba
                    final_template[key] = value
                
                with open(template_path, 'w', encoding='utf-8') as f:
                    json.dump(final_template, f, indent=2, ensure_ascii=False)
                    
                print(f"INFO: Plantilla de tema (basada en Dorado Premium) creada en: {template_path}")
            except Exception as e:
                print(f"ERROR: No se pudo crear la plantilla de tema: {e}")

    def get_theme_color(self, key, default_color, is_ctk_widget=False):
        """
        Recupera un color del tema JSON.
        'key' es el nombre del color en 'CustomColors' o el nombre del widget (ej: 'CTkLabel').
        'default_color' es el valor de fallback.
        'is_ctk_widget' permite buscar en las secciones base de CustomTkinter.
        """
        if not self.theme_data:
            return default_color
            
        if is_ctk_widget:
            # Buscar en la sección raíz del widget (ej: CTkLabel -> text_color)
            section = self.theme_data.get(key, {})
            return section.get("text_color", default_color)
            
        if "CustomColors" not in self.theme_data:
            return default_color
        
        color_val = self.theme_data["CustomColors"].get(key, default_color)
        
        # Sanitización extra de seguridad para "transparent" en border_color
        if "border_color" in key.lower():
            if isinstance(color_val, list):
                color_val = [c if c != "transparent" else "gray65" for c in color_val]
            elif color_val == "transparent":
                color_val = "gray65"
                
        return color_val

    def _load_active_theme_data(self):
        """Recarga los datos del tema actual desde el archivo JSON."""
        try:
            import json
            # El nombre del tema suele estar en self.selected_theme_accent (cargado de settings)
            theme = getattr(self, 'selected_theme_accent', 'midnight_ocean')

            if theme in {"blue", "dark-blue", "green"}:
                from main import _builtin_theme_data
                self.theme_data = _builtin_theme_data(ctk, theme)
                self.current_theme_name = self.theme_data.get("ThemeName", theme)
                self.theme_warnings = []
                print(f"INFO: Tema integrado '{self.current_theme_name}' materializado y recargado.")
                return
            
            # Rutas de búsqueda (Usuario e Internas)
            user_themes_dir = self.USER_THEMES_DIR
            base_path = getattr(sys, '_MEIPASS', self.APP_BASE_PATH)
            internal_themes_dir = os.path.join(base_path, "src", "gui", "themes")
            
            found_path = None
            for _dir in [user_themes_dir, internal_themes_dir]:
                json_path = os.path.join(_dir, f"{theme}.json")
                if os.path.exists(json_path):
                    found_path = json_path
                    break
            
            if found_path:
                # 1. Cargar tema base (Green) como red de seguridad
                base_theme_path = os.path.join(internal_themes_dir, "shrek.json")
                final_data = {}
                if os.path.exists(base_theme_path):
                    with open(base_theme_path, 'r', encoding='utf-8-sig') as f:
                        final_data = json.load(f)

                # 2. Cargar tema del usuario
                with open(found_path, 'r', encoding='utf-8-sig') as f:
                    user_data = json.load(f)
                    
                # Detectar claves faltantes antes de mezclar para informar al usuario
                missing = [k for k in final_data if k not in user_data and not k.startswith("_") and k != "CustomColors"]
                if missing:
                    print(f"ADVERTENCIA: El tema '{theme}' está incompleto.")
                    print(f"   Claves faltantes: {', '.join(missing)}")
                    self.theme_warnings = [f"El tema '{theme}' está incompleto. Faltan {len(missing)} secciones técnicas (ej: {', '.join(missing[:3])}). Se usaron valores por defecto."]
                    self.after(500, self._show_theme_warnings)

                # 3. Mezclar (Deep Update)
                def _deep_update(base, over):
                    for k, v in over.items():
                        if isinstance(v, dict) and k in base and isinstance(base[k], dict):
                            _deep_update(base[k], v)
                        else:
                            base[k] = v
                
                _deep_update(final_data, user_data)
                self.theme_data = final_data
                print(f"INFO: Tema '{theme}' completado y recargado.")
                def _sanitize(obj):
                    if isinstance(obj, dict):
                        for k, v in obj.items():
                            if "border_color" in k:
                                if isinstance(v, list):
                                    obj[k] = [c if c != "transparent" else "gray65" for c in v]
                                elif v == "transparent":
                                    obj[k] = "gray65"
                            else:
                                _sanitize(v)
                    elif isinstance(obj, list):
                        for item in obj:
                            _sanitize(item)
                
                _sanitize(final_data)
                self.theme_data = final_data
                self.current_theme_name = final_data.get("ThemeName") or final_data.get("_INSTRUCCIONES_XOMACITO", {}).get("ThemeName") or theme.replace("_", " ").replace("-", " ").title()
                print(f"INFO: Tema '{self.current_theme_name}' ({theme}) completado y recargado.")
            else:
                self.theme_data = {}
        except Exception as e:
            print(f"ERROR recargando datos del tema: {e}")
            self.theme_data = {}

    def refresh_theme(self):
        """Propaga el cambio de tema a todas las pestañas de forma dinámica."""
        self._load_active_theme_data()
        
        # Aplicar el tema de acento a nivel de CTk (Afecta a nuevos widgets)
        # Nota: CTk no actualiza widgets existentes automáticamente, por eso llamamos a refresh_theme()
        import customtkinter as ctk
        try:
            theme = getattr(self, 'selected_theme_accent', 'midnight_ocean')
            
            # Buscar el JSON del tema
            user_json = os.path.join(self.USER_THEMES_DIR, f"{theme}.json")
            base_path = getattr(sys, '_MEIPASS', self.APP_BASE_PATH)
            internal_json = os.path.join(base_path, "src", "gui", "themes", f"{theme}.json")
            
            found_json = None
            if os.path.exists(user_json):
                found_json = user_json
            elif os.path.exists(internal_json):
                found_json = internal_json
            
            if found_json:
                # Cargar, sanitizar y aplanar CTkFont antes de pasarlo a CTk
                import json, platform
                with open(found_json, 'r', encoding='utf-8-sig') as f:
                    raw_data = json.load(f)
                
                # Aplanar CTkFont por plataforma
                if "CTkFont" in raw_data:
                    font_data = raw_data["CTkFont"]
                    os_key_map = {"Windows": "Windows", "Darwin": "macOS", "Linux": "Linux"}
                    os_key = os_key_map.get(platform.system(), "Windows")
                    if os_key in font_data and isinstance(font_data[os_key], dict):
                        raw_data["CTkFont"] = font_data[os_key]
                    elif "family" not in font_data:
                        for try_key in ["Windows", "macOS", "Linux"]:
                            if try_key in font_data and isinstance(font_data[try_key], dict):
                                raw_data["CTkFont"] = font_data[try_key]
                                break
                
                # Guardar versión sanitizada temporal
                temp_path = os.path.join(self.USER_THEMES_DIR, ".active_theme_sanitized.json")
                with open(temp_path, 'w', encoding='utf-8') as f:
                    json.dump(raw_data, f)
                ctk.set_default_color_theme(temp_path)
            else:
                ctk.set_default_color_theme(theme)
        except Exception as e:
            print(f"ADVERTENCIA: Error aplicando tema de acento en refresh: {e}")

        visual_theme_data = self.theme_data or ctk.ThemeManager.theme
        root_theme = visual_theme_data.get("CTk", {})
        frame_theme = visual_theme_data.get("CTkFrame", {})
        segmented_theme = visual_theme_data.get("CTkSegmentedButton", {})
        try:
            if root_theme.get("fg_color"):
                self.configure(fg_color=root_theme["fg_color"])
            if hasattr(self, "tab_view"):
                self.tab_view.configure(
                    fg_color=frame_theme.get("fg_color"),
                    border_color=frame_theme.get("border_color"),
                    segmented_button_fg_color=segmented_theme.get("fg_color"),
                    segmented_button_selected_color=segmented_theme.get("selected_color"),
                    segmented_button_selected_hover_color=segmented_theme.get("selected_hover_color"),
                    segmented_button_unselected_color=segmented_theme.get("unselected_color"),
                    segmented_button_unselected_hover_color=segmented_theme.get("unselected_hover_color"),
                    text_color=segmented_theme.get("text_color"),
                )
        except Exception as e:
            print(f"ADVERTENCIA: No se pudo refrescar el contenedor principal del tema: {e}")

        if hasattr(self, "gradient_backdrop"):
            self.gradient_backdrop.update_theme(visual_theme_data)
        if hasattr(self, "brand_header"):
            self.brand_header.update_theme(visual_theme_data)

        # Actualizar pestañas que ya tienen implementado refresh_theme()
        if hasattr(self, 'single_tab'):
            try:
                self.single_tab.refresh_theme()
            except Exception as e:
                print(f"ERROR actualizando SingleDownloadTab: {e}")
        
        if hasattr(self, 'batch_tab'):
            try:
                self.batch_tab.refresh_theme()
            except Exception as e:
                print(f"ERROR actualizando BatchDownloadTab: {e}")

        if hasattr(self, 'image_tab'):
            try:
                self.image_tab.refresh_theme()
            except Exception as e:
                print(f"ERROR actualizando ImageToolsTab: {e}")

        if hasattr(self, 'config_tab'):
            try:
                self.config_tab.refresh_theme()
            except Exception as e:
                print(f"ERROR actualizando ConfigTab: {e}")

    def _show_theme_warnings(self):
        """Muestra un mensaje al usuario si el tema tiene problemas."""
        if not self.theme_warnings:
            return
            
        # Imprimir en consola interna (se asegura de que aparezcan tras activarse el logger)
        for warn in self.theme_warnings:
            print(f"⚠️ ADVERTENCIA DE TEMA: {warn}")

        from tkinter import messagebox
        warn_text = "\n\n".join(self.theme_warnings)
        messagebox.showwarning(
            "Aviso de Tema Visual",
            f"Se han detectado problemas menores con el tema cargado:\n\n{warn_text}\n\n"
            "La aplicación funcionará correctamente usando valores por defecto para las partes faltantes."
        )
                
        # (Aquí se añadirán el resto de pestañas cuando se refactoricen)
        print("INFO: Tema actualizado dinámicamente en las pestañas compatibles.")

    def sanitize_title_global(self, text):
        """
        Wrapper global para limpiar títulos basado en el ajuste del usuario.
        """
        return clean_filename_text(text, clean_emojis=self.clean_titles)
