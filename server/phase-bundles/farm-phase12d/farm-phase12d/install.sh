#!/usr/bin/env bash
# Phase 12d: the holding frame - USDC -> another asset kept in the executor -> USDC, 200 USD in total
# (design farm/design/design-2026-11-15-holding-frame.md, human decisions of 2026-11-15 13:45 JST).
#  - gate-ctl (11 text patches): promote checks a manifest's `holding_usd` (<= 100 per bot, <= 200
#    over all live bots, <= principal_usdc, executor with exitAll(), holding_max_hours <= 168) before
#    anything moves; stop calls the executor's exitAll() from the bot key before the sweep and, if
#    that fails, sweeps nothing and leaves the bot live (exit code 3); status shows the frame.
#  - farm-watchdog (7 text patches): a bot with holding_usd is stopped at 30 + holding_usd USD of
#    loss since promotion, and its drop between two reads may reach L + holding_usd; the gate's
#    exit_sent / exit / exit_failed nonces are known transactions.
#  - gate.json: "max_holding_usd_total": 200, "max_holding_usd_per_bot": 100 (kept if already set)
#  - prompts: common.md, roles/earner.md, roles/paper-reviewer.md, roles/live-operator.md. Edited
#    copies of the files as they were on 2026-11-15 13:48 JST; if any changed since, the script
#    stops before changing anything.
#  - decisions/human/2026-11-15-holding-frame.md and a note for meta
# Bots without holding_usd (the 3 live ones) are handled exactly as before. farm-signer, rpc-relay,
# units and keys are not touched. Checks and offline tests run before anything changes.
# farm-watchdog is restarted; if it does not come back or `gate status` fails, gate-ctl,
# farm-watchdog and gate.json are restored.
# Run from the unpacked directory: sudo ./install.sh   (safe to re-run)
set -euo pipefail
trap 'echo "install.sh failed at line $LINENO: $BASH_COMMAND" >&2' ERR
cd "$(dirname "$0")"
[[ $EUID -eq 0 ]] || { echo "run with sudo" >&2; exit 1; }
B=/opt/farm/bin
CONF=/etc/farm/gate.json
P=/srv/farm/prompts
R=$P/roles
WS=/srv/farm/ws
export PYTHONDONTWRITEBYTECODE=1
sha() { sha256sum "$1" | cut -d' ' -f1; }
OLD_GATE=833c03537d3c28b6de9fda13d11d34eee9309a418fd547b48000e63364714351
OLD_WD=5b1a3d24a97a847e63fc442dee0fd3b8f2260aa560377461a4a6d497a8df6a33
NEW_GATE=dc0d8d5a64d2b70b874576d1c2b0d9b1fad95285fa9681127dca7853d9430828
NEW_WD=4f692e414c9825168d879e15e4455725536038d48946d02bce5e8fcbe5ea13f9
declare -A OLD=(
  [common]=8b5f9671cbcd15ea320a6015bc102c24ba6c712980b7011f4298a9af7b4daf2e
  [earner]=474b6640e4de9e35acb3d66305e5f5e0a2b859b6139c667762d14da4f94a5fa9
  [paper-reviewer]=881c9a9af356b375cef315f631b6bca1f290e8bc65819326ed97341e5fae2fe4
  [live-operator]=ba530f631cf3706cdb1e4c107688f61a4b2c4a93369c1c5ca1287da5e7838ef9
)
PROMPTS=(common earner paper-reviewer live-operator)
path_of() { [[ $1 == common ]] && echo "$P/common.md" || echo "$R/$1.md"; }
tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT

echo "== checks (nothing is changed yet)"
for f in patch-12d.py test-12d.py; do
  python3 -I -B -c 'import sys; compile(open(sys.argv[1], encoding="utf-8").read(), sys.argv[1], "exec")' "$f"
done
for k in "${PROMPTS[@]}"; do
  f=$(path_of "$k"); h=$(sha "$f")
  if [[ $h == $(sha "new/$k.md") ]]; then echo "  $f: already the new version"
  elif [[ $h == "${OLD[$k]}" ]]; then echo "  $f: as expected"
  else echo "  $f changed since the bundle was built (sha256 $h, expected ${OLD[$k]}). Nothing was changed." >&2; exit 1
  fi
done
hg=$(sha $B/gate-ctl); hw=$(sha $B/farm-watchdog)
if [[ $hg == "$NEW_GATE" && $hw == "$NEW_WD" ]]; then
  echo "  gate-ctl and farm-watchdog are already the 12d versions"
  cp $B/gate-ctl $B/farm-watchdog "$tmp/"
elif [[ $hg == "$OLD_GATE" && $hw == "$OLD_WD" ]]; then
  echo "  gate-ctl and farm-watchdog: as expected"
  python3 -I -B patch-12d.py check $B/gate-ctl $B/farm-watchdog
  python3 -I -B patch-12d.py apply $B/gate-ctl $B/farm-watchdog "$tmp"
  if [[ $(sha "$tmp/gate-ctl") != "$NEW_GATE" || $(sha "$tmp/farm-watchdog") != "$NEW_WD" ]]; then
    echo "  patched files do not have the expected sha256; nothing was changed" >&2
    echo "    gate-ctl      expected $NEW_GATE" >&2
    echo "                  got      $(sha "$tmp/gate-ctl")" >&2
    echo "    farm-watchdog expected $NEW_WD" >&2
    echo "                  got      $(sha "$tmp/farm-watchdog")" >&2
    exit 1
  fi
  echo "== offline tests (installed files: report only; 7 of 37 pass before 12d)"
  python3 -I -B test-12d.py $B/gate-ctl $B/farm-watchdog /opt/farm/lib --old | tail -1
else
  echo "  gate-ctl or farm-watchdog changed since the bundle was built. Nothing was changed." >&2
  echo "    gate-ctl      expected $OLD_GATE" >&2
  echo "                  got      $hg" >&2
  echo "    farm-watchdog expected $OLD_WD" >&2
  echo "                  got      $hw" >&2
  exit 1
fi
for f in gate-ctl farm-watchdog; do
  python3 -I -B -c 'import sys; compile(open(sys.argv[1], encoding="utf-8").read(), sys.argv[1], "exec")' "$tmp/$f"
done
echo "== offline tests (patched files)"
python3 -I -B test-12d.py "$tmp/gate-ctl" "$tmp/farm-watchdog" /opt/farm/lib
python3 -I -B -c 'import json,sys; c=json.load(open(sys.argv[1])); assert "max_live_loss_usd" in c and "max_loss_per_tx_usd" in c' "$CONF"

rollback() {
  echo "!! $1 - restoring gate-ctl, farm-watchdog and gate.json" >&2
  [[ -f $B/.gate-ctl.bak-12d ]] && cp -a $B/.gate-ctl.bak-12d $B/gate-ctl
  [[ -f $B/.farm-watchdog.bak-12d ]] && cp -a $B/.farm-watchdog.bak-12d $B/farm-watchdog
  [[ -f $CONF.bak-12d ]] && cat "$CONF.bak-12d" > "$CONF"
  systemctl restart farm-watchdog.service || true
  sleep 5
  systemctl is-active farm-watchdog.service || true
  journalctl -u farm-watchdog -n 20 --no-pager >&2 || true
  exit 1
}

if [[ $hg != "$NEW_GATE" ]]; then
  echo "== gate.json"
  [[ -e $CONF.bak-12d ]] || cp -a "$CONF" "$CONF.bak-12d"
  python3 -I -B - "$CONF" > "$tmp/gate.json" <<'PY'
import json, sys
c = json.load(open(sys.argv[1], encoding="utf-8"))
c.setdefault("max_holding_usd_total", 200)
c.setdefault("max_holding_usd_per_bot", 100)
json.dump(c, sys.stdout, indent=2)
sys.stdout.write("\n")
PY
  python3 -I -B -c 'import json,sys; json.load(open(sys.argv[1]))' "$tmp/gate.json"
  cat "$tmp/gate.json" > "$CONF"         # keeps owner and mode

  echo "== install"
  [[ -e $B/.gate-ctl.bak-12d ]] || cp -a $B/gate-ctl $B/.gate-ctl.bak-12d
  [[ -e $B/.farm-watchdog.bak-12d ]] || cp -a $B/farm-watchdog $B/.farm-watchdog.bak-12d
  put() { install -o "$(stat -c %u "$2")" -g "$(stat -c %g "$2")" -m "$(stat -c %a "$2")" "$1" "$2"; }
  put "$tmp/gate-ctl" $B/gate-ctl
  put "$tmp/farm-watchdog" $B/farm-watchdog

  echo "== restart farm-watchdog"
  since=$(date '+%Y-%m-%d %H:%M:%S')
  systemctl restart farm-watchdog.service
  sleep 20                                 # one full watchdog round (15 s)
  systemctl is-active --quiet farm-watchdog.service || rollback "farm-watchdog is not active after the restart"
  journalctl -u farm-watchdog --since "$since" --no-pager | tail -n 8
fi
python3 -I -B -c 'import json,sys; c=json.load(open(sys.argv[1])); print("  gate.json: max_holding_usd_total", c.get("max_holding_usd_total"), " max_holding_usd_per_bot", c.get("max_holding_usd_per_bot"))' "$CONF"
echo "  sha256 (expected / installed)"
echo "    gate-ctl      $NEW_GATE"
echo "                  $(sha $B/gate-ctl)"
echo "    farm-watchdog $NEW_WD"
echo "                  $(sha $B/farm-watchdog)"
systemctl is-active farm-watchdog.service farm-signer.service

echo "== gate status"
sudo -u harness /opt/farm/bin/gate status > "$tmp/status.out" || rollback "gate status failed"
python3 -I -B - "$tmp/status.out" <<'PY' || cat "$tmp/status.out"
import json, sys
s = json.load(open(sys.argv[1]))
print("  capital_usd", s.get("capital_usd"), "/", s.get("max_capital_usd"), " daily_loss_usd", s.get("daily_loss_usd"),
      " frozen", s.get("frozen"), " halted", s.get("halted"))
print("  holding_usd", s.get("holding_usd"))
for b, v in sorted((s.get("live") or {}).items()):
    print(f"  {b}: {v.get('service')}  {v.get('balances_usd')}")
PY

echo "== prompts"
for k in "${PROMPTS[@]}"; do
  f=$(path_of "$k")
  if [[ $(sha "$f") != $(sha "new/$k.md") ]]; then
    cp -a "$f" "$(dirname "$f")/.$k.md.bak-12d"
    if [[ $k == common ]]; then install -o root -g root -m 644 "new/$k.md" "$f"
    else install -o harness -g harness -m 644 "new/$k.md" "$f"; fi
  fi
done
undo_prompts() {
  echo "!! restoring the previous prompt files (gate-ctl, farm-watchdog and gate.json stay installed)" >&2
  for k in "${PROMPTS[@]}"; do
    f=$(path_of "$k"); b="$(dirname "$f")/.$k.md.bak-12d"
    [[ -f $b ]] && cp -a "$b" "$f"
  done
}
echo "== assembled prompts (limit 60000, keep at or under 56000)"
echo "   expected: earner 54952, paper-reviewer 47948, researcher 39380, live-operator 36443, meta 35846"
for i in $(awk '!/^#/ && NF {print $1}' /etc/farm/roles.conf); do
  if ! /opt/farm/bin/assemble-prompt "$i"; then undo_prompts; exit 1; fi
  n=$(stat -c %s "/srv/farm/runners/$i/prompt.md")
  echo "  $i: $n bytes"
  if (( n > 56000 )); then echo "  $i is over 56000 bytes" >&2; undo_prompts; exit 1; fi
done

echo "== decision and note for meta"
install -o root -g root -m 644 decision-2026-11-15-holding-frame.md $WS/decisions/human/2026-11-15-holding-frame.md
install -o root -g root -m 644 inbox-meta-2026-11-15-phase12d-holding-frame.md \
  $WS/inbox/meta/2026-11-15-phase12d-holding-frame.md
echo "== live bots"
systemctl list-units --plain --no-legend 'bot@*.service' | awk '{print "  " $1, $3 "/" $4}'
echo "Installed phase 12d. No bot uses the frame until a manifest says holding_usd. Running sessions keep"
echo "their old prompt until their next start. Paste everything from '== checks' down."
echo "To undo: restore $B/.gate-ctl.bak-12d, $B/.farm-watchdog.bak-12d and $CONF.bak-12d, restart farm-watchdog,"
echo "restore the .bak-12d prompt files and remove the two notes"
