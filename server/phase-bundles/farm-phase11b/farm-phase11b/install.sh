#!/usr/bin/env bash
# Phase 11b: farm-dash shows what phases 7 to 11a added (2026-11-13). Read-only additions to the
# page, data.json and brief.txt (Copy for Claude):
#  - tiles: Alchemy CU this cycle (relay count against the 95.2M allowance, where it is heading,
#    USD at 0.53 per 1M), Feed CU today (farm-feed, 8546), Services (relay, feed, signer, watchdog,
#    search, model server, every fork@)
#  - badges for what wants a look: a service that is not active, a live bot that is not running,
#    a bot near the 30 USD live-loss stop or without a baseline, an unresolved sweep transfer in
#    pnl.json, the feed down / out of budget, a prompt above 56,000 bytes, Alchemy heading above
#    its allowance
#  - live bots: loss since promotion against the watchdog's stop, realized today, nonces
#  - intermediate wallet per chain (all nine), the newest gate.log records (sweep PnL, failures)
#  - Alchemy today by chain and lane with mean latency, feed subscriptions, prompt sizes,
#    the newest decisions/human files, KB leads by status
# Cost: no extra Alchemy CU on a normal page load. The native/USD price for "loss since promotion"
# is read through the research lane (public nodes first) at most once per 5 minutes per chain that
# has a live bot. Only farm-dash is changed and restarted; if it does not come back, the previous
# file is restored. Backup: /opt/farm/bin/.farm-dash.bak-11b. Safe to re-run.
set -euo pipefail
trap 'echo "install.sh failed at line $LINENO: $BASH_COMMAND" >&2' ERR
cd "$(dirname "$0")"
[[ $EUID -eq 0 ]] || { echo "run with sudo" >&2; exit 1; }
B=/opt/farm/bin
tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT
export PYTHONDONTWRITEBYTECODE=1
pyc() { python3 -I -B -c 'import sys; compile(open(sys.argv[1], encoding="utf-8").read(), sys.argv[1], "exec")' "$1"; }

for f in patch-11b.py test-11b.py block-11b.py; do pyc "$f"; done
echo "== patch texts"
python3 -I -B patch-11b.py check "$B/farm-dash"
python3 -I -B patch-11b.py apply "$B/farm-dash" "$tmp" >/dev/null
pyc "$tmp/farm-dash"
echo "== offline tests (installed file: report only)"
python3 -I -B test-11b.py "$B/farm-dash" --old | grep -c FAIL | sed 's/^/  FAIL before the patch: /' || true
echo "== offline tests (patched file)"
python3 -I -B test-11b.py "$tmp/farm-dash"

echo "== backup"
[[ -e "$B/.farm-dash.bak-11b" ]] || cp -a "$B/farm-dash" "$B/.farm-dash.bak-11b"
rollback() {
  echo "!! $1 - restoring farm-dash" >&2
  cp -a "$B/.farm-dash.bak-11b" "$B/farm-dash"
  systemctl restart farm-dash || true
  sleep 3
  systemctl is-active farm-dash || true
  journalctl -u farm-dash -n 30 --no-pager || true
  exit 1
}

echo "== install and restart"
install -o "$(stat -c %u "$B/farm-dash")" -g "$(stat -c %g "$B/farm-dash")" -m "$(stat -c %a "$B/farm-dash")" "$tmp/farm-dash" "$B/farm-dash"
systemctl restart farm-dash
sleep 3
systemctl is-active --quiet farm-dash || rollback "farm-dash is not active after the restart"
# the first request after a restart runs `gate-ctl status` once (all chains), so allow it time
curl -s --max-time 90 -o "$tmp/data.json" -w '%{http_code}' http://127.0.0.1:8090/data.json >"$tmp/code" || true
[[ $(cat "$tmp/code") == 200 ]] || rollback "data.json answered HTTP $(cat "$tmp/code")"
for path in / /brief.txt; do
  code=$(curl -s -o "$tmp/body" -w '%{http_code}' --max-time 90 "http://127.0.0.1:8090$path" || true)
  [[ $code == 200 ]] || { tail -c 600 "$tmp/body" >&2 || true; rollback "$path answered HTTP $code"; }
done
echo "farm-dash active; /, /data.json and /brief.txt answer HTTP 200"

echo "== what the new parts read on this server"
python3 -I -B - "$tmp/data.json" <<'PY' || rollback "data.json lacks the 11b keys"
import json, sys
d = json.load(open(sys.argv[1], encoding="utf-8"))
need = ("feed", "alchemy_month", "rpc_chains", "services", "gate_log", "live_loss", "prompts", "decisions", "lead_counts")
missing = [k for k in need if k not in d]
if missing:
    sys.exit(f"missing keys: {missing}")
m, f = d["alchemy_month"], d["feed"]
print("  alchemy this cycle:", m.get("error") or f"{m['cu']:,} CU since {m['since']}, on course for {m['projected_cu']} by {m['ends']}, lanes {m['lanes']}")
print("  feed:", f.get("error") or f"{f.get('cu_today')} of {f.get('daily_cu_budget')} CU today, /head on {f.get('heads_offered_on')}")
print("  services:", ", ".join(f"{s['unit']}={s['active']}" for s in d["services"]) or "NONE READ")
print("  live loss:", json.dumps(d["live_loss"]), "· stop at", d.get("max_live_loss_usd"))
print("  gate log rows:", len(d["gate_log"]), "· newest:", (d["gate_log"][0] if d["gate_log"] else None))
print("  prompts:", ", ".join(f"{p['instance']} {p['bytes']}" for p in d["prompts"]) or "NONE READ (farmgate cannot read /srv/farm/runners?)")
print("  decisions:", len(d["decisions"]), "· lead statuses:", d["lead_counts"])
print("  rpc by chain rows:", len(d["rpc_chains"]), "· pnl.json pending:", d.get("sweep_pending") or "none")
PY
python3 -I -B patch-11b.py check "$B/farm-dash" | grep -c "already applied" | sed 's/^/  hunks in place: /'
echo "Installed phase 11b. Paste everything from '== patch texts' down."
