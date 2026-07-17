from __future__ import annotations

import subprocess
import sys
from pathlib import Path


APP_NAME = "Xomacito"
STANDALONE_EXE_NAME = "dist\\Xomacito\\Xomacito.exe"


def project_root() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


def standalone_exe_path() -> Path:
    return project_root() / STANDALONE_EXE_NAME


def message(title: str, body: str) -> None:
    try:
        import ctypes

        ctypes.windll.user32.MessageBoxW(None, body, title, 0x40)
    except Exception:
        print(f"{title}\n{body}")


def main() -> int:
    exe = standalone_exe_path()
    self_test = "--self-test" in sys.argv
    if not exe.exists():
        if not self_test:
            message(APP_NAME, f"No encontré la aplicación independiente en:\n{exe}")
        return 1
    if self_test:
        result = subprocess.run([str(exe), "--self-test"], cwd=str(exe.parent), check=False)
        return result.returncode
    subprocess.Popen([str(exe)], cwd=str(exe.parent))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
