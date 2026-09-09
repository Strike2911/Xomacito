"""Compare release tags without treating an installed component as up to date."""
from packaging.version import Version, InvalidVersion


def dependency_status(local, latest, installed=True):
    result = {"latestVersion": latest, "updateAvailable": False}
    if not installed:
        return {**result, "detail": "No instalado", "action": "Instalar"}
    try:
        local_version = Version(str(local).strip().lstrip("vV"))
        latest_version = Version(str(latest).strip().lstrip("vV"))
    except InvalidVersion:
        return {**result, "detail": "Versión local desconocida", "action": "Reinstalar"}
    if latest_version > local_version:
        return {**result, "updateAvailable": True, "detail": "Actualización disponible", "action": "Actualizar"}
    return {**result, "detail": "Actualizado" if latest_version == local_version else "Versión local más reciente", "action": "Reinstalar"}
