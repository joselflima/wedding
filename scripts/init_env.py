"""Generate local-only secrets without replacing existing configuration."""
import os
from pathlib import Path
import secrets

root = Path(__file__).resolve().parent.parent
path = root / ".env"
secret_keys = {"DJANGO_SECRET_KEY", "MYSQL_PASSWORD", "MYSQL_ROOT_PASSWORD", "DEMO_PASSWORD"}
try:
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
except FileExistsError:
    print("O arquivo .env já existe; nada foi alterado.")
else:
    with os.fdopen(fd, "w") as stream:
        for line in (root / ".env.example").read_text().splitlines():
            key = line.split("=", 1)[0]
            stream.write(f"{key}={secrets.token_urlsafe(36)}\n" if key in secret_keys else line + "\n")
    print("Arquivo .env criado com segredos locais. Consulte DEMO_USERNAME e DEMO_PASSWORD para entrar.")
