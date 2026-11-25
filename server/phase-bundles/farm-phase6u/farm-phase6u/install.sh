#!/usr/bin/env bash
# Phase 6u: `fork deploy` detects creation code whose constructor arguments are missing (the cause of
# the 11-06 status-0 deploys) and takes --args <abi-encoded>; meta may run `date`.
# Run from the unpacked directory: sudo ./install.sh   (safe to re-run)
set -euo pipefail
cd "$(dirname "$0")"
[[ $EUID -eq 0 ]] || { echo "run with sudo" >&2; exit 1; }
python3 -I -m py_compile opt/farm/bin/fork
bash -n opt/farm/bin/run-role
install -o root -g root -m 755 opt/farm/bin/fork opt/farm/bin/run-role /opt/farm/bin/
REPRO=/srv/farm/ws/scratch/aave2-probe-bytecode.hex
if [[ -r $REPRO ]]; then
  echo "== repro without args (expect the constructor-arguments hint)"
  sudo -u harness /opt/farm/bin/fork deploy ethereum-review "$REPRO" || true
  echo "== repro with a dummy address argument (expect an address)"
  sudo -u harness /opt/farm/bin/fork deploy ethereum-review "$REPRO" \
    --args 0x00000000000000000000000000000000000000000000000000000000000a11ce || true
fi
echo "Installed phase 6u."
