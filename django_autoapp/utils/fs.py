"""Filesystem operation helpers with dry-run support and rollback."""

from __future__ import annotations

import logging
import shutil
from pathlib import Path

__all__: list[str] = [
    "create_directory",
    "write_file",
    "cleanup",
]

logger: logging.Logger = logging.getLogger(__name__)


def create_directory(
    path: Path,
    *,
    dry_run: bool = False,
    skipped: set[str] | None = None,
) -> None:
    """Safely create a directory with conflict detection.

    Args:
        path: The directory path to create.
        dry_run: If ``True``, log but do not create.
        skipped: Optional set to record skipped paths.

    Raises:
        OSError: If the directory cannot be created.
    """
    if path.exists():
        if skipped is not None:
            skipped.add(str(path))
        logger.warning("Directory exists: %s", path)
        return
    if not dry_run:
        path.mkdir(parents=True, exist_ok=True)
    logger.info("Created directory: %s", path)


def write_file(
    path: Path,
    content: str,
    *,
    force: bool = False,
    dry_run: bool = False,
    skipped: set[str] | None = None,
) -> None:
    """Write content to a file with conflict handling.

    Args:
        path: The target file path.
        content: The string content to write.
        force: If ``True``, overwrite existing files.
        dry_run: If ``True``, log but do not write.
        skipped: Optional set to record skipped paths.

    Raises:
        OSError: If the file cannot be written.
    """
    if path.exists() and not force:
        if skipped is not None:
            skipped.add(str(path))
        logger.warning("File exists: %s", path)
        return
    if not dry_run:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
    logger.info("Generated: %s", path)


def cleanup(*paths: Path) -> None:
    """Remove directories created during a failed operation.

    Args:
        *paths: Directory paths to remove if they exist.
    """
    for path in paths:
        if path.exists():
            shutil.rmtree(path, ignore_errors=True)
