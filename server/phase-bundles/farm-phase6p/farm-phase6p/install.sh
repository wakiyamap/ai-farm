#!/usr/bin/env bash
# Phase 6p: earner web_search via You.com instead of the DeepSeek API (no key needed, 100/day).
#   - installs @youdotcom-oss/dsh-plugin into the earner's headless dsh profile
#   - adds the `web` row (searchProvider: youcom) to /etc/farm/earner-headless.patch.yml
#   - keeps the on-disk copy under the bind mount in sync so manual `dsh headless` runs work
# Run from the unpacked directory: sudo ./install.sh   (safe to re-run)
set -euo pipefail
cd "$(dirname "$0")"
[[ $EUID -eq 0 ]] || { echo "run with sudo" >&2; exit 1; }
DSH=/opt/farm/dsh/node_modules/.bin/dsh
as_earner() { (cd /tmp && sudo -u earner env HOME=/home/earner PATH=/opt/node/bin:/usr/bin:/bin "$@"); }

# 1. plugin
as_earner "$DSH" plugin --profile headless add @youdotcom-oss/dsh-plugin

# 2. patch row (idempotent)
P=/etc/farm/earner-headless.patch.yml
if ! grep -q 'searchProvider: youcom' "$P"; then
  cp -a "$P" "$P.bak-$(date +%Y%m%d%H%M)"
  { echo; cat etc/farm/web-youcom.patch.part; } >> "$P"
fi
install -o root -g root -m 644 etc/farm/earner-headless.patch.yml.in /etc/farm/earner-headless.patch.yml.in

# 3. on-disk copy under the bind mount (the service mounts $P over it at start)
install -o earner -g earner -m 600 "$P" /home/earner/.dsh/profiles/headless/cordis.patch.yml

# 4. verify the composed config
cfg=$(as_earner "$DSH" headless --dump-config 2>&1)
echo "$cfg" | grep -n -A4 -E '^- id: web$'
echo "$cfg" | grep -q 'searchProvider: youcom' && echo "web_search provider: youcom" || { echo "youcom not active in composed config" >&2; exit 1; }
echo "$cfg" | grep -q 'youcom' && echo "$cfg" | grep -n -B1 -A6 'youcom-skills' | head -12
echo
echo "limit-like settings in the composed config (for reference):"
echo "$cfg" | grep -n -i -E 'turn|maxSteps|iteration|budget|maxTokens|contextWindow|timeout' | head -20
echo "Installed phase 6p. The next earner session uses You.com for web_search."
