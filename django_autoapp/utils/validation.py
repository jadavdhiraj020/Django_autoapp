"""Input validation utilities for project names, app names, and model names."""

from __future__ import annotations

import re

__all__: list[str] = [
    "validate_project_name",
    "validate_app_name",
    "validate_model_name",
    "validate_database_choice",
    "APP_NAME_REGEX",
    "MODEL_NAME_REGEX",
    "PROJECT_NAME_REGEX",
    "SUPPORTED_DATABASES",
]

PROJECT_NAME_REGEX: re.Pattern[str] = re.compile(r"^[a-zA-Z][a-zA-Z0-9_]*$")
APP_NAME_REGEX: re.Pattern[str] = re.compile(r"^[a-z][a-z0-9_]*$")
MODEL_NAME_REGEX: re.Pattern[str] = re.compile(r"^[A-Z][a-zA-Z0-9]*$")

SUPPORTED_DATABASES: tuple[str, ...] = ("sqlite", "postgres", "mysql")


def validate_project_name(name: str) -> str | None:
    """Validate a Django project name.

    Args:
        name: The project name to validate.

    Returns:
        An error message string if invalid, or ``None`` if valid.
    """
    if not name:
        return "Project name cannot be empty."
    if not PROJECT_NAME_REGEX.match(name):
        return (
            f"Invalid project name '{name}'. "
            "Must start with a letter and contain only letters, digits, and underscores."
        )
    return None


def validate_app_name(name: str) -> str | None:
    """Validate a Django app name.

    Args:
        name: The app name to validate.

    Returns:
        An error message string if invalid, or ``None`` if valid.
    """
    if not name:
        return "App name cannot be empty."
    if not APP_NAME_REGEX.match(name):
        return (
            f"Invalid app name '{name}'. "
            "Must be lowercase with letters, numbers, and underscores."
        )
    return None


def validate_model_name(name: str) -> str | None:
    """Validate a Django model name.

    Args:
        name: The model name to validate.

    Returns:
        An error message string if invalid, or ``None`` if valid.
    """
    if not name:
        return "Model name cannot be empty."
    if not MODEL_NAME_REGEX.match(name):
        return (
            f"Invalid model name '{name}'. "
            "Must start with uppercase letter and be alphanumeric."
        )
    return None


def validate_database_choice(db: str) -> str | None:
    """Validate a database backend choice.

    Args:
        db: The database type string.

    Returns:
        An error message string if invalid, or ``None`` if valid.
    """
    if db not in SUPPORTED_DATABASES:
        return f"Unsupported database '{db}'. Choose from: {', '.join(SUPPORTED_DATABASES)}"
    return None
