#!/usr/bin/env bash
# Phase 5: dashboard on 127.0.0.1:8090, published on the tailnet via Tailscale Serve (port 9443).
set -euo pipefail
cd "$(dirname "$0")"
[[ $EUID -eq 0 ]] || { echo "run with sudo" >&2; exit 1; }
install -o root -g root -m 755 opt/farm/bin/farm-dash /opt/farm/bin/
install -o root -g root -m 644 etc/systemd/system/farm-dash.service /etc/systemd/system/
systemctl daemon-reload
systemctl enable --now farm-dash.service
sleep 2
curl -s -o /dev/null -w 'dashboard http %{http_code}\n' http://127.0.0.1:8090/
# tailnet only (no Funnel), alongside dsh (443) and ComfyUI (8443)
tailscale serve --bg --https=9443 http://127.0.0.1:8090 >/dev/null && echo "tailscale serve: https://$(tailscale status --json | python3 -c 'import json,sys;print(json.load(sys.stdin)["Self"]["DNSName"].rstrip("."))'):9443/"
echo "Installed phase 5."
