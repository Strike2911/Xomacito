"""Exercise historical Windows updaters against a release without downloading it."""
import argparse
import json
from pathlib import Path
import re
import subprocess
import types

from packaging.version import Version

ROOT = Path(__file__).resolve().parents[1]


def git(*args):
    return subprocess.check_output(["git", *args], cwd=ROOT, text=True, encoding="utf-8")


def audit(release):
    class Response:
        def raise_for_status(self):
            pass

        def json(self):
            return release

    class Session:
        def get(self, url, **kwargs):
            assert url == "https://api.github.com/repos/Strike2911/Xomacito/releases/latest", url
            return Response()

    commits = git("rev-list", "HEAD", "--", "main.py", "src/core/app_updater.py").splitlines()
    seen = set()
    checked = []
    for commit in commits:
        tree = git("ls-tree", "-r", "--name-only", commit, "src/core/app_updater.py")
        if not tree.strip():
            continue  # Versions before the first built-in updater require manual installation.
        main = git("show", f"{commit}:main.py")
        versions = dict(re.findall(r'^(APP_VERSION|UPDATE_VERSION)\s*=\s*["\x27]([^"\x27]+)', main, re.M))
        current = versions.get("UPDATE_VERSION", versions.get("APP_VERSION"))
        if not current:
            raise RuntimeError(f"Unknown version at {commit}")
        source = git("show", f"{commit}:src/core/app_updater.py")
        key = (current, source)
        if key in seen:
            continue
        seen.add(key)
        module = types.ModuleType("legacy_updater")
        module.__file__ = str(ROOT / "src/core/app_updater.py")
        exec(compile(source, f"{commit}:app_updater.py", "exec"), module.__dict__)
        kwargs = {"session": Session()}
        if "prefer_light" in module.check_for_app_update.__code__.co_varnames:
            kwargs["prefer_light"] = False
        result = module.check_for_app_update(current, **kwargs)
        expected = Version(release["tag_name"].removeprefix("v")) > Version(current)
        if result.get("error") or result["update_available"] != expected:
            raise AssertionError(f"{commit[:8]} / {current}: {result}")
        if expected and not result["installer_name"].lower().endswith("-setup.exe"):
            raise AssertionError(f"Legacy client did not receive full setup: {result}")
        checked.append(current)
    if "3.3" not in checked:
        raise AssertionError("The audit must include the real 3.3 updater; fetch full Git history.")
    return {"implementations_and_versions_checked": len(checked),
            "versions": sorted(set(checked), key=Version), "target": release["tag_name"]}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("release_json", type=Path)
    args = parser.parse_args()
    print(json.dumps(audit(json.loads(args.release_json.read_text(encoding="utf-8-sig"))), indent=2))
