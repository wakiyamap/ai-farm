#!/usr/bin/env bash
# Phase 6l: change the paper-reviewer's model (roles.conf column 4, passed to `codex exec -m`).
#   sudo REVIEWER_MODEL=gpt-6-sol ./install.sh
# The script first asks codex (as harness) for a one-word reply with that model; a wrong id fails here.
# Revert: run again with the previous id (gpt-6.1-sol).
set -euo pipefail
cd "$(dirname "$0")"
[[ $EUID -eq 0 ]] || { echo "run with sudo" >&2; exit 1; }
: "${REVIEWER_MODEL:?set REVIEWER_MODEL=<model id>, e.g. gpt-6-sol}"
. /etc/farm/farm.env
echo "smoke test: codex exec -m $REVIEWER_MODEL (as harness)"
out=$(cd /srv/farm/ws && sudo -u harness env PATH="$HARNESS_PATH" "$CODEX_BIN" exec --skip-git-repo-check -m "$REVIEWER_MODEL" \
      'Reply with the single word OK.' 2>&1 | tail -5) || true
echo "$out"
grep -q "OK" <<<"$out" || { echo "model $REVIEWER_MODEL did not answer; roles.conf left unchanged" >&2; exit 1; }
cp -a /etc/farm/roles.conf "/etc/farm/roles.conf.bak-$(date +%Y%m%d%H%M)"
sed -i -E "s/^(paper-reviewer[[:space:]]+paper-reviewer[[:space:]]+codex[[:space:]]+).*/\1$REVIEWER_MODEL/" /etc/farm/roles.conf
grep -E '^paper-reviewer' /etc/farm/roles.conf
/opt/farm/bin/assemble-prompt paper-reviewer
systemctl reset-failed agent@paper-reviewer.service 2>/dev/null || true
echo "Installed phase 6l (paper-reviewer model = $REVIEWER_MODEL). Run now: sudo systemctl start agent@paper-reviewer"
