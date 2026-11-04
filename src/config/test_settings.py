"""Isolated fast checks; database constraint acceptance also runs against MySQL."""
import os
os.environ.setdefault("DJANGO_SECRET_KEY", "isolated-tests-only")
from .settings import *  # noqa: F403
DATABASES = {"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": ":memory:"}}
PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]
