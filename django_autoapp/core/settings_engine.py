"""AST-based Django settings.py modification engine.

Provides safe, idempotent editing of ``INSTALLED_APPS`` and other
settings without breaking formatting or introducing duplicates.
"""

from __future__ import annotations

import ast
import re
from pathlib import Path
from typing import Sequence

from django_autoapp.utils.log import info, warn, error

__all__: list[str] = [
    "add_to_installed_apps",
    "set_setting",
    "get_database_config",
]


def _read_settings(path: Path) -> str:
    """Read settings.py content.

    Args:
        path: Absolute path to settings.py.

    Returns:
        File content as string.
    """
    if not path.exists():
        error(f"settings.py not found at {path}")
    return path.read_text(encoding="utf-8")


def _find_list_assignment(
    source: str, variable_name: str
) -> tuple[int, int, str] | None:
    """Find a list/tuple assignment in Python source using AST.

    Args:
        source: Python source code.
        variable_name: Name of the variable to find (e.g. 'INSTALLED_APPS').

    Returns:
        Tuple of (start_offset, end_offset, bracket_type) or None.
        bracket_type is '[' for list or '(' for tuple.
    """
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return None

    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == variable_name:
                    value = node.value
                    if isinstance(value, (ast.List, ast.Tuple)):
                        bracket = "[" if isinstance(value, ast.List) else "("
                        # AST gives us line/col info
                        start_line = value.lineno
                        end_line = value.end_lineno
                        start_col = value.col_offset
                        end_col = value.end_col_offset
                        if end_line is not None and end_col is not None:
                            lines = source.splitlines(keepends=True)
                            # Calculate byte offsets
                            start_offset = sum(len(l) for l in lines[:start_line - 1]) + start_col
                            end_offset = sum(len(l) for l in lines[:end_line - 1]) + end_col
                            return (start_offset, end_offset, bracket)
    return None


def add_to_installed_apps(
    settings_path: Path,
    app_names: str | Sequence[str],
) -> None:
    """Insert app name(s) into INSTALLED_APPS if not already present.

    Uses AST parsing to safely locate the list boundaries, then
    inserts the entry before the closing bracket with correct indentation.

    Args:
        settings_path: Path to the Django settings.py file.
        app_names: Single app name or sequence of app names to insert.
    """
    if isinstance(app_names, str):
        app_names = [app_names]

    content = _read_settings(settings_path)

    apps_to_add: list[str] = []
    for app_name in app_names:
        if app_name in content:
            warn(f"'{app_name}' already in settings — skipped")
        else:
            apps_to_add.append(app_name)

    if not apps_to_add:
        return

    # Try AST-based approach first
    result = _find_list_assignment(content, "INSTALLED_APPS")

    if result is not None:
        start_offset, end_offset, bracket_type = result
        close_bracket = "]" if bracket_type == "[" else ")"
        list_content = content[start_offset:end_offset]

        # Find insertion point: just before the closing bracket
        close_idx = list_content.rfind(close_bracket)
        if close_idx == -1:
            error("Could not find closing bracket of INSTALLED_APPS")

        # Determine indentation from existing entries
        indent = "    "
        lines_in_list = list_content[:close_idx].splitlines()
        for line in reversed(lines_in_list):
            stripped = line.lstrip()
            if stripped.startswith(("'", '"')):
                indent = line[: len(line) - len(stripped)]
                break

        # Build insertion string
        insertion = ""
        for app_name in apps_to_add:
            insertion += f'{indent}"{app_name}",\n'

        abs_close = start_offset + close_idx
        patched = content[:abs_close] + insertion + content[abs_close:]
        settings_path.write_text(patched, encoding="utf-8")

        for app_name in apps_to_add:
            info(f"Added '{app_name}' to INSTALLED_APPS")
        return

    # Fallback: line-based approach (for non-standard formatting)
    marker_idx = content.find("INSTALLED_APPS")
    if marker_idx == -1:
        error("Could not locate INSTALLED_APPS in settings.py")

    bracket_idx = content.find("]", marker_idx)
    if bracket_idx == -1:
        bracket_idx = content.find(")", marker_idx)
    if bracket_idx == -1:
        error("Could not find closing bracket of INSTALLED_APPS")

    # Detect indentation
    last_nl = content.rfind("\n", marker_idx, bracket_idx)
    indent = "    "
    if last_nl != -1:
        line_after = content[last_nl + 1 : bracket_idx]
        indent = ""
        for ch in line_after:
            if ch in (" ", "\t"):
                indent += ch
            else:
                break
        if not indent:
            indent = "    "

    insertion = ""
    for app_name in apps_to_add:
        insertion += f'{indent}"{app_name}",\n'

    patched = content[:bracket_idx] + insertion + content[bracket_idx:]
    settings_path.write_text(patched, encoding="utf-8")

    for app_name in apps_to_add:
        info(f"Added '{app_name}' to INSTALLED_APPS")


def set_setting(settings_path: Path, key: str, value: str) -> None:
    """Set or replace a top-level setting in settings.py.

    If the key exists, replaces its value. If not, appends it.

    Args:
        settings_path: Path to settings.py.
        key: Setting name (e.g. 'SECRET_KEY').
        value: The raw Python expression string to assign.
    """
    content = _read_settings(settings_path)

    pattern = re.compile(rf"^{re.escape(key)}\s*=\s*.+$", re.MULTILINE)
    new_line = f"{key} = {value}"

    if pattern.search(content):
        content = pattern.sub(new_line, content, count=1)
    else:
        content = content.rstrip() + f"\n\n{new_line}\n"

    settings_path.write_text(content, encoding="utf-8")
    info(f"Set {key} in settings.py")


def get_database_config(db_type: str, project_name: str) -> str:
    """Generate a DATABASES configuration string for settings.py.

    Args:
        db_type: One of 'sqlite', 'postgres', 'mysql'.
        project_name: The project name (used for database naming).

    Returns:
        Python source code string for DATABASES setting.
    """
    if db_type == "sqlite":
        return (
            "DATABASES = {\n"
            "    'default': {\n"
            "        'ENGINE': 'django.db.backends.sqlite3',\n"
            "        'NAME': BASE_DIR / 'db.sqlite3',\n"
            "    }\n"
            "}"
        )
    elif db_type == "postgres":
        return (
            "DATABASES = {\n"
            "    'default': {\n"
            "        'ENGINE': 'django.db.backends.postgresql',\n"
            f"        'NAME': os.environ.get('DB_NAME', '{project_name}'),\n"
            "        'USER': os.environ.get('DB_USER', 'postgres'),\n"
            "        'PASSWORD': os.environ.get('DB_PASSWORD', ''),\n"
            "        'HOST': os.environ.get('DB_HOST', 'localhost'),\n"
            "        'PORT': os.environ.get('DB_PORT', '5432'),\n"
            "    }\n"
            "}"
        )
    elif db_type == "mysql":
        return (
            "DATABASES = {\n"
            "    'default': {\n"
            "        'ENGINE': 'django.db.backends.mysql',\n"
            f"        'NAME': os.environ.get('DB_NAME', '{project_name}'),\n"
            "        'USER': os.environ.get('DB_USER', 'root'),\n"
            "        'PASSWORD': os.environ.get('DB_PASSWORD', ''),\n"
            "        'HOST': os.environ.get('DB_HOST', 'localhost'),\n"
            "        'PORT': os.environ.get('DB_PORT', '3306'),\n"
            "    }\n"
            "}"
        )
    return ""
