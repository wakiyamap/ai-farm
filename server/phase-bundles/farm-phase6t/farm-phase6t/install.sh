#!/usr/bin/env bash
# Phase 6t: `fork deploy` reads forge artifacts, rejects malformed hex, warns on runtime-only code,
# and on a revert prints gasUsed, the eth_call error, callTracer error and the last opcodes;
# new `fork info <chain>` (anvil version / hardfork). inbox/human/2026-11-06-meta-fork-deploy-bash.md §1.
# Run from the unpacked directory: sudo ./install.sh   (safe to re-run)
set -euo pipefail
cd "$(dirname "$0")"
[[ $EUID -eq 0 ]] || { echo "run with sudo" >&2; exit 1; }
python3 -I -m py_compile opt/farm/bin/fork
install -o root -g root -m 755 opt/farm/bin/fork /opt/farm/bin/
echo "== anvil"; /opt/foundry/bin/anvil --version || true
for c in base arbitrum ethereum ethereum-review; do sudo -u harness /opt/farm/bin/fork info "$c" || true; done
REPRO=/srv/farm/ws/scratch/aave2-probe-bytecode.hex
if [[ -r $REPRO ]]; then
  echo "== reproducing meta's failing deploy on the reviewer fork (ethereum-review, no effect on earner forks)"
  sudo -u harness /opt/farm/bin/fork deploy ethereum-review "$REPRO" || true
fi
echo "Installed phase 6t. Paste everything from '== anvil' down."
