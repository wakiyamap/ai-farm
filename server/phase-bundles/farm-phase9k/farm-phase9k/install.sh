#!/usr/bin/env bash
# Phase 9k (inbox/human/2026-11-10-meta-gate-inline-comment.md, meta a73d9b23):
#  1. gate promote reads capital_usd / max_loss_per_tx_usd / principal_usdc with a trailing
#     "# comment" and YAML quotes (morpho-watcher-ethereum crashed with ValueError on
#     "capital_usd: 16 # ..." on 11-10 02:55Z, one review cycle lost). A non-number is refused with
#     a message before anything moves. (The signer already read these through manifest_block.)
#  2. run-role: the claude-harness researcher may Edit /srv/farm/prompts/roles/TOOLS.md, as
#     common.md says (researcher-claude d54abc09 was denied). Nothing else under prompts/.
# Exact-text patches of the installed files; nothing changes if they differ. Safe to re-run.
set -euo pipefail
trap 'echo "install.sh failed at line $LINENO: $BASH_COMMAND" >&2' ERR
cd "$(dirname "$0")"
[[ $EUID -eq 0 ]] || { echo "run with sudo" >&2; exit 1; }
B=/opt/farm/bin
tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT

python3 -I patch-9k.py check "$B/gate-ctl" "$B/run-role"
python3 -I patch-9k.py apply "$B/gate-ctl" "$B/run-role" "$tmp" >/dev/null
python3 -I -m py_compile "$tmp/gate-ctl"
bash -n "$tmp/run-role"
echo "== offline tests"
python3 -I test-9k.py "$B/gate-ctl" "$B/run-role" --old || true
python3 -I test-9k.py "$tmp/gate-ctl" "$tmp/run-role"
for f in gate-ctl run-role; do
  [[ -e "$B/.$f.bak-9k" ]] || cp -a "$B/$f" "$B/.$f.bak-9k"
done
install -o root -g root -m 755 "$tmp/gate-ctl" "$tmp/run-role" "$B/"
sudo -u harness /opt/farm/bin/gate status >/dev/null && echo "gate status: ok"
echo "Installed phase 9k. researcher-claude picks up the permission at its next run (16:10 JST)."
