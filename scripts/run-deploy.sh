#!/usr/bin/env bash
# GitHub runner: transport only. Deployment logic lives in deploy-vps.sh.
set -euo pipefail

: "${VPS_HOST:?Configure VPS_HOST}"
: "${VPS_USER:?Configure VPS_USER}"
: "${VPS_APP_DIR:?Configure VPS_APP_DIR}"
: "${VPS_SSH_KEY:?Configure VPS_SSH_KEY}"
: "${VPS_KNOWN_HOSTS:?Configure VPS_KNOWN_HOSTS}"
: "${DEPLOY_SHA:?Configure DEPLOY_SHA}"
VPS_PORT=${VPS_PORT:-22}

# SSH joins remote arguments into a shell command; restrict them before interpolation.
[[ "$VPS_HOST" =~ ^[a-zA-Z0-9][a-zA-Z0-9.-]*$ ]] || { echo 'Invalid VPS_HOST (IPv4 or DNS required)' >&2; exit 1; }
[[ "$VPS_USER" =~ ^[a-zA-Z_][a-zA-Z0-9_-]*$ ]] || { echo 'Invalid VPS_USER' >&2; exit 1; }
[[ "$VPS_PORT" =~ ^[0-9]{1,5}$ ]] && ((10#$VPS_PORT >= 1 && 10#$VPS_PORT <= 65535)) || { echo 'Invalid VPS_PORT' >&2; exit 1; }
[[ "$VPS_APP_DIR" =~ ^/[a-zA-Z0-9_./-]+$ && "$VPS_APP_DIR" != / ]] || { echo 'Invalid VPS_APP_DIR (absolute path without spaces required)' >&2; exit 1; }
[[ "$DEPLOY_SHA" =~ ^[a-f0-9]{40}$ ]] || { echo 'Invalid commit SHA' >&2; exit 1; }

script_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
umask 077
ssh_dir=$(mktemp -d "${RUNNER_TEMP:-/tmp}/wedding-ssh.XXXXXX")
trap 'rm -rf -- "$ssh_dir"' EXIT
printf '%s\n' "$VPS_SSH_KEY" > "$ssh_dir/key"
printf '%s\n' "$VPS_KNOWN_HOSTS" > "$ssh_dir/known_hosts"

ssh -T -p "$VPS_PORT" -i "$ssh_dir/key" \
  -o BatchMode=yes -o IdentitiesOnly=yes -o StrictHostKeyChecking=yes \
  -o "UserKnownHostsFile=$ssh_dir/known_hosts" \
  -o ConnectTimeout=15 -o ServerAliveInterval=30 -o ServerAliveCountMax=6 \
  "$VPS_USER@$VPS_HOST" "bash -s -- '$VPS_APP_DIR' '$DEPLOY_SHA'" \
  < "$script_dir/deploy-vps.sh"
