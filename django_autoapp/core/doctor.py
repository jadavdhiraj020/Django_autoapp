"""Project diagnostics engine — the ``autoapp doctor`` command.

Scans the current Django project for common issues and provides
step-by-step fix instructions.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from typing import Any

__all__: list[str] = ["run_doctor"]


class _Check:
    """A single diagnostic check result."""

    def __init__(self, name: str, passed: bool, message: str, fix: str = "") -> None:
        self.name = name
        self.passed = passed
        self.message = message
        self.fix = fix


def _check_manage_py() -> _Check:
    """Check that manage.py exists in the current directory."""
    manage = Path.cwd() / "manage.py"
    if manage.exists():
        return _Check("manage.py", True, "manage.py found")
    return _Check(
        "manage.py",
        False,
        "manage.py not found in current directory",
        "Make sure you are inside your Django project root directory:\n"
        "  cd <your_project_name>",
    )


def _check_venv() -> _Check:
    """Check if running inside a virtual environment."""
    in_venv = sys.prefix != sys.base_prefix
    if in_venv:
        return _Check("Virtual Environment", True, f"Active venv: {sys.prefix}")
    return _Check(
        "Virtual Environment",
        False,
        "Not running inside a virtual environment",
        "Activate your virtual environment:\n"
        "  Windows:  ..\\venv\\Scripts\\activate\n"
        "  macOS/Linux: source ../venv/bin/activate",
    )


def _check_django_installed() -> _Check:
    """Check if Django is installed."""
    try:
        import django  # noqa: F401
        return _Check("Django", True, f"Django {django.VERSION} installed")
    except ImportError:
        return _Check(
            "Django",
            False,
            "Django is not installed",
            "Install Django:\n  pip install Django>=4.2",
        )


def _check_autoapp_in_installed_apps() -> _Check:
    """Check if django_autoapp is in INSTALLED_APPS."""
    manage = Path.cwd() / "manage.py"
    if not manage.exists():
        return _Check("INSTALLED_APPS", False, "Cannot check — manage.py not found", "")

    # Find settings.py by scanning manage.py for the settings module
    content = manage.read_text(encoding="utf-8")
    settings_module = ""
    for line in content.splitlines():
        if "DJANGO_SETTINGS_MODULE" in line and "'" in line:
            start = line.index("'") + 1
            end = line.index("'", start)
            settings_module = line[start:end]
            break
        elif "DJANGO_SETTINGS_MODULE" in line and '"' in line:
            start = line.index('"') + 1
            end = line.index('"', start)
            settings_module = line[start:end]
            break

    if not settings_module:
        return _Check("INSTALLED_APPS", False, "Could not detect settings module", "")

    # Convert module path to file path
    parts = settings_module.split(".")
    settings_path = Path.cwd() / Path(*parts).with_suffix(".py")

    if not settings_path.exists():
        return _Check(
            "INSTALLED_APPS",
            False,
            f"settings.py not found at {settings_path}",
            "",
        )

    settings_content = settings_path.read_text(encoding="utf-8")
    if "django_autoapp" in settings_content:
        return _Check("INSTALLED_APPS", True, "django_autoapp is registered")
    return _Check(
        "INSTALLED_APPS",
        False,
        "django_autoapp is NOT in INSTALLED_APPS",
        "Add 'django_autoapp' to INSTALLED_APPS in your settings.py:\n"
        "  INSTALLED_APPS = [\n"
        "      ...\n"
        '      "django_autoapp",\n'
        "  ]",
    )


def _check_migrations() -> _Check:
    """Check for unapplied migrations."""
    try:
        result = subprocess.run(
            [sys.executable, "manage.py", "showmigrations", "--plan"],
            cwd=str(Path.cwd()),
            capture_output=True,
            text=True,
            timeout=15,
        )
        if result.returncode != 0:
            return _Check(
                "Migrations",
                False,
                "Could not check migrations",
                f"Error: {result.stderr.strip()[:200]}",
            )
        unapplied = [
            line.strip()
            for line in result.stdout.splitlines()
            if line.strip().startswith("[ ]")
        ]
        if unapplied:
            return _Check(
                "Migrations",
                False,
                f"{len(unapplied)} unapplied migration(s) found",
                "Apply pending migrations:\n"
                "  python manage.py migrate",
            )
        return _Check("Migrations", True, "All migrations applied")
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return _Check("Migrations", False, "Could not run migration check", "")


def _check_database() -> _Check:
    """Check database connectivity."""
    try:
        result = subprocess.run(
            [sys.executable, "manage.py", "check", "--database", "default"],
            cwd=str(Path.cwd()),
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode == 0:
            return _Check("Database", True, "Database connection OK")
        return _Check(
            "Database",
            False,
            "Database check failed",
            f"Error: {result.stderr.strip()[:200]}\n\n"
            "Common fixes:\n"
            "  - Check your DATABASES config in settings.py\n"
            "  - Ensure the database server is running\n"
            "  - Run: python manage.py migrate",
        )
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return _Check("Database", False, "Could not run database check", "")


def run_doctor(stdout: Any = None) -> None:
    """Run all diagnostic checks and print results.

    Args:
        stdout: Optional writable stream (defaults to ``print``).
    """
    write = stdout.write if stdout else print

    write("\n  🩺  Django AutoApp Doctor\n")
    write("  " + "=" * 40 + "\n\n")

    checks: list[_Check] = [
        _check_manage_py(),
        _check_venv(),
        _check_django_installed(),
        _check_autoapp_in_installed_apps(),
        _check_migrations(),
        _check_database(),
    ]

    passed = 0
    failed = 0

    for check in checks:
        if check.passed:
            write(f"  ✅  {check.name}: {check.message}\n")
            passed += 1
        else:
            write(f"  ❌  {check.name}: {check.message}\n")
            if check.fix:
                write(f"\n      Fix:\n")
                for line in check.fix.splitlines():
                    write(f"      {line}\n")
                write("\n")
            failed += 1

    write(f"\n  Results: {passed} passed, {failed} failed\n\n")

    if failed == 0:
        write("  🎉  Everything looks good! Your project is healthy.\n\n")
    else:
        write(f"  ⚠️  {failed} issue(s) found. Follow the fix instructions above.\n\n")
