#!/usr/bin/env bash
# Phase 4b (take 2): relay send socket in its own runtime dir /run/farm-relay.
set -euo pipefail
cd "$(dirname "$0")"
[[ $EUID -eq 0 ]] || { echo "run with sudo" >&2; exit 1; }
install -o root -g root -m 755 opt/farm/bin/rpc-relay opt/farm/bin/gate-ctl opt/farm/bin/farm-signer /opt/farm/bin/
install -o root -g root -m 644 etc/systemd/system/rpc-relay.service /etc/systemd/system/
systemctl daemon-reload
systemctl restart rpc-relay.service
sleep 1
systemctl restart farm-signer.service farm-watchdog.service
journalctl -u rpc-relay -n 3 --no-pager
ls -l /run/farm-relay/
if [[ -d /srv/farm/ws/bots/live/selfping ]]; then
  /opt/farm/bin/gate-root archive selfping >/dev/null && echo "rolled back selfping"
  python3 - <<'PY'
import json
p="/var/lib/farmgate/accounts.json"
try:
    a=json.load(open(p)); a["bots"].pop("selfping", None); json.dump(a, open(p,"w"), indent=1)
except FileNotFoundError:
    pass
PY
  rm -rf /srv/farm/ws/bots/archive/selfping*
fi
echo "Installed phase 4b."
