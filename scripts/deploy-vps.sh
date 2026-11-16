#!/usr/bin/env bash
set -Eeuo pipefail
umask 077
# Installed on the server, invoked by a forced-command SSH key.
revision=${SSH_ORIGINAL_COMMAND:-${1:-}}
[[ "$revision" =~ ^[0-9a-f]{40}$ ]] || { echo 'Invalid revision'; exit 2; }
exec 9>/docker/wedding.deploy.lock
flock -w 1800 9
release="/docker/wedding-releases/$revision"
mkdir -p "$release" /docker/wedding/backups
# Each archive comes from git archive of the workflow checkout.
tar -xz --no-same-owner -C "$release"
cd "$release"
docker build -t "wedding-base:$revision" .
python3 - "$revision" <<'PY'
from pathlib import Path
import re, sys
s = Path('compose.vps.yaml').read_text()
s = re.sub(r'    build:\n      context: .*\n', '', s)
s = re.sub(r'    image: wedding-base:.*', '    image: wedding-base:' + sys.argv[1], s)
Path('compose.deploy.yaml').write_text(s)
PY
compose=(docker compose --project-name wedding --env-file /docker/wedding/.env -f "$release/compose.deploy.yaml")
"${compose[@]}" config --quiet
"${compose[@]}" run --rm --no-deps web python manage.py check --deploy --fail-level WARNING
# Existing production DB is already running; never recreate it during code deploys.
docker compose -f /docker/wedding/docker-compose.yml --env-file /docker/wedding/.env exec -T db sh -c 'MYSQL_PWD="$MYSQL_PASSWORD" mysqldump -u"$MYSQL_USER" --single-transaction --no-tablespaces "$MYSQL_DATABASE"' | gzip > "/docker/wedding/backups/$revision-$(date -u +%Y%m%dT%H%M%SZ).sql.gz"
"${compose[@]}" run --rm --no-deps web python manage.py migrate --noinput
cp /docker/wedding/docker-compose.yml /docker/wedding/compose.previous.yaml
cp "$release/compose.deploy.yaml" /docker/wedding/docker-compose.yml
cd /docker/wedding
docker compose up -d --no-deps --no-build web
curl --fail --silent --show-error --retry 12 --retry-all-errors --retry-delay 5 --max-time 10 https://wedding.srv1625057.hstgr.cloud/health/
printf '%s\n' "$revision" > /docker/wedding/deployed-revision
