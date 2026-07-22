"""Interfaz Qt Quick de Xomacito.

La capa visual vive en QML y la lógica de aplicación permanece en Python.  El
paquete no importa Qt al cargarse para que las pruebas del motor y el modo
``--self-test`` sigan siendo rápidos.
"""

__all__ = ["run_qt_app"]


def run_qt_app(**kwargs):
    from .application import run_qt_app as _run_qt_app

    return _run_qt_app(**kwargs)
