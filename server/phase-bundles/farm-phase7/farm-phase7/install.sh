#!/usr/bin/env bash
# Phase 7: USDC principal for live bots.
#   - manifest `principal_usdc: <usd>` (part of capital_usd): gate sends it as USDC at promote,
#     `gate fund <id> <usd> --usdc` tops it up, sweep returns USDC first (with a gas top-up if needed)
#   - X and gate status include USDC balances; PnL includes the USDC delta
#   - signer: USDC token always callable; transfer/transferFrom only to allowed_contracts or the
#     intermediate wallet; USDC moved out counts toward the daily spend
#   - watchdog: native + USDC drop > L in one interval stops the bot
#   - common.md: X explains funding
# Run from the unpacked directory: sudo ./install.sh   (safe to re-run)
set -euo pipefail
cd "$(dirname "$0")"
[[ $EUID -eq 0 ]] || { echo "run with sudo" >&2; exit 1; }
python3 -I -m py_compile opt/farm/bin/gate-ctl opt/farm/bin/farm-signer opt/farm/bin/farm-watchdog
python3 - <<'PY'
import json
cfg = json.load(open("/etc/farm/gate.json"))
for c in ("ethereum", "base", "arbitrum"):
    assert cfg.get("usdc", {}).get(c), f"gate.json usdc.{c} missing"
print("gate.json usdc:", cfg["usdc"])
PY
install -o root -g root -m 755 opt/farm/bin/gate-ctl opt/farm/bin/farm-signer opt/farm/bin/farm-watchdog /opt/farm/bin/
install -o root -g root -m 644 prompts/common.md /srv/farm/prompts/
systemctl restart farm-signer.service farm-watchdog.service
sleep 2
systemctl is-active farm-signer.service farm-watchdog.service
sudo -u harness /opt/farm/bin/gate status | python3 -c 'import json,sys; d=json.load(sys.stdin); print("capital_usd", d["capital_usd"]); print("intermediate", json.dumps(d["intermediate_balances_usd"]))'
while read -r inst _; do
  [[ -z "$inst" || "$inst" == \#* ]] && continue
  /opt/farm/bin/assemble-prompt "$inst"
done < /etc/farm/roles.conf
echo "Installed phase 7."
