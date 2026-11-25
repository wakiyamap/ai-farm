#!/usr/bin/env bash
# Install phase 1 of the farm: agent launcher, run recording, port rules.
# Run from the unpacked directory: sudo ./install.sh
# Safe to re-run; it never overwrites /etc/farm/farm.env or the earner patch file.
set -euo pipefail
cd "$(dirname "$0")"
[[ $EUID -eq 0 ]] || { echo "run with sudo" >&2; exit 1; }

apt-get install -y nftables sqlite3 >/dev/null

# Scripts
install -d -o root -g root -m 755 /opt/farm/bin /opt/farm/context
install -o root -g root -m 755 \
  opt/farm/bin/run-role opt/farm/bin/assemble-prompt opt/farm/bin/record-run /opt/farm/bin/

# Config
install -d -o root -g root -m 755 /etc/farm
install -o root -g root -m 644 \
  etc/farm/roles.conf etc/farm/farm.nft etc/farm/smoke.example /etc/farm/
for f in farm.env earner-headless.patch.yml; do
  [[ -e "/etc/farm/$f" ]] || install -o root -g root -m 644 "etc/farm/$f" /etc/farm/
done

# systemd units (timers are installed but not enabled yet)
install -o root -g root -m 644 \
  etc/systemd/system/agent@.service \
  etc/systemd/system/farm-nft.service \
  etc/systemd/system/farm-*.timer /etc/systemd/system/
install -d -o root -g root -m 755 "/etc/systemd/system/agent@earner-local.service.d"
install -o root -g root -m 644 \
  "etc/systemd/system/agent@earner-local.service.d/earner.conf" \
  "/etc/systemd/system/agent@earner-local.service.d/"

# One root-owned working directory per instance
while read -r inst _; do
  [[ -z "$inst" || "$inst" == \#* ]] && continue
  install -d -o root -g root -m 755 "/srv/farm/runners/$inst"
done < /etc/farm/roles.conf

# Agent config files at the workspace root: root-owned and empty, so no agent
# can plant instructions, hooks or MCP servers that another agent's CLI loads.
# setfacl -b drops the workspace's default ACL, which would let group farm write.
WS=/srv/farm/ws
for d in .claude .codex .dsh; do
  install -d -o root -g root -m 755 "$WS/$d"
  setfacl -b "$WS/$d"
done
for f in AGENTS.md CLAUDE.md CLAUDE.local.md; do
  install -o root -g root -m 644 /dev/null "$WS/$f"
  setfacl -b "$WS/$f"
done
echo '{"mcpServers":{}}' > "$WS/.mcp.json"
chown root:root "$WS/.mcp.json"
chmod 644 "$WS/.mcp.json"
setfacl -b "$WS/.mcp.json"

# Targets for the earner's read-only bind mounts
runuser -u earner -- install -d -m 700 \
  /home/earner/.dsh /home/earner/.dsh/profiles /home/earner/.dsh/profiles/headless
runuser -u earner -- touch \
  /home/earner/.dsh/AGENTS.md /home/earner/.dsh/profiles/headless/cordis.patch.yml

systemctl daemon-reload
systemctl enable --now farm-nft.service

for p in /opt/node/bin/node /opt/farm/dsh/node_modules/.bin/dsh; do
  [[ -x "$p" ]] || echo "WARNING: $p not found (needed by the earner)"
done
echo "Installed. Check the paths in /etc/farm/farm.env before the smoke test."
