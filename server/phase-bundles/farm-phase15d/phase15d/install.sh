#!/usr/bin/env bash
# Phase 15d (2026-11-18): farm.nft lets earner and farmbot reach 127.0.0.1:29486 (farm-hermes, 15c),
# so a bot that needs Pyth update data can run on paper and live. Three text patches; nothing else
# changes. If nft refuses the rules or a check fails, the previous farm.nft is restored.
# Run from the unpacked directory: sudo ./install.sh   (safe to re-run)
set -euo pipefail
trap 'echo "install.sh failed at line $LINENO: $BASH_COMMAND" >&2' ERR
cd "$(dirname "$0")"
[[ $EUID -eq 0 ]] || { echo "run with sudo" >&2; exit 1; }
NFT=/etc/farm/farm.nft
OLD=acc2c1df146dbf4a16a9743791641c2b64175e56c7d13cef1b5a2d74d3e15310   # after 12f
NEW=7ed9a8b32324c56f977f945be85e3151459e312b0632c63949e5b29804dff559
sha() { sha256sum "$1" | cut -d' ' -f1; }
tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT
reach() { runuser -u "$1" -- python3 -I -c "import socket; socket.create_connection(('127.0.0.1', $2), 3)" 2>/dev/null; }

echo "== checks (nothing is changed yet)"
h=$(sha $NFT)
if [[ $h == "$NEW" ]]; then
  echo "  farm.nft is already the 15d version"
  cp $NFT "$tmp/farm.nft"
elif [[ $h == "$OLD" ]]; then
  echo "  farm.nft: as expected (12f)"
  python3 -I -B patch-15d.py check $NFT
  python3 -I -B patch-15d.py apply $NFT "$tmp/farm.nft"
  [[ $(sha "$tmp/farm.nft") == "$NEW" ]] || { echo "  the patched farm.nft does not have the expected sha256; nothing was changed" >&2; exit 1; }
else
  echo "  farm.nft changed since the bundle was built. Nothing was changed." >&2
  echo "    expected $OLD" >&2
  echo "    got      $h" >&2
  exit 1
fi
nft -c -f "$tmp/farm.nft"
echo "  syntax ok"

back() {
  echo "!! $1 - restoring farm.nft" >&2
  [[ -f $NFT.bak-15d ]] && { cat "$NFT.bak-15d" > $NFT; nft -f $NFT || true; }
  exit 1
}
echo "== install"
if [[ $h != "$NEW" ]]; then
  [[ -e $NFT.bak-15d ]] || cp -a $NFT $NFT.bak-15d
  cat "$tmp/farm.nft" > $NFT                  # keeps owner and mode
  nft -f $NFT || back "nft refused the new rules"
fi
echo "== reach"
for u in earner farmbot harness; do
  reach $u 29486 && echo "  $u -> 29486 (farm-hermes): reaches" || back "$u cannot reach farm-hermes"
done
reach farmbot 29485 && back "farmbot reaches 29485 (relayapi), which it must not" || echo "  farmbot -> 29485 (relayapi): refused, as before"
reach farmbot 9013 && back "farmbot reaches 9013 (reviewer fork), which it must not" || echo "  farmbot -> 9013 (reviewer fork): refused, as before"
reach farmbot 8545 && echo "  farmbot -> 8545 (relay): reaches, as before" || back "farmbot lost the relay"
echo "== sha256 (expected / installed)"
echo "  farm.nft $NEW"
echo "           $(sha $NFT)"
echo "Installed phase 15d. To undo: sudo sh -c 'cat $NFT.bak-15d > $NFT && nft -f $NFT'"
