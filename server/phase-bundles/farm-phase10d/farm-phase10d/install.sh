#!/usr/bin/env bash
# Phase 10d (human decision 2026-11-11):
#  - gate-ctl: a manifest that names an executor may leave allowed_contracts empty (the signer
#    allows the gate-deployed executor from state/executor.json); without an executor the list is
#    still required
#  - run-role: the live-operator may copy a stopped bot from bots/archive to bots/paper, mkdir there,
#    and move handled inbox/live notes (its sent-back copies were blocked on 11-10)
#  - common.md: only native and USDC count as funds (X, sweep, live-loss stop); allowed_contracts is
#    what the bot wallet itself sends to
#  - decisions/human/2026-11-11-executor-bots-funds.md for meta / reviewer / earner
# Checks (patch texts, offline tests, the 10b / 9j / 9k suites on the new files) run before anything
# changes. No service restart: gate-ctl and run-role are read on every call. Backups: .<name>.bak-10d.
set -euo pipefail
trap 'echo "install.sh failed at line $LINENO: $BASH_COMMAND" >&2' ERR
cd "$(dirname "$0")"
[[ $EUID -eq 0 ]] || { echo "run with sudo" >&2; exit 1; }
B=/opt/farm/bin E=/etc/farm P=/srv/farm/prompts
tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT
INST=("$B/gate-ctl" "$B/run-role" "$P/common.md")

python3 -I -m py_compile patch-10d.py test-10d.py regress/test-10b.py regress/test-9j.py regress/test-9k.py
echo "== patch texts"
python3 -I patch-10d.py check "${INST[@]}"
python3 -I patch-10d.py apply "${INST[@]}" "$tmp" >/dev/null
python3 -I -m py_compile "$tmp/gate-ctl"
bash -n "$tmp/run-role"
echo "== offline tests"
python3 -I test-10d.py "${INST[@]}" /opt/farm/lib --old || true
python3 -I test-10d.py "$tmp/gate-ctl" "$tmp/run-role" "$tmp/common.md" /opt/farm/lib
echo "== regression (10b / 9j / 9k suites on the 10d files)"
python3 -I regress/test-10b.py "$tmp/gate-ctl" "$B/farm-signer" "$B/farm-watchdog" "$tmp/common.md" /opt/farm/lib | tail -1
python3 -I regress/test-9j.py "$tmp/gate-ctl" | tail -1
python3 -I regress/test-9k.py "$tmp/gate-ctl" "$tmp/run-role" | tail -1

echo "== backups"
bak() { local d f; d=$(dirname "$1"); f=$(basename "$1"); [[ -e "$d/.$f.bak-10d" ]] || cp -a "$1" "$d/.$f.bak-10d"; }
for f in "${INST[@]}"; do bak "$f"; done

echo "== install"
put() { install -o "$(stat -c %u "$2")" -g "$(stat -c %g "$2")" -m "$(stat -c %a "$2")" "$1" "$2"; }
put "$tmp/gate-ctl" "$B/gate-ctl"
put "$tmp/run-role" "$B/run-role"
put "$tmp/common.md" "$P/common.md"
sudo -u harness /opt/farm/bin/gate status > /dev/null && echo "gate status ok"
while read -r inst _; do
  [[ -z "$inst" || "$inst" == \#* ]] && continue
  /opt/farm/bin/assemble-prompt "$inst"
done < "$E/roles.conf"
d=/srv/farm/ws/decisions/human/2026-11-11-executor-bots-funds.md
[[ -e $d ]] || install -o root -g root -m 644 decision-2026-11-11-executor-bots-funds.md "$d"
ls -la "$d"
echo "Installed phase 10d. Paste everything from '== patch texts' down."
