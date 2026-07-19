"""Actualizaciones de Xomacito mediante el repositorio oficial de GitHub."""

from __future__ import annotations

import hashlib
import re
import tempfile
from pathlib import Path
from typing import Callable
from urllib.parse import urlparse

import requests
from packaging.version import InvalidVersion, Version


REPOSITORY = "Strike2911/Xomacito"
LATEST_RELEASE_API = f"https://api.github.com/repos/{REPOSITORY}/releases/latest"
RELEASES_URL = f"https://github.com/{REPOSITORY}/releases"
REQUEST_HEADERS = {
    "Accept": "application/vnd.github+json",
    "User-Agent": "Xomacito-Updater",
    "X-GitHub-Api-Version": "2022-11-28",
}
MAX_INSTALLER_SIZE = 2 * 1024 * 1024 * 1024


class AppUpdateError(RuntimeError):
    """Error recuperable durante la comprobación o descarga de una versión."""


def _parsed_version(value: str) -> Version:
    normalized = str(value or "").strip()
    if normalized.lower().startswith("v"):
        normalized = normalized[1:]
    try:
        return Version(normalized)
    except InvalidVersion as error:
        raise AppUpdateError(f"Versión no válida: {value!r}") from error


def _select_installer_asset(assets: list[dict]) -> dict | None:
    uploaded = [asset for asset in assets if asset.get("state", "uploaded") == "uploaded"]
    for asset in uploaded:
        if str(asset.get("name", "")).casefold() == "setup.exe":
            return asset
    for asset in uploaded:
        name = str(asset.get("name", "")).casefold()
        if name.endswith(".exe") and "setup" in name and "xomacito" in name:
            return asset
    return None


def _official_installer_url(url: str) -> bool:
    parsed = urlparse(str(url or ""))
    expected_prefix = f"/{REPOSITORY}/releases/download/".casefold()
    return (
        parsed.scheme.casefold() == "https"
        and parsed.hostname is not None
        and parsed.hostname.casefold() == "github.com"
        and parsed.path.casefold().startswith(expected_prefix)
        and parsed.path.casefold().endswith(".exe")
    )


def check_for_app_update(current_version: str, session=None, timeout: float = 12.0) -> dict:
    """Devuelve información de la última versión estable sin provocar downgrades."""
    try:
        current = _parsed_version(current_version)
        client = session or requests
        response = client.get(LATEST_RELEASE_API, headers=REQUEST_HEADERS, timeout=timeout)
        response.raise_for_status()
        release = response.json()

        latest_text = str(release.get("tag_name", "")).strip()
        latest = _parsed_version(latest_text)
        update_available = latest > current
        result = {
            "update_available": update_available,
            "current_version": str(current),
            "latest_version": str(latest),
            "release_url": release.get("html_url") or RELEASES_URL,
            "release_notes": str(release.get("body") or "").strip(),
        }

        if not update_available:
            return result

        asset = _select_installer_asset(list(release.get("assets") or []))
        if not asset:
            return {
                **result,
                "error": "La versión nueva no contiene el instalador oficial de Xomacito.",
            }

        installer_url = str(asset.get("browser_download_url") or "")
        if not _official_installer_url(installer_url):
            return {
                **result,
                "error": "GitHub devolvió una dirección de instalador no reconocida.",
            }

        installer_size = int(asset.get("size") or 0)
        if installer_size <= 0 or installer_size > MAX_INSTALLER_SIZE:
            return {
                **result,
                "error": "El tamaño publicado del instalador no es válido.",
            }

        installer_sha256 = _expected_sha256(str(asset.get("digest") or ""))
        if not installer_sha256:
            return {
                **result,
                "error": "La versión nueva no incluye una huella SHA-256 verificable.",
            }

        return {
            **result,
            "installer_url": installer_url,
            "installer_name": str(asset.get("name") or "setup.exe"),
            "installer_size": installer_size,
            "installer_digest": f"sha256:{installer_sha256}",
        }
    except Exception as error:
        if isinstance(error, AppUpdateError):
            message = str(error)
        else:
            message = f"No se pudo consultar la versión más reciente: {error}"
        return {
            "update_available": False,
            "current_version": str(current_version),
            "error": message,
        }


def _expected_sha256(digest: str) -> str | None:
    match = re.fullmatch(r"sha256:([0-9a-fA-F]{64})", str(digest or "").strip())
    return match.group(1).lower() if match else None


def download_installer(
    update_info: dict,
    destination: str | Path | None = None,
    progress_callback: Callable[[int, int], None] | None = None,
    session=None,
) -> Path:
    """Descarga el setup completo y valida tamaño, formato PE y SHA-256."""
    installer_url = str(update_info.get("installer_url") or "")
    if not _official_installer_url(installer_url):
        raise AppUpdateError("La dirección del instalador no pertenece al repositorio oficial.")

    expected_size = int(update_info.get("installer_size") or 0)
    if expected_size <= 0 or expected_size > MAX_INSTALLER_SIZE:
        raise AppUpdateError("El tamaño esperado del instalador no es válido.")

    version_text = re.sub(r"[^0-9A-Za-z._-]+", "-", str(update_info.get("latest_version") or "new"))
    if destination is None:
        update_dir = Path(tempfile.gettempdir()) / "Xomacito" / "updates"
        destination_path = update_dir / f"Xomacito-Setup-{version_text}.exe"
    else:
        destination_path = Path(destination)
    destination_path.parent.mkdir(parents=True, exist_ok=True)
    partial_path = destination_path.with_suffix(destination_path.suffix + ".part")
    partial_path.unlink(missing_ok=True)

    client = session or requests
    response = None
    downloaded = 0
    hasher = hashlib.sha256()
    try:
        response = client.get(
            installer_url,
            headers={"User-Agent": REQUEST_HEADERS["User-Agent"]},
            stream=True,
            timeout=(12, 90),
        )
        response.raise_for_status()
        with partial_path.open("wb") as output:
            for chunk in response.iter_content(chunk_size=1024 * 1024):
                if not chunk:
                    continue
                downloaded += len(chunk)
                if downloaded > expected_size or downloaded > MAX_INSTALLER_SIZE:
                    raise AppUpdateError("La descarga superó el tamaño publicado por GitHub.")
                output.write(chunk)
                hasher.update(chunk)
                if progress_callback:
                    progress_callback(downloaded, expected_size)

        if downloaded != expected_size:
            raise AppUpdateError(
                f"La descarga quedó incompleta ({downloaded} de {expected_size} bytes)."
            )
        with partial_path.open("rb") as downloaded_file:
            if downloaded_file.read(2) != b"MZ":
                raise AppUpdateError("El archivo descargado no es un instalador válido de Windows.")

        expected_digest = _expected_sha256(update_info.get("installer_digest", ""))
        if not expected_digest:
            raise AppUpdateError("No hay una huella SHA-256 válida para verificar el instalador.")
        if hasher.hexdigest().lower() != expected_digest:
            raise AppUpdateError("La verificación SHA-256 del instalador no coincide.")

        partial_path.replace(destination_path)
        return destination_path
    except Exception:
        partial_path.unlink(missing_ok=True)
        raise
    finally:
        if response is not None and hasattr(response, "close"):
            response.close()


def silent_installer_command(installer_path: str | Path) -> list[str]:
    """Parámetros Inno Setup usados después de que el usuario acepta actualizar."""
    return [
        str(Path(installer_path)),
        "/SILENT",
        "/SP-",
        "/CLOSEAPPLICATIONS",
        "/NORESTART",
        "/XOMACITOUPDATE=1",
    ]
