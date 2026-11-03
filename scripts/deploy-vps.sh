#!/usr/bin/env bash
# Runs on the VPS. No credentials or server-specific values belong in this file.
set -euo pipefail

app_dir=${1:?Usage: deploy-vps.sh /absolute/application/path commit-sha}
commit=${2:?Commit SHA is required}
[[ "$commit" =~ ^[a-f0-9]{40}$ ]] || { echo 'Invalid commit SHA' >&2; exit 1; }
[[ "$app_dir" == /* && "$app_dir" != / ]] || { echo 'An absolute application directory is required' >&2; exit 1; }
cd -- "$app_dir"
[[ -d .git && -f .env && -f compose.production.yaml ]] || {
  echo 'VPS not prepared: repository clone, .env and compose.production.yaml are required.' >&2
  exit 1
}
command -v flock >/dev/null
# Also protects deployments started manually on the server.
exec 9>.deploy.lock
flock -n 9 || { echo 'Another deployment is running on this VPS.' >&2; exit 1; }
[[ -z "$(git status --porcelain --untracked-files=no)" ]] || {
  echo 'Tracked files have local changes; deployment aborted without overwriting them.' >&2
  exit 1
}
export GIT_TERMINAL_PROMPT=0
git fetch --no-tags origin '+refs/heads/main:refs/remotes/origin/main'
if [[ "$(git rev-parse refs/remotes/origin/main)" != "$commit" ]]; then
  echo 'Skipping superseded deployment: main no longer points to this commit.'
  exit 0
fi
git checkout --detach "$commit"

# Stable project name preserves the existing MySQL volume across updates.
compose=(docker compose --project-name wedding --env-file .env -f compose.yaml -f compose.production.yaml)
"${compose[@]}" config --quiet
"${compose[@]}" build web
"${compose[@]}" up -d --wait db
"${compose[@]}" run --rm web python manage.py check --deploy --fail-level WARNING
"${compose[@]}" run --rm web python manage.py migrate --noinput
"${compose[@]}" up -d --wait --wait-timeout 120 --remove-orphans
printf 'Deployment completed: %s\n' "$commit"
