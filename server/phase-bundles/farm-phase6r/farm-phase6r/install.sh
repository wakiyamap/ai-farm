#!/usr/bin/env bash
# Phase 6r: L 20 -> 50 USD (human decision 2026-11-06), USD basis = signing-time price.
#   - gate.json max_loss_per_tx_usd = 50 (signer per-tx check, watchdog interval-drop stop)
#   - common.md L text; X (2000), daily loss (200) and Base gas wallet cap (18) unchanged
# Run from the unpacked directory: sudo ./install.sh   (safe to re-run)
set -euo pipefail
cd "$(dirname "$0")"
[[ $EUID -eq 0 ]] || { echo "run with sudo" >&2; exit 1; }
python3 - <<'PY'
import json
p = "/etc/farm/gate.json"
c = json.load(open(p))
c["max_loss_per_tx_usd"] = 50
json.dump(c, open(p, "w"), indent=2); open(p, "a").write("\n")
print({k: c[k] for k in ("max_capital_usd", "max_daily_loss_usd", "max_loss_per_tx_usd")}, "gas_wallet_cap_usd", c.get("gas_wallet_cap_usd"))
PY
install -o root -g root -m 644 prompts/common.md /srv/farm/prompts/
systemctl restart farm-signer.service farm-watchdog.service
sleep 2
systemctl is-active farm-signer.service farm-watchdog.service
while read -r inst _; do
  [[ -z "$inst" || "$inst" == \#* ]] && continue
  /opt/farm/bin/assemble-prompt "$inst"
done < /etc/farm/roles.conf
echo "Installed phase 6r."
