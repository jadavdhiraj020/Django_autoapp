"""Structured logging and output helpers for CLI and management commands."""

from __future__ import annotations

import sys
from typing import NoReturn

__all__: list[str] = ["log", "success", "warn", "error", "info"]


def log(icon: str, message: str) -> None:
    """Print a formatted status message to stdout.

    Args:
        icon: Emoji or symbol prefix.
        message: Human-readable status line.
    """
    print(f"  {icon}  {message}")


def success(message: str) -> None:
    """Print a success message."""
    log("✅", message)


def warn(message: str) -> None:
    """Print a warning message."""
    log("⚠️", message)


def info(message: str) -> None:
    """Print an informational message."""
    log("ℹ️", message)


def error(message: str) -> NoReturn:
    """Print an error message and exit with code 1.

    Args:
        message: Human-readable error description.
    """
    print(f"\n  ❌  Error: {message}", file=sys.stderr)
    raise SystemExit(1)
