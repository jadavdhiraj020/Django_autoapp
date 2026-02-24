"""Project initializer — creates Django projects with virtual environments.

Handles the full lifecycle of ``django-autoapp-init``:
venv creation, package installation, project scaffolding,
settings patching, and optional extras (git, docker, env, etc.).
"""

from __future__ import annotations

import platform
import subprocess
import textwrap
import venv
from pathlib import Path
from typing import Any

from django_autoapp.core.settings_engine import (
    add_to_installed_apps,
    get_database_config,
    set_setting,
)
from django_autoapp.utils.fs import cleanup, write_file
from django_autoapp.utils.log import error, info, log, success, warn
from django_autoapp.utils.validation import validate_project_name

__all__: list[str] = ["init_project"]

_IS_WINDOWS: bool = platform.system() == "Windows"


def _get_venv_python(venv_dir: Path) -> Path:
    """Return path to the Python interpreter inside a venv."""
    if _IS_WINDOWS:
        return venv_dir / "Scripts" / "python.exe"
    return venv_dir / "bin" / "python"


def _get_django_admin(venv_dir: Path) -> Path:
    """Return path to django-admin inside a venv."""
    if _IS_WINDOWS:
        return venv_dir / "Scripts" / "django-admin.exe"
    return venv_dir / "bin" / "django-admin"


def _get_activate_hint(project_name: str, venv_name: str) -> str:
    """Return platform-appropriate activation instructions."""
    if _IS_WINDOWS:
        activate = f"..\\{venv_name}\\Scripts\\activate"
    else:
        activate = f"source ../{venv_name}/bin/activate"
    return textwrap.dedent(f"""\

        ✅  Project '{project_name}' created successfully!

        Next steps:
          cd {project_name}
          {activate}
          python manage.py runserver
    """)


def _get_inplace_activate_hint(project_name: str, venv_name: str) -> str:
    """Return activation hint for in-place project structure."""
    if _IS_WINDOWS:
        activate = f"{venv_name}\\Scripts\\activate"
    else:
        activate = f"source {venv_name}/bin/activate"
    return textwrap.dedent(f"""\

        ✅  Project '{project_name}' created successfully! (in-place mode)

        Next steps:
          {activate}
          python manage.py runserver
    """)


def _run(
    cmd: list[str | Path],
    *,
    cwd: Path | None = None,
    label: str = "",
) -> None:
    """Execute a subprocess with clean error handling."""
    try:
        subprocess.run(
            [str(c) for c in cmd],
            cwd=str(cwd) if cwd else None,
            check=True,
            capture_output=True,
            text=True,
        )
    except subprocess.CalledProcessError as exc:
        detail = exc.stderr.strip() or exc.stdout.strip() or str(exc)
        error(f"{label} failed:\n{detail}")


def _create_venv(venv_dir: Path) -> Path:
    """Create a virtual environment and return the python path."""
    log("📦", "Creating virtual environment …")
    try:
        venv.create(str(venv_dir), with_pip=True)
    except Exception as exc:
        cleanup(venv_dir)
        error(f"Failed to create virtual environment: {exc}")

    venv_python = _get_venv_python(venv_dir)
    if not venv_python.exists():
        cleanup(venv_dir)
        error(f"Python interpreter not found at {venv_python}")

    # Upgrade pip silently
    _run(
        [venv_python, "-m", "pip", "install", "--upgrade", "pip"],
        label="pip upgrade",
    )
    return venv_python


def _install_packages(
    venv_python: Path,
    venv_dir: Path,
    *,
    django_version: str = ">=4.2",
    with_api: bool = False,
) -> None:
    """Install Django, django-autoapp, and optional packages."""
    log("📥", "Installing Django …")
    try:
        _run(
            [venv_python, "-m", "pip", "install", f"Django{django_version}"],
            label="Django install",
        )
    except SystemExit:
        cleanup(venv_dir)
        raise

    log("📥", "Installing django-autoapp …")
    try:
        _run(
            [venv_python, "-m", "pip", "install", "django-autoapp"],
            label="django-autoapp install",
        )
    except SystemExit:
        cleanup(venv_dir)
        raise

    if with_api:
        log("📥", "Installing djangorestframework …")
        try:
            _run(
                [venv_python, "-m", "pip", "install", "djangorestframework"],
                label="DRF install",
            )
        except SystemExit:
            warn("Failed to install DRF — you can install it manually later")


def _create_project(
    django_admin: Path,
    project_name: str,
    target_dir: Path,
    *,
    inplace: bool = False,
    venv_dir: Path | None = None,
) -> None:
    """Scaffold a Django project using django-admin."""
    log("🏗️", f"Creating Django project '{project_name}' …")
    if inplace:
        cmd = [django_admin, "startproject", project_name, "."]
        cwd = target_dir
    else:
        cmd = [django_admin, "startproject", project_name, str(target_dir)]
        cwd = None
    try:
        _run(cmd, cwd=cwd, label="django-admin startproject")
    except SystemExit:
        dirs_to_clean = [d for d in [venv_dir, target_dir] if d]
        cleanup(*dirs_to_clean)
        raise


def _init_git(project_dir: Path) -> None:
    """Initialize a git repository with a .gitignore and initial commit."""
    log("🔧", "Initializing git repository …")
    gitignore_content = textwrap.dedent("""\
        # Python
        __pycache__/
        *.py[cod]
        *.egg-info/
        dist/
        build/
        .eggs/

        # Virtual env
        venv/
        .venv/
        env/

        # Django
        db.sqlite3
        *.log
        staticfiles/
        media/

        # Environment
        .env
        .env.local

        # IDE
        .idea/
        .vscode/
        *.swp
        *.swo

        # OS
        .DS_Store
        Thumbs.db
    """)
    write_file(project_dir / ".gitignore", gitignore_content, force=True)

    try:
        subprocess.run(
            ["git", "init"], cwd=str(project_dir),
            check=True, capture_output=True, text=True,
        )
        subprocess.run(
            ["git", "add", "."], cwd=str(project_dir),
            check=True, capture_output=True, text=True,
        )
        subprocess.run(
            ["git", "commit", "-m", "Initial commit (django-autoapp)"],
            cwd=str(project_dir),
            check=True, capture_output=True, text=True,
        )
        info("Git repository initialized with initial commit")
    except (subprocess.CalledProcessError, FileNotFoundError) as exc:
        warn(f"Git initialization incomplete — you can finish it manually later")


def _generate_env_file(project_dir: Path, project_name: str) -> None:
    """Generate a .env file with common settings."""
    env_content = textwrap.dedent(f"""\
        # Django settings
        DJANGO_SECRET_KEY=change-me-to-a-random-secret-key
        DJANGO_DEBUG=True
        DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1

        # Database (only needed for postgres/mysql)
        DB_NAME={project_name}
        DB_USER=postgres
        DB_PASSWORD=
        DB_HOST=localhost
        DB_PORT=5432
    """)
    write_file(project_dir / ".env", env_content, force=True)
    info("Generated .env file")


def _generate_dockerfile(project_dir: Path, project_name: str) -> None:
    """Generate Dockerfile and docker-compose.yml."""
    dockerfile = textwrap.dedent(f"""\
        FROM python:3.12-slim

        ENV PYTHONDONTWRITEBYTECODE=1
        ENV PYTHONUNBUFFERED=1

        WORKDIR /app

        COPY requirements.txt .
        RUN pip install --no-cache-dir -r requirements.txt

        COPY . .

        EXPOSE 8000

        CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
    """)

    compose = textwrap.dedent(f"""\
        version: '3.8'

        services:
          web:
            build: .
            ports:
              - "8000:8000"
            volumes:
              - .:/app
            environment:
              - DJANGO_DEBUG=True
            depends_on:
              - db

          db:
            image: postgres:16-alpine
            environment:
              POSTGRES_DB: {project_name}
              POSTGRES_USER: postgres
              POSTGRES_PASSWORD: postgres
            volumes:
              - postgres_data:/var/lib/postgresql/data
            ports:
              - "5432:5432"

        volumes:
          postgres_data:
    """)

    requirements = "Django>=4.2\ndjango-autoapp\n"

    write_file(project_dir / "Dockerfile", dockerfile, force=True)
    write_file(project_dir / "docker-compose.yml", compose, force=True)
    write_file(project_dir / "requirements.txt", requirements, force=True)
    info("Generated Dockerfile, docker-compose.yml, and requirements.txt")


def init_project(options: dict[str, Any]) -> None:
    """Full project initialization with all options.

    Args:
        options: Dictionary of parsed CLI arguments containing:
            - project_name (str): Django project name
            - venv_name (str): Virtual environment directory name
            - no_venv (bool): Skip venv creation
            - inplace (bool): Create project in current directory
            - django_version (str): Django version specifier
            - with_admin_user (bool): Create superuser after project
            - with_git (bool): Initialize git
            - database (str): Database backend type
            - bootstrap (bool): Include Bootstrap base template
            - api (bool): Include DRF
            - docker (bool): Generate Docker files
            - env (bool): Generate .env file
    """
    project_name: str = options["project_name"]
    venv_name: str = options.get("venv_name", "venv")
    no_venv: bool = options.get("no_venv", False)
    inplace: bool = options.get("inplace", False)
    django_version: str = options.get("django_version", ">=4.2")
    with_git: bool = options.get("with_git", False)
    database: str | None = options.get("database")
    with_api: bool = options.get("api", False)
    docker: bool = options.get("docker", False)
    generate_env: bool = options.get("env", False)

    cwd = Path.cwd()
    venv_dir: Path = cwd / venv_name
    project_dir: Path = cwd if inplace else cwd / project_name

    # --- Validate name ------------------------------------------------
    err = validate_project_name(project_name)
    if err:
        error(err)

    # --- Guard directories -------------------------------------------
    if not no_venv and venv_dir.exists():
        error(f"Directory already exists: {venv_dir}")
    if not inplace and project_dir.exists():
        error(f"Directory already exists: {project_dir}")

    # --- Create venv --------------------------------------------------
    venv_python: Path | None = None
    if not no_venv:
        venv_python = _create_venv(venv_dir)
        _install_packages(
            venv_python,
            venv_dir,
            django_version=django_version,
            with_api=with_api,
        )
    else:
        info("Skipping virtual environment creation (--no-venv)")

    # --- Create project -----------------------------------------------
    if venv_python:
        django_admin = _get_django_admin(venv_dir)
    else:
        # Use system django-admin
        django_admin = Path("django-admin")

    if inplace:
        project_dir.mkdir(parents=True, exist_ok=True)

    _create_project(
        django_admin,
        project_name,
        project_dir,
        inplace=inplace,
        venv_dir=venv_dir if not no_venv else None,
    )

    # --- Patch settings.py -------------------------------------------
    log("⚙️", "Configuring settings.py …")
    if inplace:
        settings_path = project_dir / project_name / "settings.py"
    else:
        settings_path = project_dir / project_name / "settings.py"

    if not settings_path.exists():
        dirs_to_clean = [d for d in [venv_dir, project_dir] if d and d != cwd]
        cleanup(*dirs_to_clean)
        error(f"settings.py not found at {settings_path}")

    apps_to_add = ["django_autoapp"]
    if with_api:
        apps_to_add.append("rest_framework")
    add_to_installed_apps(settings_path, apps_to_add)

    # --- Database configuration ---------------------------------------
    if database and database != "sqlite":
        log("🗄️", f"Configuring {database} database …")
        db_config = get_database_config(database, project_name)
        set_setting(settings_path, "DATABASES", db_config)

        # Add os import if needed for env vars
        content = settings_path.read_text(encoding="utf-8")
        if "import os" not in content:
            content = "import os\n" + content
            settings_path.write_text(content, encoding="utf-8")

    # --- Optional extras ----------------------------------------------
    if generate_env:
        _generate_env_file(project_dir, project_name)

    if docker:
        _generate_dockerfile(project_dir, project_name)

    if with_git:
        _init_git(project_dir)

    # --- Done ---------------------------------------------------------
    if inplace:
        print(_get_inplace_activate_hint(project_name, venv_name))
    else:
        print(_get_activate_hint(project_name, venv_name))
