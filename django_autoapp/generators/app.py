"""Enhanced app generator — extends the existing autoapp with optional extras.

Handles generation of DRF serializers/viewsets, signals, tests, auth mixins,
pagination, search, and filtering based on CLI flags.
"""

from __future__ import annotations

import importlib.resources
import logging
from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader, StrictUndefined, TemplateNotFound

from django_autoapp.utils.fs import create_directory, write_file

__all__: list[str] = ["generate_app"]

logger: logging.Logger = logging.getLogger(__name__)

DEFAULT_TEMPLATE_DIR: str = "codegen_templates"


def _get_templates_dir(custom_dir: str | None = None) -> Path:
    """Resolve the templates directory path.

    Args:
        custom_dir: Optional custom template directory path.

    Returns:
        Resolved path to templates directory.
    """
    if custom_dir and custom_dir != DEFAULT_TEMPLATE_DIR:
        custom_path = Path(custom_dir)
        if custom_path.exists():
            return custom_path

    try:
        ref = importlib.resources.files("django_autoapp").joinpath(
            f"templates/{DEFAULT_TEMPLATE_DIR}"
        )
        path = Path(str(ref))
        if path.is_dir():
            return path
    except (TypeError, FileNotFoundError):
        pass

    raise FileNotFoundError(
        "Templates directory not found. Provide --template-dir option."
    )


def _get_jinja_env(
    search_paths: list[str], html: bool = False
) -> Environment:
    """Create a configured Jinja2 environment."""
    return Environment(
        loader=FileSystemLoader(search_paths),
        undefined=StrictUndefined,
        autoescape=html,
        block_start_string="<%" if html else "{%",
        block_end_string="%>" if html else "%}",
        variable_start_string="<<" if html else "{{",
        variable_end_string=">>" if html else "}}",
        comment_start_string="<#" if html else "{#",
        comment_end_string="#>" if html else "#}",
        lstrip_blocks=True,
        trim_blocks=True,
    )


def _render_templates(
    env: Environment,
    templates: dict[str, Path],
    context: dict[str, Any],
    *,
    force: bool = False,
    dry_run: bool = False,
    skipped: set[str] | None = None,
) -> None:
    """Batch-render templates to output paths."""
    for template_name, output_path in templates.items():
        try:
            template = env.get_template(template_name)
            content = template.render(context)
            write_file(output_path, content, force=force, dry_run=dry_run, skipped=skipped)
        except TemplateNotFound:
            logger.warning("Template not found: %s", template_name)
        except Exception as e:
            logger.error("Error rendering %s: %s", template_name, e)
            raise


def generate_app(
    app_name: str,
    model_name: str,
    *,
    template_dir: str | None = None,
    force: bool = False,
    dry_run: bool = False,
    with_api: bool = False,
    with_auth: bool = False,
    with_pagination: bool = False,
    with_search: bool = False,
    with_filters: bool = False,
    with_signals: bool = False,
    with_tests: bool = False,
    with_docs: bool = False,
    skipped: set[str] | None = None,
) -> None:
    """Generate a Django app with all boilerplate code.

    Args:
        app_name: Name of the Django app.
        model_name: Name of the primary model.
        template_dir: Optional custom template directory.
        force: Overwrite existing files.
        dry_run: Simulate without writing.
        with_api: Generate DRF serializers and viewsets.
        with_auth: Add LoginRequiredMixin to views.
        with_pagination: Add pagination support.
        with_search: Add search functionality.
        with_filters: Add filtering support.
        with_signals: Generate signals.py.
        with_tests: Generate tests.py.
        with_docs: Generate documentation markdown.
        skipped: Set to track skipped files.
    """
    from django.utils.crypto import get_random_string

    templates_dir = _get_templates_dir(template_dir)
    project_root = Path.cwd()
    app_path = project_root / app_name

    # Create directory structure
    dirs = [
        app_path,
        app_path / "migrations",
        app_path / "templates" / app_name,
        app_path / "management" / "commands",
    ]
    for d in dirs:
        create_directory(d, dry_run=dry_run, skipped=skipped)

    # Create __init__.py files
    init_files = [
        app_path / "__init__.py",
        app_path / "migrations" / "__init__.py",
        app_path / "management" / "__init__.py",
        app_path / "management" / "commands" / "__init__.py",
    ]
    for f in init_files:
        write_file(f, "", force=force, dry_run=dry_run, skipped=skipped)

    # Template context
    context: dict[str, Any] = {
        "app_name": app_name,
        "model_name": model_name,
        "secret_key": get_random_string(50),
        "with_auth": with_auth,
        "with_pagination": with_pagination,
        "with_search": with_search,
        "with_filters": with_filters,
        "urls": {
            "create": f"{app_name}:{model_name.lower()}_create",
            "update": f"{app_name}:{model_name.lower()}_update",
            "delete": f"{app_name}:{model_name.lower()}_delete",
            "list": f"{app_name}:{model_name.lower()}_list",
        },
    }

    # --- Python templates (existing) ---
    python_env = _get_jinja_env([str(templates_dir)])
    python_templates: dict[str, Path] = {
        "models.j2": app_path / "models.py",
        "views.j2": app_path / "views.py",
        "urls.j2": app_path / "urls.py",
        "forms.j2": app_path / "forms.py",
        "admin.j2": app_path / "admin.py",
        "run_project.j2": app_path / "management" / "commands" / "run_project.py",
        "apps.j2": app_path / "apps.py",
    }

    # --- Optional extras ---
    if with_api:
        python_templates["serializers.j2"] = app_path / "serializers.py"
        python_templates["viewsets.j2"] = app_path / "viewsets.py"
        python_templates["api_urls.j2"] = app_path / "api_urls.py"

    if with_signals:
        python_templates["signals.j2"] = app_path / "signals.py"

    if with_tests:
        python_templates["tests.j2"] = app_path / "tests.py"

    _render_templates(
        python_env, python_templates, context,
        force=force, dry_run=dry_run, skipped=skipped,
    )

    # --- HTML templates ---
    html_env = _get_jinja_env(
        [str(project_root / "templates"), str(templates_dir)], html=True
    )
    html_templates: dict[str, Path] = {
        "list_template.j2": app_path / "templates" / app_name / f"{model_name.lower()}_list.html",
        "form_template.j2": app_path / "templates" / app_name / f"{model_name.lower()}_form.html",
        "confirm_delete_template.j2": app_path / "templates" / app_name / f"{model_name.lower()}_confirm_delete.html",
        "detail_template.j2": app_path / "templates" / app_name / f"{model_name.lower()}_detail.html",
        "project_base_template.j2": project_root / "templates" / "base.html",
        "project_nav_template.j2": project_root / "templates" / "navbar.html",
    }
    _render_templates(
        html_env, html_templates, context,
        force=force, dry_run=dry_run, skipped=skipped,
    )

    # --- Static files ---
    static_files: dict[Path, str] = {
        project_root / "static/css/style.css": "/* Basic CSS */\nbody { font-family: Arial, sans-serif; }\n",
        project_root / "static/js/script.js": "// Basic JS\nconsole.log('Hello from script.js');\n",
    }
    for path, content in static_files.items():
        write_file(path, content, force=force, dry_run=dry_run, skipped=skipped)

    # --- Documentation ---
    if with_docs:
        docs_content = f"""# {app_name.title()} App

## Model: {model_name}

### Fields
- `name` — CharField (max_length=255, unique)
- `created_at` — DateTimeField (auto_now_add)
- `updated_at` — DateTimeField (auto_now)

### URL Patterns

| URL | View | Name |
|-----|------|------|
| `/{app_name}/` | {model_name}ListView | `{app_name}:{model_name.lower()}_list` |
| `/{app_name}/create/` | {model_name}CreateView | `{app_name}:{model_name.lower()}_create` |
| `/{app_name}/<pk>/` | {model_name}DetailView | `{app_name}:{model_name.lower()}_detail` |
| `/{app_name}/<pk>/update/` | {model_name}UpdateView | `{app_name}:{model_name.lower()}_update` |
| `/{app_name}/<pk>/delete/` | {model_name}DeleteView | `{app_name}:{model_name.lower()}_delete` |

### Setup

1. Add `"{app_name}"` to `INSTALLED_APPS`
2. Add `path("{app_name}/", include("{app_name}.urls"))` to project `urls.py`
3. Run `python manage.py makemigrations {app_name}`
4. Run `python manage.py migrate`
"""
        write_file(
            app_path / "README.md", docs_content,
            force=force, dry_run=dry_run, skipped=skipped,
        )
