from __future__ import annotations

from pathlib import Path


def next_available_media_stem(folder: str | Path, stem: str) -> str:
    """Return a title that does not collide with any existing file extension.

    Download engines choose the final extension after format selection, so checking
    only ``title.mp4`` is not enough.  This helper treats every ``title.*`` file as
    occupied and follows the familiar Windows copy convention: ``title (1)``.
    """

    directory = Path(folder)
    base = str(stem).strip() or "archivo"
    try:
        existing = {path.name.casefold() for path in directory.iterdir()}
    except (FileNotFoundError, NotADirectoryError, PermissionError, OSError):
        existing = set()

    def is_occupied(candidate: str) -> bool:
        folded = candidate.casefold()
        return any(
            name == folded or name.startswith(f"{folded}.")
            for name in existing
        )

    if not is_occupied(base):
        return base

    counter = 1
    while is_occupied(f"{base} ({counter})"):
        counter += 1
    return f"{base} ({counter})"


def next_available_path(path: str | Path) -> Path:
    """Return an available sibling path using ``name (n).ext`` numbering."""

    desired = Path(path)
    if not desired.exists():
        return desired
    counter = 1
    while True:
        candidate = desired.with_name(f"{desired.stem} ({counter}){desired.suffix}")
        if not candidate.exists():
            return candidate
        counter += 1
