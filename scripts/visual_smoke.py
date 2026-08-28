"""Abre la interfaz desde la fuente para una revisión visual manual, sin el bloqueo de instancia."""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.ui import run_qt_app


if __name__ == "__main__":
    raise SystemExit(run_qt_app(
        project_root=ROOT,
        app_version="1.0",
        update_version="4.0.13",
    ))
