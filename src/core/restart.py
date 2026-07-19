"""Utilidades para reiniciar correctamente una aplicación PyInstaller one-file."""

from __future__ import annotations

import os


RESTART_WAIT_ENV = "XOMACITO_RESTART_WAIT"


def clean_restart_environment(source=None) -> dict:
    """Fuerza al nuevo proceso a extraerse en su propia carpeta temporal.

    Sin esta bandera PyInstaller puede reutilizar el directorio ``_MEI`` del
    proceso que se está cerrando y perder ``base_library.zip`` durante el inicio.
    """
    environment = dict(source if source is not None else os.environ)
    environment["PYINSTALLER_RESET_ENVIRONMENT"] = "1"
    # La nueva instancia espera brevemente a que la actual libere el cerrojo.
    environment[RESTART_WAIT_ENV] = "1"
    return environment


def restart_wait_requested(source=None) -> bool:
    environment = source if source is not None else os.environ
    return str(environment.get(RESTART_WAIT_ENV, "")).strip() == "1"
