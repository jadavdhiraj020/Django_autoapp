"""Management command to auto-generate Django apps with full CRUD boilerplate.

Supports subcommands ``doctor`` and ``guide`` for diagnostics and
context-aware help.

Usage::

    python manage.py autoapp <app_name> <model_name>
    python manage.py autoapp <app_name> <model_name> --api --tests --signals
    python manage.py autoapp doctor
    python manage.py autoapp guide
"""

from __future__ import annotations

from typing import Any

from django.core.management.base import BaseCommand, CommandError

__all__: list[str] = ["Command"]

# Subcommand names
_SUBCOMMANDS: frozenset[str] = frozenset({"doctor", "guide"})


class Command(BaseCommand):
    """Auto-generate a Django app with boilerplate CRUD code.

    Also provides ``doctor`` and ``guide`` subcommands for
    project diagnostics and context-aware guidance.

    Usage:
        python manage.py autoapp <app_name> <model_name> [options]
        python manage.py autoapp doctor
        python manage.py autoapp guide
    """

    help: str = (
        "Auto-generates Django app with boilerplate code including models, views, urls, "
        "forms, admin, templates, static files, and management commands. "
        "Also supports: autoapp doctor, autoapp guide."
    )

    def add_arguments(self, parser: Any) -> None:
        """Register CLI arguments for the autoapp command.

        Args:
            parser: The argparse.ArgumentParser instance provided by Django.
        """
        parser.add_argument(
            "app_name",
            type=str,
            help="Name of the new Django app, or subcommand (doctor, guide)",
        )
        parser.add_argument(
            "model_name",
            nargs="?",
            type=str,
            default=None,
            help="Name of the primary model",
        )
        parser.add_argument(
            "--template-dir",
            type=str,
            default=None,
            help="Custom template directory path",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Simulate execution without writing files",
        )
        parser.add_argument(
            "--force",
            action="store_true",
            help="Overwrite existing files",
        )

        # --- Enhanced generator flags ---
        parser.add_argument(
            "--api",
            action="store_true",
            help="Generate DRF serializers and viewsets",
        )
        parser.add_argument(
            "--auth",
            action="store_true",
            help="Add LoginRequiredMixin to views",
        )
        parser.add_argument(
            "--pagination",
            action="store_true",
            help="Add pagination support",
        )
        parser.add_argument(
            "--search",
            action="store_true",
            help="Add search functionality",
        )
        parser.add_argument(
            "--filters",
            action="store_true",
            help="Add filtering support",
        )
        parser.add_argument(
            "--signals",
            action="store_true",
            help="Generate signals.py",
        )
        parser.add_argument(
            "--tests",
            action="store_true",
            help="Generate basic unit tests",
        )
        parser.add_argument(
            "--docs",
            action="store_true",
            help="Generate markdown documentation",
        )

    def handle(self, *args: Any, **options: Any) -> None:
        """Execute the autoapp command or a subcommand.

        Args:
            *args: Positional arguments (unused).
            **options: Parsed command-line options.
        """
        app_name: str = options["app_name"].strip()

        # --- Subcommands ---
        if app_name == "doctor":
            self._run_doctor()
            return

        if app_name == "guide":
            self._run_guide()
            return

        # --- App generation ---
        model_name: str | None = options.get("model_name")
        if not model_name:
            raise CommandError(
                "model_name is required for app generation.\n"
                "Usage: python manage.py autoapp <app_name> <model_name>\n"
                "       python manage.py autoapp doctor\n"
                "       python manage.py autoapp guide"
            )
        model_name = model_name.strip()

        # Validate inputs
        from django_autoapp.utils.validation import validate_app_name, validate_model_name

        app_err = validate_app_name(app_name)
        if app_err:
            raise CommandError(app_err)

        model_err = validate_model_name(model_name)
        if model_err:
            raise CommandError(model_err)

        # Check if app already exists
        from pathlib import Path

        app_path = Path.cwd() / app_name
        if app_path.exists() and not options["force"]:
            raise CommandError(
                f"Application '{app_name}' already exists. Use --force to overwrite."
            )

        # Generate app using the new generator
        from django_autoapp.generators.app import generate_app

        skipped: set[str] = set()

        try:
            generate_app(
                app_name,
                model_name,
                template_dir=options.get("template_dir"),
                force=options["force"],
                dry_run=options["dry_run"],
                with_api=options["api"],
                with_auth=options["auth"],
                with_pagination=options["pagination"],
                with_search=options["search"],
                with_filters=options["filters"],
                with_signals=options["signals"],
                with_tests=options["tests"],
                with_docs=options["docs"],
                skipped=skipped,
            )
        except FileNotFoundError as e:
            raise CommandError(str(e)) from e
        except Exception as e:
            raise CommandError(f"Error generating app: {e}") from e

        # Final output
        self.stdout.write(
            self.style.SUCCESS(f"\nSuccessfully created app '{app_name}'")
        )

        # Show what extras were generated
        extras = []
        if options["api"]:
            extras.append("DRF serializers + viewsets")
        if options["signals"]:
            extras.append("signals.py")
        if options["tests"]:
            extras.append("tests.py")
        if options["docs"]:
            extras.append("README.md")
        if extras:
            self.stdout.write(
                self.style.SUCCESS(f"  Extras: {', '.join(extras)}")
            )

        if skipped:
            self.stdout.write(self.style.WARNING("\nSkipped items:"))
            for item in sorted(skipped):
                self.stdout.write(f"  - {item}")

        if options["dry_run"]:
            self.stdout.write(
                self.style.WARNING("\nDRY RUN: No files were actually written")
            )

    def _run_doctor(self) -> None:
        """Run the doctor diagnostics command."""
        from django_autoapp.core.doctor import run_doctor

        run_doctor(stdout=self.stdout)

    def _run_guide(self) -> None:
        """Run the context-aware guide command."""
        from django_autoapp.core.guide import run_guide

        run_guide(stdout=self.stdout)
