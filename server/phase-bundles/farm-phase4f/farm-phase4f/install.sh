#!/usr/bin/env bash
# Phase 4f: lessons from earner session 2 (cut off mid-build) and the reviewer's KB note.
#  - earner records findings BEFORE building; unfinished bots are offered as the next target
#  - attempts.outcome accepts reviewer / operator decisions
set -euo pipefail
cd "$(dirname "$0")"
[[ $EUID -eq 0 ]] || { echo "run with sudo" >&2; exit 1; }
install -o root -g root -m 755 opt/farm/bin/kb-write /opt/farm/bin/
install -o root -g root -m 755 opt/farm/context/earner /opt/farm/context/
install -o harness -g harness -m 644 prompts/roles/earner.md /srv/farm/prompts/roles/
/opt/farm/bin/assemble-prompt earner-local
echo "Installed phase 4f."
