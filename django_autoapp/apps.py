"""Django AppConfig for the django_autoapp package."""

from __future__ import annotations

from django.apps import AppConfig


class DjangoAutoappConfig(AppConfig):
    """Configuration for the Django AutoApp code-generation package.

    Registers the ``autoapp`` management command for generating
    Django apps with full CRUD boilerplate.
    """

    default_auto_field: str = "django.db.models.BigAutoField"
    name: str = "django_autoapp"
    verbose_name: str = "Django AutoApp"
    label: str = "django_autoapp"
