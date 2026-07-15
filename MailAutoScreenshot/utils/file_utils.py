"""File utility helpers."""

from __future__ import annotations

import re
from pathlib import Path


WINDOWS_INVALID_FILENAME_PATTERN = re.compile(r'[<>:"/\\|?*\x00-\x1f]')


def ensure_directory(path: str) -> Path:
    """Create a directory if needed and return it as a Path."""

    directory = Path(path).expanduser()
    directory.mkdir(parents=True, exist_ok=True)
    return directory


def safe_filename(raw_name: str, extension: str = ".PNG", max_stem_length: int = 180) -> str:
    """Build a Windows-safe screenshot filename from the original Excel value.

    The original mail name is preserved as much as Windows allows. Only illegal
    filename characters and control characters are replaced.
    """

    stem = str(raw_name).strip()
    stem = WINDOWS_INVALID_FILENAME_PATTERN.sub("_", stem)
    stem = re.sub(r"\s+", " ", stem).strip()
    stem = stem.rstrip(". ")

    if not stem:
        stem = "mail_screenshot"

    if len(stem) > max_stem_length:
        stem = stem[:max_stem_length].rstrip(". ")

    suffix = extension if extension.startswith(".") else f".{extension}"
    return f"{stem}{suffix.upper()}"


def unique_path(directory: str | Path, filename: str) -> Path:
    """Return a non-existing path, preserving the requested name when possible."""

    base_dir = ensure_directory(str(directory))
    candidate = base_dir / filename
    if not candidate.exists():
        return candidate

    stem = candidate.stem
    suffix = candidate.suffix
    counter = 2

    while True:
        next_candidate = base_dir / f"{stem}_{counter}{suffix}"
        if not next_candidate.exists():
            return next_candidate
        counter += 1
