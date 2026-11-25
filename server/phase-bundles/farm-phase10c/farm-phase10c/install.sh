#!/usr/bin/env bash
# Phase 10c: the watchdog enforces the 30 USD live-loss stop (human decision 2026-11-10).
#  - farm-watchdog: every round, per live bot, loss since promotion = pnl.json baselines (native +
#    USDC, top-ups included) minus wallet value now (current prices); above gate.json
#    max_live_loss_usd (30) -> gate stop + wake live-operator. Skipped for a bot in a round where one
#    of its chains could not be read, and for a bot without a baseline (reported once).
#  - gate.json: "max_live_loss_usd": 30
#  - common.md: the live-loss stop as a hard constraint enforced in code
#  - decisions/human/2026-11-10-live-loss-stop-watchdog.md: promote criterion 5 is met by the
#    watchdog; reviewers stop failing bots on their own loss-accounting crash windows
# Before anything changes: patch texts, offline tests (10c + the 10b and 9i suites on the new
# watchdog), and a dry run of what the stop sees for every live bot now (stops the install if one
# would be stopped at once). If farm-watchdog does not come back, it and gate.json are restored.
set -euo pipefail
trap 'echo "install.sh failed at line $LINENO: $BASH_COMMAND" >&2' ERR
cd "$(dirname "$0")"
[[ $EUID -eq 0 ]] || { echo "run with sudo" >&2; exit 1; }
B=/opt/farm/bin E=/etc/farm P=/srv/farm/prompts
HERE=$(pwd)
tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT

python3 -I -m py_compile cfg-10c.py patch-10c.py test-10c.py regress/test-10b.py regress/test-9i.py
echo "== patch texts"
python3 -I patch-10c.py check "$B/farm-watchdog" "$P/common.md"
python3 -I patch-10c.py apply "$B/farm-watchdog" "$P/common.md" "$tmp" >/dev/null
python3 -I -m py_compile "$tmp/farm-watchdog"
echo "== offline tests"
python3 -I test-10c.py "$B/farm-watchdog" "$P/common.md" /opt/farm/lib --old || true
python3 -I test-10c.py "$tmp/farm-watchdog" "$tmp/common.md" /opt/farm/lib
echo "== regression (10b and 9i suites with the new watchdog)"
python3 -I regress/test-10b.py "$B/gate-ctl" "$B/farm-signer" "$tmp/farm-watchdog" "$tmp/common.md" /opt/farm/lib | tail -1
python3 -I regress/test-9i.py "$B/gate-ctl" "$tmp/farm-watchdog" | tail -1
echo "== dry run: what the live-loss stop sees now"
sudo -u harness /opt/farm/bin/gate status > "$tmp/status.json"
python3 -I cfg-10c.py dryrun "$tmp/farm-watchdog" "$tmp/status.json"

echo "== backups"
bak() { local d f; d=$(dirname "$1"); f=$(basename "$1"); [[ -e "$d/.$f.bak-10c" ]] || cp -a "$1" "$d/.$f.bak-10c"; }
for f in "$B/farm-watchdog" "$P/common.md" "$E/gate.json"; do bak "$f"; done

echo "== install"
put() { install -o "$(stat -c %u "$2")" -g "$(stat -c %g "$2")" -m "$(stat -c %a "$2")" "$1" "$2"; }
put "$tmp/farm-watchdog" "$B/farm-watchdog"
python3 -I cfg-10c.py apply "$E/gate.json"
since=$(date '+%Y-%m-%d %H:%M:%S')
systemctl restart farm-watchdog
sleep 25                                   # one full round (interval 15 s) with the new code
if ! systemctl is-active --quiet farm-watchdog; then
  echo "!! farm-watchdog not active - restoring" >&2
  cp -a "$B/.farm-watchdog.bak-10c" "$B/farm-watchdog"
  cp -a "$E/.gate.json.bak-10c" "$E/gate.json"
  systemctl restart farm-watchdog || true
  journalctl -u farm-watchdog --since "$since" --no-pager | tail -n 30
  exit 1
fi
echo "farm-watchdog active"
journalctl -u farm-watchdog --since "$since" --no-pager | tail -n 10

echo "== common.md, prompts, decision"
put "$tmp/common.md" "$P/common.md"
while read -r inst _; do
  [[ -z "$inst" || "$inst" == \#* ]] && continue
  /opt/farm/bin/assemble-prompt "$inst"
done < "$E/roles.conf"
d=/srv/farm/ws/decisions/human/2026-11-10-live-loss-stop-watchdog.md
[[ -e $d ]] || install -o root -g root -m 644 decision-2026-11-10-live-loss-stop-watchdog.md "$d"
ls -la "$d"
echo "Installed phase 10c. Paste everything from '== patch texts' down."
