"""CLI entry point for ``django-autoapp-init``.

Creates a fully bootstrapped Django project with a virtual environment
and ``django_autoapp`` pre-installed in a single command.

Usage::

    django-autoapp-init <project_name>
    django-autoapp-init <project_name> --docker --env --with-git
    django-autoapp-init --interactive
"""

from __future__ import annotations

import argparse
from typing import Any

from django_autoapp.core.initializer import init_project
from django_autoapp.utils.log import error
from django_autoapp.utils.validation import (
    SUPPORTED_DATABASES,
    validate_database_choice,
)

__all__: list[str] = ["main"]


def _interactive_mode() -> dict[str, Any]:
    """Run interactive guided setup, prompting the user for each option.

    Returns:
        Dictionary of options matching the CLI argument namespace.
    """
    print("\n  🧙  Django AutoApp — Interactive Setup\n")
    print("  " + "=" * 40 + "\n")

    project_name = input("  Project name: ").strip()
    if not project_name:
        error("Project name cannot be empty.")

    venv_name = input("  Virtual env folder name [venv]: ").strip() or "venv"
    no_venv = input("  Skip venv creation? (y/N): ").strip().lower() == "y"

    django_version = (
        input("  Django version [>=4.2]: ").strip() or ">=4.2"
    )

    db_input = input(f"  Database ({', '.join(SUPPORTED_DATABASES)}) [sqlite]: ").strip() or "sqlite"
    db_err = validate_database_choice(db_input)
    if db_err:
        error(db_err)

    with_api = input("  Include Django REST Framework? (y/N): ").strip().lower() == "y"
    bootstrap = input("  Include Bootstrap 5 template? (y/N): ").strip().lower() == "y"
    with_git = input("  Initialize git repository? (y/N): ").strip().lower() == "y"
    docker = input("  Generate Dockerfile + docker-compose? (y/N): ").strip().lower() == "y"
    generate_env = input("  Generate .env file? (y/N): ").strip().lower() == "y"
    with_admin = input("  Create superuser after setup? (y/N): ").strip().lower() == "y"

    # Summary
    print("\n  📋  Summary:\n")
    print(f"    Project:    {project_name}")
    print(f"    Venv:       {'skip' if no_venv else venv_name}")
    print(f"    Django:     {django_version}")
    print(f"    Database:   {db_input}")
    print(f"    DRF:        {'Yes' if with_api else 'No'}")
    print(f"    Bootstrap:  {'Yes' if bootstrap else 'No'}")
    print(f"    Git:        {'Yes' if with_git else 'No'}")
    print(f"    Docker:     {'Yes' if docker else 'No'}")
    print(f"    .env:       {'Yes' if generate_env else 'No'}")
    print(f"    Superuser:  {'Yes' if with_admin else 'No'}")
    print()

    confirm = input("  Proceed? (Y/n): ").strip().lower()
    if confirm == "n":
        print("\n  Aborted.")
        raise SystemExit(0)

    return {
        "project_name": project_name,
        "venv_name": venv_name,
        "no_venv": no_venv,
        "inplace": False,
        "django_version": django_version,
        "with_admin_user": with_admin,
        "with_git": with_git,
        "database": db_input,
        "bootstrap": bootstrap,
        "api": with_api,
        "docker": docker,
        "env": generate_env,
    }


def _build_parser() -> argparse.ArgumentParser:
    """Build the CLI argument parser with all options.

    Returns:
        Configured ``argparse.ArgumentParser`` instance.
    """
    parser = argparse.ArgumentParser(
        prog="django-autoapp-init",
        description=(
            "Bootstrap a new Django project with a virtual environment "
            "and django-autoapp pre-installed."
        ),
    )

    # Positional
    parser.add_argument(
        "project_name",
        nargs="?",
        type=str,
        help="Name of the Django project to create (valid Python identifier)",
    )

    # Project structure
    parser.add_argument(
        "--inplace",
        action="store_true",
        help="Create the project in the current directory (django-admin startproject <name> .)",
    )

    # Virtual environment
    parser.add_argument(
        "--venv-name",
        type=str,
        default="venv",
        help="Custom virtual environment folder name (default: venv)",
    )
    parser.add_argument(
        "--no-venv",
        action="store_true",
        help="Skip virtual environment creation",
    )

    # Django
    parser.add_argument(
        "--django-version",
        type=str,
        default=">=4.2",
        help="Django version specifier (default: >=4.2)",
    )

    # Extras
    parser.add_argument(
        "--with-admin-user",
        action="store_true",
        help="Create a superuser interactively after project setup",
    )
    parser.add_argument(
        "--with-git",
        action="store_true",
        help="Initialize a git repository with .gitignore and initial commit",
    )
    parser.add_argument(
        "--database",
        type=str,
        default="sqlite",
        choices=SUPPORTED_DATABASES,
        help="Database backend to configure (default: sqlite)",
    )
    parser.add_argument(
        "--bootstrap",
        action="store_true",
        help="Include Bootstrap 5 base template",
    )
    parser.add_argument(
        "--api",
        action="store_true",
        help="Install and configure Django REST Framework",
    )
    parser.add_argument(
        "--docker",
        action="store_true",
        help="Generate Dockerfile and docker-compose.yml",
    )
    parser.add_argument(
        "--env",
        action="store_true",
        help="Generate a .env file with common settings",
    )

    # Mode
    parser.add_argument(
        "--interactive",
        action="store_true",
        help="Run interactive guided setup mode",
    )

    return parser


def main() -> None:
    """Entry point for the ``django-autoapp-init`` console script."""
    parser = _build_parser()
    args = parser.parse_args()

    # Interactive mode
    if args.interactive:
        options = _interactive_mode()
        init_project(options)
        return

    # Normal mode — require project_name
    if not args.project_name:
        parser.error("project_name is required (or use --interactive)")

    # Validate database choice
    if args.database:
        db_err = validate_database_choice(args.database)
        if db_err:
            parser.error(db_err)

    options: dict[str, Any] = {
        "project_name": args.project_name,
        "venv_name": args.venv_name,
        "no_venv": args.no_venv,
        "inplace": args.inplace,
        "django_version": args.django_version,
        "with_admin_user": args.with_admin_user,
        "with_git": args.with_git,
        "database": args.database,
        "bootstrap": args.bootstrap,
        "api": args.api,
        "docker": args.docker,
        "env": args.env,
    }

    init_project(options)


if __name__ == "__main__":
    main()
