"""Django AutoApp — Auto-generate Django apps with full CRUD boilerplate."""

from __future__ import annotations

try:
    from importlib.metadata import version, PackageNotFoundError

    __version__: str = version("django-autoapp")
except PackageNotFoundError:
    __version__ = "1.0.2"

__all__: list[str] = ["__version__"]
