#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
[[ $EUID -eq 0 ]] || { echo "run with sudo" >&2; exit 1; }
install -o root -g root -m 755 opt/farm/bin/gate-ctl /opt/farm/bin/
echo "Installed phase 4d."
