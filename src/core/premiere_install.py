"""Install and verify the UXP panel with Adobe's official installer agent."""
from __future__ import annotations

import json
import os
from pathlib import Path
import re
import subprocess
import sys
from zipfile import ZipFile

from packaging.version import Version

PLUGIN_ID = "com.strike2911.xomacito.link"
INSTALL_HELP = "https://developer.adobe.com/premiere-pro/uxp/plugins/distribution/install/"


def find_agent() -> Path | None:
    if sys.platform == "darwin":
        candidates = [Path("/Library/Application Support/Adobe/Adobe Desktop Common/RemoteComponents/UPI/UnifiedPluginInstallerAgent/UnifiedPluginInstallerAgent.app/Contents/macOS/UnifiedPluginInstallerAgent")]
    else:
        roots = {Path(value) for key in ("CommonProgramFiles", "CommonProgramFiles(x86)")
                 if (value := os.environ.get(key))}
        roots.add(Path("C:/Program Files/Common Files"))
        roots.add(Path("C:/Program Files (x86)/Common Files"))
        candidates = [root / "Adobe/Adobe Desktop Common/RemoteComponents/UPI/UnifiedPluginInstallerAgent/UnifiedPluginInstallerAgent.exe" for root in sorted(roots)]
    return next((path for path in candidates if path.is_file()), None)


def run_agent(agent: Path, action: str, argument: str, timeout: int = 45):
    prefix = "--" if sys.platform == "darwin" else "/"
    return subprocess.run([str(agent), prefix + action, argument], capture_output=True,
                          text=True, encoding="utf-8", errors="replace", timeout=timeout,
                          creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))


def parse_listing(output: str, minimum: str, wanted: str) -> dict:
    """Only an enabled panel in a compatible Premiere host counts as installed."""
    compatible = False
    host = ""
    installed = ""
    in_premiere = False
    for line in output.splitlines():
        if re.search(r"extensions? installed for", line, re.I):
            in_premiere = False
        heading = re.search(r"extensions? installed for (.*?)\s*\(ver\s+([\d.]+)\)", line, re.I)
        if heading:
            in_premiere = "premiere" in heading[1].lower()
            if in_premiere:
                host = heading[2]
                compatible = compatible or Version(host) >= Version(minimum)
            continue
        panel = re.match(r"\s*Enabled\s+Xomacito Link\s+([\d.]+)\s*$", line, re.I)
        if panel and in_premiere and Version(host) >= Version(minimum):
            if not installed or Version(panel[1]) > Version(installed):
                installed = panel[1]
    return {"hostVersion": host, "compatible": compatible, "installedVersion": installed,
            "verified": bool(installed and Version(installed) >= Version(wanted))}


def panel_status(package: Path, install: bool = False) -> dict:
    if not package.is_file():
        raise RuntimeError("Falta Xomacito-Link.ccx. Reinstala Xomacito con el instalador completo.")
    with ZipFile(package) as archive:
        manifest = json.loads(archive.read("manifest.json"))
        if manifest.get("id") != PLUGIN_ID or archive.testzip() is not None:
            raise RuntimeError("El paquete de Xomacito Link no es válido.")
    wanted = manifest["version"]
    minimum = manifest["host"]["minVersion"]
    agent = find_agent()
    base = {"wantedVersion": wanted, "minimumVersion": minimum, "verified": False,
            "canInstall": False, "message": ""}
    if agent is None:
        return {**base, "message": "No se encontró el instalador de Adobe. Abre o repara Creative Cloud Desktop y vuelve a comprobar. También puedes abrir el archivo CCX manualmente."}
    listing = run_agent(agent, "list", "all")
    if listing.returncode != 0:
        return {**base, "message": f"Adobe no pudo consultar los plugins (código {listing.returncode}). Abre Creative Cloud Desktop e inicia sesión; después vuelve a comprobar."}
    status = parse_listing(listing.stdout, minimum, wanted)
    result = {**base, **status, "canInstall": status["compatible"]}
    if not status["compatible"]:
        return {**result, "message": f"Adobe no detectó Premiere {minimum} o posterior. Abre Premiere al menos una vez y Creative Cloud Desktop, y vuelve a comprobar."}
    if status["verified"] and not install:
        return {**result, "message": f"Adobe confirma Xomacito Link {status['installedVersion']}. Reinicia Premiere y abre Ventana > Plugins UXP > Xomacito Link. Vincula la carpeta que aparece abajo y abre un proyecto."}
    if not install:
        return {**result, "message": f"Premiere {status['hostVersion']} compatible. " + (f"El panel instalado es {status['installedVersion']}; hay una actualización." if status['installedVersion'] else "Xomacito Link aún no está instalado o está desactivado.")}
    try:
        installed = run_agent(agent, "install", str(package.resolve()), timeout=180)
    except subprocess.TimeoutExpired:
        return {**result, "message": "Adobe no terminó dentro del tiempo de espera. Revisa sus ventanas de confirmación y pulsa Comprobar estado antes de reintentar."}
    if installed.returncode != 0:
        detail = (installed.stdout + "\n" + installed.stderr).strip()[-1200:]
        return {**result, "message": f"Adobe no pudo instalar Xomacito Link (código {installed.returncode}). Revisa Creative Cloud Desktop y sus permisos.\n{detail}"}
    listing = run_agent(agent, "list", "all")
    verified = parse_listing(listing.stdout, minimum, wanted) if listing.returncode == 0 else {}
    result.update(verified or {"verified": False})
    result["message"] = (f"Adobe confirmó la instalación de Xomacito Link {wanted}. Reinicia Premiere y abre Ventana > Plugins UXP > Xomacito Link."
                         if verified.get("verified") else "Adobe terminó, pero todavía no confirma el panel instalado. Revisa Creative Cloud > Plugins y pulsa Comprobar estado.")
    return result
