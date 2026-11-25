#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
[[ $EUID -eq 0 ]] || { echo "run with sudo" >&2; exit 1; }
install -o root -g root -m 755 opt/farm/bin/farm-dash /opt/farm/bin/
systemctl restart farm-dash.service
echo "Installed phase 6a (dashboard in JST)."
