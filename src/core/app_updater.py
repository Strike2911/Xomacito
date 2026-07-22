"""Actualizaciones de Xomacito mediante el repositorio oficial de GitHub."""

from __future__ import annotations

import hashlib
import re
import tempfile
import uuid
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
UPDATE_PROMPT_NOTES_LIMIT = 1200
RELEASE_NOTICES = {
    "2.3": {
        "eyebrow": "ACTUALIZACIÓN INSTALADA",
        "title": "Xomacito 2.3",
        "subtitle": "¡LA PREMIERE READY UPDATE!!",
        "message": (
            "La recodificación vuelve a funcionar de forma confiable y Xomacito "
            "prepara resultados MP4 más compatibles con Premiere. Encontrar el archivo "
            "terminado ahora también es inmediato."
        ),
        "highlights": [
            "Recodificación reparada para entradas MKV y salidas MP4.",
            "Audio AAC/M4A prioritario para evitar MKV cuando los streams lo permiten.",
            "Temporales y contenedores FFmpeg validados en todos los flujos.",
            "El botón Resultado abre la ubicación y selecciona el archivo.",
            "El Explorador se abre automáticamente al terminar una descarga.",
        ],
        "contributors": ["Jorge", "Xomas", "Megas", "Playera", "Mensva"],
        "closing": "Gracias por seguir aportando ideas y pruebas al proyecto.",
    },
    "2.2": {
        "eyebrow": "ACTUALIZACIÓN INSTALADA",
        "title": "Xomacito 2.2",
        "subtitle": "¡LA MIAU UPDATE!!",
        "message": (
            "Ahora cada descarga y cada revelación del gacha tienen una respuesta "
            "sonora clara, mientras el instalador explica su progreso desde el primer segundo."
        ),
        "highlights": [
            "Nuevo maullido al completar una descarga.",
            "Cinco efectos de revelación, uno para cada rareza del gacha.",
            "Sonidos asíncronos que no bloquean ni ralentizan la interfaz.",
            "Actualizador más claro y con menos espera al preparar la instalación.",
        ],
        "contributors": ["Jorge", "Xomas", "Megas", "Playera"],
        "closing": "Gracias por seguir aportando ideas al proyecto.",
    },
    "2.1": {
        "eyebrow": "ACTUALIZACIÓN INSTALADA",
        "title": "Xomacito 2.1",
        "subtitle": "LA DowP KILLER UPDATE!!",
        "message": (
            "Xomacito dio el salto a una interfaz más rápida, limpia y fluida, "
            "manteniendo todas sus herramientas en un espacio más cómodo."
        ),
        "highlights": [
            "Nueva interfaz Qt Quick, más suave y responsiva.",
            "Pantalla principal compacta, incluso en 1280 × 720.",
            "Temas instantáneos y pegado automático de enlaces.",
            "Descargas, recodificación e imagen con el flujo completo.",
            "¡Nuevo sistema de GACHA! Desbloquea gatos y personaliza tu avatar.",
        ],
        "contributors": ["Jorge", "Xomas", "Megas", "Playera"],
        "closing": "Gracias por ser los principales contribuyentes de ideas del proyecto.",
    },
    "1.6.4": {
        "title": "Xomacito 1.6.4 — ¡Actualización instalada!",
        "message": (
            "Playera encontró un fallo en donde la recodificación no "
            "funcionaba correctamente :v\n\n"
            "Importante para videos MOV con transparencia:\n"
            "• ProRes 422 Proxy no admite canal alfa y elimina la transparencia.\n"
            "• Xomacito ahora selecciona ProRes 4444 Liviano (Transparencia), "
            "que conserva el alfa y reduce el peso.\n"
            "• La aplicación bloquea perfiles incompatibles para que el alfa no "
            "se pierda por accidente.\n\n"
            "ᗧ • • •  VIVA LA GRASA!!! :V"
        ),
    }
}


class AppUpdateError(RuntimeError):
    """Error recuperable durante la comprobación o descarga de una versión."""


def build_update_prompt(update_info: dict, current_version: str) -> str:
    """Construye la alerta de actualización incluyendo las notas publicadas."""
    latest_version = str(update_info.get("latest_version") or "nueva")
    release_notes = str(update_info.get("release_notes") or "").strip()
    if len(release_notes) > UPDATE_PROMPT_NOTES_LIMIT:
        release_notes = release_notes[:UPDATE_PROMPT_NOTES_LIMIT].rstrip() + "…"

    notes_section = f"\n\nNovedades:\n{release_notes}" if release_notes else ""
    return (
        f"Hay una nueva versión disponible: {latest_version}\n"
        f"Tu versión actual: {current_version}"
        f"{notes_section}\n\n"
        "¿Quieres descargarla e instalarla ahora?\n\n"
        "Si eliges Sí, Xomacito verificará el instalador, se cerrará "
        "durante la actualización y volverá a abrirse al terminar."
    )


def _parsed_version(value: str) -> Version:
    normalized = str(value or "").strip()
    if normalized.lower().startswith("v"):
        normalized = normalized[1:]
    try:
        return Version(normalized)
    except InvalidVersion as error:
        raise AppUpdateError(f"Versión no válida: {value!r}") from error


def release_notice_for_version(current_version: str) -> dict | None:
    """Devuelve el aviso que debe mostrarse una vez al instalar una versión."""
    try:
        normalized = str(_parsed_version(current_version))
    except AppUpdateError:
        return None
    return RELEASE_NOTICES.get(normalized)


def _select_installer_asset(assets: list[dict]) -> dict | None:
    uploaded = [asset for asset in assets if asset.get("state", "uploaded") == "uploaded"]
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
            "installer_name": str(asset.get("name") or "Xomacito-Setup.exe"),
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
        # Cada intento recibe su propio nombre. Un setup anterior puede seguir
        # abierto unos segundos y Windows no permite reemplazarlo en ese estado.
        attempt_id = uuid.uuid4().hex[:12]
        destination_path = update_dir / f"Xomacito-{version_text}-Setup-{attempt_id}.exe"
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


_DEFERRED_INSTALLER_SCRIPT = r"""param(
    [Parameter(Mandatory=$true)][int]$XomacitoProcessId,
    [Parameter(Mandatory=$true)][string]$InstallerPath
)

$ErrorActionPreference = 'Stop'

# Wait for the application to finish normally. If shutdown gets stuck, force
# only the exact process that requested this already-authorized update.
for ($attempt = 0; $attempt -lt 300; $attempt++) {
    if ($null -eq (Get-Process -Id $XomacitoProcessId -ErrorAction SilentlyContinue)) {
        break
    }
    Start-Sleep -Milliseconds 100
}

if ($null -ne (Get-Process -Id $XomacitoProcessId -ErrorAction SilentlyContinue)) {
    Stop-Process -Id $XomacitoProcessId -Force -ErrorAction SilentlyContinue
    Wait-Process -Id $XomacitoProcessId -ErrorAction SilentlyContinue
}

if (-not (Test-Path -LiteralPath $InstallerPath -PathType Leaf)) {
    exit 2
}

$installerArguments = @(
    '/SILENT',
    '/SP-',
    '/CLOSEAPPLICATIONS',
    '/NORESTART',
    '/XOMACITOUPDATE=1'
)
$setup = Start-Process -FilePath $InstallerPath -ArgumentList $installerArguments `
    -WindowStyle Hidden -Wait -PassThru
$setupExitCode = $setup.ExitCode

if ($setupExitCode -eq 0) {
    Remove-Item -LiteralPath $InstallerPath -Force -ErrorAction SilentlyContinue
}
Remove-Item -LiteralPath $PSCommandPath -Force -ErrorAction SilentlyContinue
exit $setupExitCode
"""


def deferred_installer_command(
    installer_path: str | Path,
    xomacito_process_id: int,
    launcher_path: str | Path | None = None,
) -> list[str]:
    """Crea un lanzador que espera el cierre real de Xomacito antes de instalar."""
    installer = Path(installer_path).resolve()
    if launcher_path is None:
        launcher = installer.parent / f"xomacito-update-{uuid.uuid4().hex[:12]}.ps1"
    else:
        launcher = Path(launcher_path).resolve()
    launcher.parent.mkdir(parents=True, exist_ok=True)
    launcher.write_text(_DEFERRED_INSTALLER_SCRIPT, encoding="utf-8-sig")

    return [
        "powershell.exe",
        "-NoLogo",
        "-NoProfile",
        "-NonInteractive",
        "-ExecutionPolicy",
        "Bypass",
        "-WindowStyle",
        "Hidden",
        "-File",
        str(launcher),
        "-XomacitoProcessId",
        str(int(xomacito_process_id)),
        "-InstallerPath",
        str(installer),
    ]
