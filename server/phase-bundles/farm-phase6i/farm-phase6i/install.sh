#!/usr/bin/env bash
# Phase 6i: decision (a) on Base fee bounds (inbox/human/2026-11-04-meta-base-l1fee-and-perms.md §1).
#   - gate.json: "gas_wallet_cap_usd": {"base": 18}
#   - gate-ctl: promote/fund never push a capped chain's native balance above the cap; status shows it
#   - farm-signer: refuses to sign on a capped chain while the bot's native balance is above the cap
#   - common.md: L explains the OP Stack rule
# Run from the unpacked directory: sudo ./install.sh   (safe to re-run)
set -euo pipefail
cd "$(dirname "$0")"
[[ $EUID -eq 0 ]] || { echo "run with sudo" >&2; exit 1; }
python3 -I -m py_compile opt/farm/bin/gate-ctl opt/farm/bin/farm-signer
python3 - <<'PY'
import json
p = "/etc/farm/gate.json"
cfg = json.load(open(p))
cfg.setdefault("gas_wallet_cap_usd", {})
cfg["gas_wallet_cap_usd"].setdefault("base", 18)
json.dump(cfg, open(p, "w"), indent=2); open(p, "a").write("\n")
print("gate.json gas_wallet_cap_usd:", cfg["gas_wallet_cap_usd"])
PY
install -o root -g root -m 755 opt/farm/bin/gate-ctl opt/farm/bin/farm-signer /opt/farm/bin/
install -o root -g root -m 644 prompts/common.md /srv/farm/prompts/
systemctl restart farm-signer.service
sleep 2
systemctl is-active farm-signer.service
sudo -u harness /opt/farm/bin/gate status | grep -A2 gas_wallet_cap_usd
while read -r inst _; do
  [[ -z "$inst" || "$inst" == \#* ]] && continue
  /opt/farm/bin/assemble-prompt "$inst"
done < /etc/farm/roles.conf
echo "Installed phase 6i."
