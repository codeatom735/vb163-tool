"""Logging setup."""

from __future__ import annotations

import logging
import sys
from pathlib import Path
from typing import Any


def setup_logger(log_dir: str = "logs") -> Any:
    """Configure and return an application logger.

    loguru is used when installed. A standard-library logger is returned as a
    fallback so importing the project still works before dependencies are
    installed.
    """

    log_path = _resolve_log_dir(log_dir)
    log_path.mkdir(parents=True, exist_ok=True)

    try:
        from loguru import logger
    except ImportError:
        return _setup_stdlib_logger(log_path)

    logger.remove()
    if sys.stderr is not None:
        logger.add(
            sys.stderr,
            level="INFO",
            format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {message}",
        )
    logger.add(
        log_path / "app.log",
        level="INFO",
        rotation="10 MB",
        retention="30 days",
        encoding="utf-8",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {message}",
        enqueue=True,
    )
    return logger


def _setup_stdlib_logger(log_path: Path) -> logging.Logger:
    logger = logging.getLogger("MailAutoScreenshot")
    logger.setLevel(logging.INFO)

    if logger.handlers:
        return logger

    formatter = logging.Formatter("%(asctime)s | %(levelname)s | %(message)s")
    file_handler = logging.FileHandler(log_path / "app.log", encoding="utf-8")
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    if sys.stderr is not None:
        stream_handler = logging.StreamHandler()
        stream_handler.setFormatter(formatter)
        logger.addHandler(stream_handler)
    return logger


def _resolve_log_dir(log_dir: str) -> Path:
    path = Path(log_dir).expanduser()
    if path.is_absolute():
        return path

    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent / path

    return Path.cwd() / path
