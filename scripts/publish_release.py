"""Publish stable Windows releases only when legacy clients can update too."""
from __future__ import annotations

import argparse
import json
import re
import subprocess
from urllib.parse import urlparse

from packaging.version import Version

REPO = "Strike2911/Xomacito"


def validate_release(release: dict, repository: str = REPO) -> dict:
    tag = str(release.get("tag_name", ""))
    version = Version(tag.removeprefix("v"))
    if version <= Version("3.3"):
        raise ValueError("El tag interno debe superar 3.3; no uses la versión comercial como tag.")
    if release.get("prerelease"):
        raise ValueError("Solo se pueden publicar actualizaciones estables como latest.")
    full = [a for a in release.get("assets", [])
            if re.fullmatch(r"xomacito-[0-9.]+-setup\.exe", str(a.get("name", "")).lower())]
    if len(full) != 1:
        raise ValueError("Falta un único instalador completo Xomacito-<versión>-Setup.exe. "
                         "Update-Light no es reconocido por los actualizadores antiguos.")
    asset = full[0]
    if asset.get("state") != "uploaded":
        raise ValueError("El instalador completo todavía no terminó de subir.")
    if not 0 < int(asset.get("size", 0)) <= 2 * 1024**3:
        raise ValueError("Tamaño del instalador completo inválido.")
    if not re.fullmatch(r"sha256:[0-9a-fA-F]{64}", str(asset.get("digest", ""))):
        raise ValueError("GitHub todavía no ofrece un SHA-256 verificable para el instalador completo.")
    url = urlparse(str(asset.get("browser_download_url", "")))
    if (url.scheme != "https" or url.netloc.lower() != "github.com"
            or url.path != f"/{repository}/releases/download/{tag}/{asset['name']}"):
        raise ValueError("El instalador no pertenece a esta publicación oficial.")
    return asset


def gh(*args: str):
    return subprocess.check_output(["gh", *args], text=True, encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tag", required=True)
    parser.add_argument("--repo", default=REPO)
    parser.add_argument("--check-only", action="store_true")
    args = parser.parse_args()
    pages = json.loads(gh("api", f"repos/{args.repo}/releases?per_page=100", "--paginate", "--slurp"))
    release = next((r for page in pages for r in page if r["tag_name"] == args.tag), None)
    if release is None:
        raise ValueError(f"No existe la publicación {args.tag}.")
    asset = validate_release(release, args.repo)
    latest = json.loads(gh("api", f"repos/{args.repo}/releases/latest"))
    if Version(args.tag.removeprefix("v")) < Version(latest["tag_name"].removeprefix("v")):
        raise ValueError("No se puede reemplazar latest por una versión anterior.")
    print(f"Compatible con actualizadores antiguos: {asset['name']}")
    if not args.check_only:
        gh("release", "edit", args.tag, "--repo", args.repo, "--draft=false", "--latest")
        print(release["html_url"])


if __name__ == "__main__":
    main()
