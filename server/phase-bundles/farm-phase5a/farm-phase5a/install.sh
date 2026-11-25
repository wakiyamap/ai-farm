#!/usr/bin/env bash
# Phase 5a: reviewer-readable bot files (default ACL), correct sweep PnL, dashboard reads ops.db.
set -euo pipefail
cd "$(dirname "$0")"
[[ $EUID -eq 0 ]] || { echo "run with sudo" >&2; exit 1; }
install -o root -g root -m 755 opt/farm/bin/gate-ctl opt/farm/bin/farm-dash /opt/farm/bin/
install -o root -g root -m 644 etc/systemd/system/farm-dash.service /etc/systemd/system/

# bots/paper: every new file readable by group farm regardless of the writer's umask or mode
WS=/srv/farm/ws
setfacl -R -m g:farm:rwX -m d:g:farm:rwX "$WS/bots/paper"
setfacl -R -m m::rwx -m d:m::rwx "$WS/bots/paper"
chmod -R g+rX "$WS/bots/paper"
# ops.db readable by the dashboard (farmgate)
chmod o+rx /var/lib/farm; chmod o+r /var/lib/farm/ops.db

# reset the wrong +5.0 from the double sweep of the test bot
python3 - <<'PY'
import json
p="/var/lib/farmgate/pnl.json"
try:
    d=json.load(open(p)); d["realized_usd"].pop("selfping", None); json.dump(d, open(p,"w"))
except (FileNotFoundError, KeyError, ValueError):
    pass
PY
chown farmgate:farmgate /var/lib/farmgate/pnl.json 2>/dev/null || true
rm -f "$WS/inbox/meta/3851d81-review-permissions.md" "$WS/inbox/meta/earner-file-permissions-pitfall.md"

systemctl daemon-reload
systemctl restart farm-dash.service
sleep 2
curl -s http://127.0.0.1:8090/data.json | python3 -c "import json,sys; d=json.load(sys.stdin); print('runs:', d['runs'][:1]); print('pnl today:', d['pnl'][-1])"
echo "Installed phase 5a."
