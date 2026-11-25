#!/usr/bin/env bash
# Install phase 2a: KB and wiki CLIs, where writes go only through validating
# writers running as farmdata; plus the phase 1 fixes.
# Run from the unpacked directory: sudo ./install.sh   (safe to re-run)
set -euo pipefail
cd "$(dirname "$0")"
[[ $EUID -eq 0 ]] || { echo "run with sudo" >&2; exit 1; }

apt-get install -y git >/dev/null

# Owner of the knowledge stores
id farmdata >/dev/null 2>&1 || \
  useradd --system -s /usr/sbin/nologin -d /var/lib/farmdata -m farmdata
install -d -o farmdata -g farmdata -m 750 /var/lib/farmdata

# Tools
install -o root -g root -m 755 \
  opt/farm/bin/kb opt/farm/bin/kb-write opt/farm/bin/wiki opt/farm/bin/wiki-write \
  opt/farm/bin/run-role /opt/farm/bin/
install -o root -g root -m 644 etc/farm/chains /etc/farm/

# sudoers: checked before it goes live
visudo -cf etc/sudoers.d/farm-data
install -o root -g root -m 440 etc/sudoers.d/farm-data /etc/sudoers.d/farm-data

# Knowledge stores: owned by farmdata, readable by everyone, writable by nobody else
WS=/srv/farm/ws
for d in kb wiki; do
  setfacl -bR "$WS/$d"
  chown -R farmdata:farm "$WS/$d"
  chmod 2755 "$WS/$d"
done
runuser -u farmdata -- /opt/farm/bin/kb-write --init
if [[ ! -d "$WS/wiki/.git" ]]; then
  runuser -u farmdata -- env HOME=/var/lib/farmdata git -C "$WS/wiki" init -q -b main
  runuser -u farmdata -- env HOME=/var/lib/farmdata git -C "$WS/wiki" \
    -c user.name=farm -c user.email=farm@farm commit -q --allow-empty -m "Start the wiki"
fi

# Prompts: common.md human-only, role files and TOOLS.md owned by harness.
# This overwrites role files, so re-running later would discard meta's edits.
install -o root -g root -m 644 prompts/common.md /srv/farm/prompts/
install -o harness -g harness -m 644 prompts/roles/*.md /srv/farm/prompts/roles/

# Build every instance's prompt now, so a first start never meets a missing
# bind-mount source (the earner-local failure in phase 1).
while read -r inst _; do
  [[ -z "$inst" || "$inst" == \#* ]] && continue
  /opt/farm/bin/assemble-prompt "$inst"
done < /etc/farm/roles.conf

echo "Installed phase 2a."
