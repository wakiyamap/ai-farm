#!/usr/bin/env bash
# Phase 6: local fork nodes (anvil) + Foundry, executor-contract execution model,
# gate deploys executors, relay paper lane prefers public nodes, dashboard fixes.
# Run from the unpacked directory: sudo ./install.sh   (safe to re-run)
set -euo pipefail
cd "$(dirname "$0")"
[[ $EUID -eq 0 ]] || { echo "run with sudo" >&2; exit 1; }

# --- Foundry, system-wide and root-owned (agents must not be able to swap the binaries) ---
if [[ ! -x /opt/foundry/bin/anvil ]]; then
  echo "Installing Foundry into /opt/foundry (via foundryup, then moved)"
  install -d -o root -g root -m 755 /opt/foundry /opt/foundry/bin
  tmp=$(mktemp -d)
  HOME="$tmp" bash -c 'curl -sSL https://foundry.paradigm.xyz | bash >/dev/null 2>&1 && "$HOME/.foundry/bin/foundryup" >/dev/null 2>&1'
  for b in anvil forge cast chisel; do
    [[ -x "$tmp/.foundry/bin/$b" ]] && install -o root -g root -m 755 "$tmp/.foundry/bin/$b" /opt/foundry/bin/
  done
  rm -rf "$tmp"
fi
/opt/foundry/bin/anvil --version
# verify the flags this unit relies on exist in this anvil build
for f in --fork-url --auto-impersonate --no-rate-limit --retries --timeout --compute-units-per-second --chain-id; do
  /opt/foundry/bin/anvil --help | grep -q -- "$f" || { echo "anvil lacks $f; adjust fork@.service" >&2; exit 1; }
done
ln -sfn /opt/foundry/bin/forge /usr/local/bin/forge
ln -sfn /opt/foundry/bin/cast /usr/local/bin/cast

# --- fork service user and units ---
id farmfork >/dev/null 2>&1 || useradd --system -s /usr/sbin/nologin -d /nonexistent -M farmfork
install -o root -g root -m 644 "etc/systemd/system/fork@.service" /etc/systemd/system/
install -o root -g root -m 644 etc/farm/fork.env etc/farm/fork-base.env etc/farm/fork-arbitrum.env etc/farm/fork-ethereum.env etc/farm/farm.nft /etc/farm/
install -o root -g root -m 755 opt/farm/bin/fork opt/farm/bin/gate-ctl opt/farm/bin/farm-signer opt/farm/bin/run-role opt/farm/bin/rpc-relay opt/farm/bin/farm-dash /opt/farm/bin/
install -o root -g root -m 644 etc/farm/relay.json /etc/farm/
install -o root -g root -m 644 etc/systemd/system/farm-dash.service /etc/systemd/system/
rm -f /etc/systemd/system/farm-dash.service.d/groups.conf
install -o root -g root -m 644 prompts/common.md /srv/farm/prompts/
install -o harness -g harness -m 644 prompts/roles/*.md /srv/farm/prompts/roles/

# FORK_URL_* for agent sessions
grep -q '^FORK_URL_BASE=' /etc/farm/farm.env || cat >> /etc/farm/farm.env <<'EOF'
FORK_URL_BASE=http://127.0.0.1:9001
FORK_URL_ARBITRUM=http://127.0.0.1:9002
FORK_URL_ETHEREUM=http://127.0.0.1:9003
EOF

# group-readable regardless of writer umask: inboxes, scratch, logs (meta reported inbox/meta unreadable)
WS=/srv/farm/ws
for d in inbox scratch logs claims; do
  setfacl -R -m g:farm:rwX -m d:g:farm:rwX -m m::rwx -m d:m::rwx "$WS/$d"
  chmod -R g+rwX "$WS/$d"
done

systemctl daemon-reload
systemctl restart farm-nft.service rpc-relay.service farm-signer.service farm-dash.service
systemctl enable --now fork@base.service fork@arbitrum.service fork@ethereum.service
echo "waiting for forks to sync their first block..."
for _ in $(seq 1 30); do
  ok=0
  for p in 9001 9002 9003; do
    curl -s -m 3 -X POST "http://127.0.0.1:$p" -H 'content-type: application/json' \
      -d '{"jsonrpc":"2.0","id":1,"method":"eth_blockNumber","params":[]}' | grep -q result && ok=$((ok+1))
  done
  [[ $ok -eq 3 ]] && break
  sleep 2
done
sudo -u earner /opt/farm/bin/fork status
while read -r inst _; do
  [[ -z "$inst" || "$inst" == \#* ]] && continue
  /opt/farm/bin/assemble-prompt "$inst"
done < /etc/farm/roles.conf
echo "Installed phase 6."
