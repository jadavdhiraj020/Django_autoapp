"""Context-aware guide system — the ``autoapp guide`` command.

Detects the current project state and recommends the next step
with exact commands to run.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

__all__: list[str] = ["run_guide"]


def _detect_state() -> dict[str, Any]:
    """Scan the current directory and detect project state.

    Returns:
        Dictionary of detected state flags.
    """
    cwd = Path.cwd()
    state: dict[str, Any] = {
        "has_manage_py": (cwd / "manage.py").exists(),
        "has_venv": any(
            (cwd.parent / d).exists() for d in ("venv", ".venv", "env")
        ),
        "in_venv": sys.prefix != sys.base_prefix,
        "has_db": (cwd / "db.sqlite3").exists(),
        "apps": [],
        "settings_module": "",
        "has_docker": (cwd / "Dockerfile").exists(),
        "has_env": (cwd / ".env").exists(),
        "has_git": (cwd / ".git").exists(),
    }

    # Detect apps (dirs with models.py)
    for child in cwd.iterdir():
        if child.is_dir() and (child / "models.py").exists():
            if child.name not in ("__pycache__",):
                state["apps"].append(child.name)

    # Detect settings module from manage.py
    manage = cwd / "manage.py"
    if manage.exists():
        content = manage.read_text(encoding="utf-8")
        for line in content.splitlines():
            if "DJANGO_SETTINGS_MODULE" in line:
                for quote in ("'", '"'):
                    if quote in line:
                        try:
                            start = line.index(quote) + 1
                            end = line.index(quote, start)
                            state["settings_module"] = line[start:end]
                        except ValueError:
                            pass
                        break
                break

    return state


def run_guide(stdout: Any = None) -> None:
    """Print context-aware next-step guidance.

    Args:
        stdout: Optional writable stream (defaults to ``print``).
    """
    write = stdout.write if stdout else print

    state = _detect_state()

    write("\n  📖  Django AutoApp Guide\n")
    write("  " + "=" * 40 + "\n\n")

    # --- Not in a Django project ---
    if not state["has_manage_py"]:
        write("  🔍  No Django project detected in this directory.\n\n")
        write("  To create a new project:\n\n")
        write("    Option 1 — Use django-autoapp-init:\n")
        write("      mkdir mysite && cd mysite\n")
        write("      django-autoapp-init myproject\n")
        write("      cd myproject\n\n")
        write("    Option 2 — Manual setup:\n")
        write("      django-admin startproject myproject .\n")
        write("      pip install django-autoapp\n")
        write('      # Add "django_autoapp" to INSTALLED_APPS\n\n')
        return

    # --- Inside a Django project ---
    write("  📁  Django project detected")
    if state["settings_module"]:
        write(f" ({state['settings_module']})")
    write("\n\n")

    # Show current state
    write("  Current state:\n")
    write(f"    Virtual env active:  {'✅ Yes' if state['in_venv'] else '❌ No'}\n")
    write(f"    Database exists:     {'✅ Yes' if state['has_db'] else '❌ No'}\n")
    write(f"    Docker configured:   {'✅ Yes' if state['has_docker'] else '⬜ No'}\n")
    write(f"    .env file:           {'✅ Yes' if state['has_env'] else '⬜ No'}\n")
    write(f"    Git initialized:     {'✅ Yes' if state['has_git'] else '⬜ No'}\n")
    write(f"    Apps found:          {', '.join(state['apps']) if state['apps'] else 'None'}\n")
    write("\n")

    # --- Recommendations ---
    write("  📋  Recommended next steps:\n\n")
    step = 1

    if not state["in_venv"]:
        write(f"    {step}. Activate your virtual environment:\n")
        write(f"       Windows:    ..\\venv\\Scripts\\activate\n")
        write(f"       macOS/Linux: source ../venv/bin/activate\n\n")
        step += 1

    if not state["has_db"]:
        write(f"    {step}. Run initial migrations:\n")
        write(f"       python manage.py migrate\n\n")
        step += 1

    if not state["apps"]:
        write(f"    {step}. Generate your first app:\n")
        write(f"       python manage.py autoapp blog Post\n\n")
        write(f"    {step + 1}. Register the app in settings.py and urls.py:\n")
        write(f'       Add "blog" to INSTALLED_APPS\n')
        write(f'       Add path("blog/", include("blog.urls")) to urlpatterns\n\n')
        step += 2
    else:
        write(f"    {step}. Generate another app:\n")
        write(f"       python manage.py autoapp <app_name> <ModelName>\n\n")
        step += 1

        write(f"    {step}. Generate with extras:\n")
        write(f"       python manage.py autoapp shop Product --api --tests --signals\n\n")
        step += 1

    if state["apps"] and not state["has_db"]:
        write(f"    {step}. Create migrations for your apps:\n")
        for app in state["apps"]:
            write(f"       python manage.py makemigrations {app}\n")
        write(f"       python manage.py migrate\n\n")
        step += 1

    if not state["has_docker"]:
        write(f"    {step}. Add Docker support:\n")
        write(f"       django-autoapp-init myproject --docker\n\n")
        step += 1

    write(f"    {step}. Run the development server:\n")
    write(f"       python manage.py runserver\n\n")

    write(f"    💡  Run diagnostics anytime:\n")
    write(f"       python manage.py autoapp doctor\n\n")
