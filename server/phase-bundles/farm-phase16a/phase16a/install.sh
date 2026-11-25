#!/usr/bin/env bash
# Phase 16a: Stellar, read only.
#  - rpc-relay: relay.json "nonevm_chains" (stellar via Alchemy), Stellar RPC read methods only,
#    lanes research / scout / paper only, never a send (send socket included)
#  - scout-enum: DefiLlama "Stellar" protocols, queued at tier 2
#  - /opt/farm/context/scout: Stellar steps; roles/scout.md: a Stellar section
#  - two targeted scout candidates (Blend interest auctions, BIM harvest) at the head of the queue
# Nothing signs or sends on Stellar. gate, signer, watchdog, feed, farmchains.py: unchanged.
# JSON answers are parsed from stdin: getLatestLedger carries ledger XDR larger than one argv string may be.
# Run from the unpacked directory: sudo ./install.sh   (safe to re-run)
set -euo pipefail
trap 'echo "install.sh failed at line $LINENO: $BASH_COMMAND" >&2' ERR
cd "$(dirname "$0")"
[[ $EUID -eq 0 ]] || { echo "run with sudo" >&2; exit 1; }
B=/opt/farm/bin; C=/opt/farm/context; R=/srv/farm/prompts/roles; CFG=/etc/farm/relay.json
KEY=/etc/farm/alchemy.key; Q=/srv/farm/ws/scout
sha() { sha256sum "$1" | cut -d' ' -f1; }
state() {  # file, old, new [, other accepted] -> prints old / new / try1, exits if none
  local h; h=$(sha "$1")
  if [[ $h == "$3" ]]; then echo new
  elif [[ $h == "$2" ]]; then echo old
  elif [[ -n ${4:-} && $h == "$4" ]]; then echo try1
  else echo "  $1 changed since it was sent (sha256 $h). Nothing was changed." >&2; exit 1; fi
}
OLD_RELAY=aeb3fb3c1d4290d1a8a05ab50c58679a60741e9b4d8df56754c150c17e6130e4; NEW_RELAY=d3241a0787429489aa65f3b649d8d354a5cf1d8a4dca346b41127c1fb8274c68
TRY1_RELAY=94620b08d304c42091b217f1cc875be1d6e35020a2b3908ba1c386b391141919   # first try (21:06), rolled back
OLD_ENUM=92adcd937ee09a2bdc04bab6639e81e6ac7acc66eb02873e3b4ee91f4e8ea487;  NEW_ENUM=a8371c7030b8a84948f661c717f2470d971a2d166df1173b0919acf57c7d6d51
OLD_CTX=debc1442b561f21150ec76a1e582128ede446826fdcc6742f892337980509994;   NEW_CTX=fca5c78fe6acae7f79fd31c6bb7642b2e36e607659ad5b14318bcc65ffd31778
OLD_MD=99da980489a299291176373adc8e1f67af212fac0224b343bd2c2ac1dfbc84b9;    NEW_MD=38246bee5d6c501571909aeb9aa182a9baefb3fb1df388fdc51dabbada8188d1

echo "== checks (nothing is changed yet)"
s_relay=$(state $B/rpc-relay $OLD_RELAY $NEW_RELAY $TRY1_RELAY); echo "  rpc-relay: $s_relay"
s_enum=$(state $B/scout-enum $OLD_ENUM $NEW_ENUM);   echo "  scout-enum: $s_enum"
s_ctx=$(state $C/scout $OLD_CTX $NEW_CTX);           echo "  context/scout: $s_ctx"
s_md=$(state $R/scout.md $OLD_MD $NEW_MD);           echo "  roles/scout.md: $s_md"
[[ -s $KEY ]] || { echo "  $KEY missing. Nothing was changed." >&2; exit 1; }

echo "== Alchemy reads Stellar mainnet? (the key is passed on stdin, never printed)"
resp=$(printf 'url = "https://stellar-mainnet.g.alchemy.com/v2/%s"\n' "$(tr -d '[:space:]' < $KEY)" |
       curl -s -m 20 -K - -X POST -H 'Content-Type: application/json' \
            -d '{"jsonrpc":"2.0","id":1,"method":"getLatestLedger"}' || true)
if ! python3 -c 'import json,sys; r=json.load(sys.stdin); s=r["result"]["sequence"]; print("  latest ledger", s)' <<<"$resp"; then
  echo "  Alchemy answered: ${resp:0:300}" >&2
  echo "  No ledger sequence in the answer. If it is an auth error, enable Stellar Mainnet for the app in the Alchemy dashboard and re-run. Nothing was changed." >&2
  exit 1
fi

echo "== patch and test on copies"
W=$(mktemp -d); trap 'rm -rf "$W"' EXIT
# the original of each file: the .bak-16a left by an earlier run if there is one, else the file itself
orig() { if [[ -e $2 ]]; then cp -p "$2" "$3"; else cp -p "$1" "$3"; fi; }
orig $B/rpc-relay $B/.rpc-relay.bak-16a "$W/rpc-relay"
orig $B/scout-enum $B/.scout-enum.bak-16a "$W/scout-enum"
orig $C/scout $C/.scout.bak-16a "$W/context-scout"
orig $R/scout.md $R/.scout.md.bak-16a "$W/scout.md"
for p in "rpc-relay $OLD_RELAY" "scout-enum $OLD_ENUM" "context-scout $OLD_CTX" "scout.md $OLD_MD"; do
  set -- $p; [[ $(sha "$W/$1") == "$2" ]] || { echo "  $1: the original is not the version that was sent. Nothing was changed." >&2; exit 1; }
done
python3 -B patch-16a.py "$W/rpc-relay" "$W/scout-enum" "$W/context-scout" "$W/scout.md"
for p in "rpc-relay $NEW_RELAY" "scout-enum $NEW_ENUM" "context-scout $NEW_CTX" "scout.md $NEW_MD"; do
  set -- $p; [[ $(sha "$W/$1") == "$2" ]] || { echo "  $1: patched sha256 is not the expected one. Nothing was changed." >&2; exit 1; }
done
python3 -B test-16a.py "$W/rpc-relay" "$W/scout-enum" "$W/context-scout" "$W/scout.md" candidates

echo "== install"
for f in rpc-relay scout-enum; do [[ -e $B/.$f.bak-16a ]] || cp -p $B/$f $B/.$f.bak-16a; done
[[ -e $C/.scout.bak-16a ]] || cp -p $C/scout $C/.scout.bak-16a
[[ -e $R/.scout.md.bak-16a ]] || cp -p $R/scout.md $R/.scout.md.bak-16a
[[ -e $CFG.bak-16a ]] || cp -p $CFG $CFG.bak-16a
python3 - "$CFG" <<'PY'
import json, os, sys
p = sys.argv[1]
c = json.load(open(p, encoding="utf-8"))
c.setdefault("nonevm_chains", {})["stellar"] = {
    "alchemy": "stellar-mainnet", "public": [], "kind": "stellar",
    "lanes": ["research", "scout", "paper"],
    "note": "16a: read only. Stellar RPC methods only, never a send. Public nodes not listed yet."}
st = os.stat(p)
tmp = p + ".tmp16a"
with open(tmp, "w", encoding="utf-8") as f:
    json.dump(c, f, indent=2)
    f.write("\n")
os.chown(tmp, st.st_uid, st.st_gid); os.chmod(tmp, st.st_mode & 0o7777); os.replace(tmp, p)
print("  relay.json: nonevm_chains.stellar set")
PY
install -o root -g root -m 755 "$W/rpc-relay" $B/rpc-relay

rollback() {
  echo "  rolling back rpc-relay, relay.json and the scout files" >&2
  cp -p $B/.rpc-relay.bak-16a $B/rpc-relay; cp -p $CFG.bak-16a $CFG
  cp -p $B/.scout-enum.bak-16a $B/scout-enum; cp -p $C/.scout.bak-16a $C/scout; cp -p $R/.scout.md.bak-16a $R/scout.md
  systemctl restart rpc-relay || true
  exit 1
}
echo "== restart rpc-relay (live bots cannot read for a few seconds; fork@ restarts with it)"
systemctl restart rpc-relay
sleep 15
systemctl is-active --quiet rpc-relay || { journalctl -u rpc-relay -n 20 --no-pager >&2; rollback; }
post() { curl -s -m 20 -X POST "http://127.0.0.1:8545/$1?lane=research" -H 'Content-Type: application/json' -d "$2"; }
r1=$(post stellar '{"jsonrpc":"2.0","id":1,"method":"getLatestLedger"}')
python3 -c 'import json,sys; print("  relay stellar getLatestLedger:", json.load(sys.stdin)["result"]["sequence"])' <<<"$r1" ||
  { echo "  relay answered: ${r1:0:300}" >&2; rollback; }
r2=$(post base '{"jsonrpc":"2.0","id":1,"method":"eth_blockNumber","params":[]}')
python3 -c 'import json,sys; print("  relay base eth_blockNumber:", int(json.load(sys.stdin)["result"], 16))' <<<"$r2" ||
  { echo "  relay answered: ${r2:0:300}" >&2; rollback; }
r3=$(post stellar '{"jsonrpc":"2.0","id":1,"method":"sendTransaction","params":{"transaction":"AAAA"}}')
python3 -c 'import json,sys; e=json.load(sys.stdin)["error"]; print("  relay stellar sendTransaction refused:", e["code"])' <<<"$r3" ||
  { echo "  sendTransaction was not refused: ${r3:0:300}" >&2; rollback; }
r4=$(curl -s -m 10 http://127.0.0.1:8545/health)
python3 -c 'import json,sys; h=json.load(sys.stdin); assert "stellar" not in h["chains"]; print("  /health chains:", len(h["chains"]), "EVM, nonevm:", h["nonevm_chains"])' <<<"$r4" || rollback
failed=$(systemctl list-units 'fork@*' --state=failed --no-legend | wc -l)
echo "  fork@ failed units: $failed"

echo "== scout files (only after the relay serves stellar)"
install -o root -g root -m 755 "$W/scout-enum" $B/scout-enum
install -o root -g root -m 755 "$W/context-scout" $C/scout
install -o harness -g harness -m 644 "$W/scout.md" $R/scout.md
echo "== scout prompts and queue"
for n in 1 2 3 4; do /opt/farm/bin/assemble-prompt "scout-$n"; done
echo "  scout prompt: $(stat -c %s /srv/farm/runners/scout-1/prompt.md) bytes"
for f in candidates/*.json; do
  id=$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["id"])' "$f")
  if ls $Q/queue $Q/doing $Q/done 2>/dev/null | grep -c -- "$id" >/dev/null; then echo "  $id: already queued or done"
  else install -o harness -g farm -m 664 "$f" $Q/queue/; echo "  queued $(basename "$f")"; fi
done
systemctl start farm-scout-enum.service || echo "  farm-scout-enum did not run now; the timer will" >&2
echo "  stellar candidates in queue: $(ls $Q/queue | grep -c stellar || true)"

echo "== sha256 (expected / installed)"
for p in "$B/rpc-relay $NEW_RELAY" "$B/scout-enum $NEW_ENUM" "$C/scout $NEW_CTX" "$R/scout.md $NEW_MD"; do
  set -- $p; echo "  $1"; echo "    $2"; echo "    $(sha "$1")"
done
echo "Installed phase 16a. Undo: copy the .bak-16a files back (rpc-relay, scout-enum, context/scout, scout.md, relay.json) and restart rpc-relay."
