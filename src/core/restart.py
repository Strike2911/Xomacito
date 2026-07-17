"""Utilidades para reiniciar correctamente una aplicación PyInstaller one-file."""

from __future__ import annotations

import os


def clean_restart_environment(source=None) -> dict:
    """Fuerza al nuevo proceso a extraerse en su propia carpeta temporal.

    Sin esta bandera PyInstaller puede reutilizar el directorio ``_MEI`` del
    proceso que se está cerrando y perder ``base_library.zip`` durante el inicio.
    """
    environment = dict(source if source is not None else os.environ)
    environment["PYINSTALLER_RESET_ENVIRONMENT"] = "1"
    return environment
