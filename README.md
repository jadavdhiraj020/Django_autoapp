# Django AutoApp

[![PyPI version](https://img.shields.io/pypi/v/django-autoapp.svg)](https://pypi.org/project/django-autoapp/)
[![Python](https://img.shields.io/pypi/pyversions/django-autoapp.svg)](https://pypi.org/project/django-autoapp/)
[![Django](https://img.shields.io/badge/Django-4.2%2B-green.svg)](https://www.djangoproject.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

**Auto-generate Django apps with full CRUD boilerplate** — models, views, URLs, forms, admin, templates, and static files — in a single command.

## Installation

```sh
pip install django-autoapp
```

## Quick Start — New Project from Scratch

Bootstrap a full Django project + virtual environment in one command:

```sh
mkdir my_site && cd my_site
django-autoapp-init myproject
```

This creates:

```
my_site/
├── venv/              ← isolated virtual environment
└── myproject/         ← Django project (manage.py, settings, etc.)
```

Then follow the printed instructions:

```sh
cd myproject
..\venv\Scripts\activate      # Windows
source ../venv/bin/activate   # macOS / Linux
python manage.py autoapp blog Post
python manage.py runserver
```

## Adding to an Existing Project

Add to your `INSTALLED_APPS`:

```python
INSTALLED_APPS = [
    # ...
    "django_autoapp",
]
```

## Usage

```sh
python manage.py autoapp <APP_NAME> <MODEL_NAME>
```

### Example

```sh
python manage.py autoapp blog Post
```

This generates a complete `blog/` app with a `Post` model, including:

- `models.py` — Model with `name`, `created_at`, `updated_at` fields
- `views.py` — ListView, CreateView, DetailView, UpdateView, DeleteView
- `urls.py` — URL patterns with proper namespacing
- `forms.py` — ModelForm
- `admin.py` — Admin registration with all fields displayed
- `apps.py` — AppConfig
- `templates/` — List, form, detail, and confirm-delete HTML templates
- `management/commands/run_project.py` — One-command project runner

### Options

| Flag | Description |
|------|-------------|
| `--dry-run` | Simulate execution without writing any files |
| `--force` | Overwrite existing files and directories |
| `--template-dir PATH` | Use a custom Jinja2 template directory |

## Requirements

- Python ≥ 3.10
- Django ≥ 4.2
- Jinja2 ≥ 3.1

## License

[MIT](LICENSE)
