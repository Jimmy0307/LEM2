#!/usr/bin/env bash
# Run a pre-deployed repo on a remote Linux host using YOUR configured SSH key.
# Does not transfer datasets, modify SSH keys, or accept passwords.
set -euo pipefail
if (( $# != 3 )); then
  echo "Usage: REMOTE_HOST=user@host REMOTE_REPO=/srv/LEM2 $0 /remote/case.json /remote/outputs /remote/repo" >&2
  echo "Use: $0 /remote/path/case.json /remote/path/output /remote/path/repo" >&2
  exit 2
fi
: "${REMOTE_HOST:?Set REMOTE_HOST=user@host (known SSH host with key installed)}"
case "$REMOTE_HOST" in *[!a-zA-Z0-9_.@-]*|'') echo 'Invalid SSH host' >&2; exit 2;; esac
case_path="$1"; output_dir="$2"; remote_repo="$3"
# shell-quote ALL supplied remote paths. Does not interpolate into commands bare.
remote_command="cd $(printf '%q' "$remote_repo") && python3 -m federated_decision_making.cli run --case $(printf '%q' "$case_path") --output $(printf '%q' "$output_dir")"
if [[ "${DRY_RUN:-0}" == "1" ]]; then
  printf 'ssh <configured-key> %s %s\n' "$REMOTE_HOST" "$remote_command"
  exit 0
fi
exec ssh -T -o BatchMode=yes -o StrictHostKeyChecking=yes -o ConnectTimeout=12 \
  -- "$REMOTE_HOST" "$remote_command"
