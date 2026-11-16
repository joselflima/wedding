from pathlib import Path
import secrets

p = Path('.env.local')
if p.exists():
    raise SystemExit('.env.local já existe; arquivo preservado.')
p.write_text('DJANGO_SECRET_KEY=' + secrets.token_urlsafe(64) + '\nDJANGO_DEBUG=false\nDJANGO_HTTPS=false\nDJANGO_ALLOWED_HOSTS=localhost,127.0.0.1\nMYSQL_DATABASE=wedding_local\nMYSQL_USER=wedding\nMYSQL_PASSWORD=' + secrets.token_urlsafe(32) + '\nMYSQL_ROOT_PASSWORD=' + secrets.token_urlsafe(32) + '\n')
p.chmod(0o600)
