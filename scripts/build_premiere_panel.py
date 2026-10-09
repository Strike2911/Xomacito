"""Build the same Xomacito Link CCX on Windows and macOS."""
import json
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile


def build():
    panel = Path(__file__).resolve().parents[1] / "premiere-panel"
    manifest = json.loads((panel / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["manifestVersion"] == 5 and manifest["host"]["app"] == "premierepro"
    assert manifest["requiredPermissions"] == {"localFileSystem": "request"}
    target = panel / "Xomacito-Link.ccx"
    temporary = target.with_suffix(".tmp")
    with ZipFile(temporary, "w", compression=ZIP_DEFLATED) as archive:
        for name in ("manifest.json", "index.html", "index.js", "styles.css"):
            archive.write(panel / name, name)
    temporary.replace(target)
    with ZipFile(target) as archive:
        assert archive.testzip() is None
    print(f"Xomacito Link {manifest['version']}: {target}")


if __name__ == "__main__":
    build()
