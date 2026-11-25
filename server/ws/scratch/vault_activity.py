#!/usr/bin/env python3
import json, subprocess, sys, collections

FROM_HEX, TO_HEX = sys.argv[1], sys.argv[2]
pairs = [l.split() for l in open('scratch/pairs.tsv') if l.strip()]
vault_of_token = {}
for tok, vault in pairs:
    vault_of_token.setdefault(tok, set()).add(vault.lower())

TOPIC = "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef"
batches = [pairs[i:i+32] for i in range(0, len(pairs), 32)]

seen = set()
all_logs = []
for b in batches:
    tokens = sorted({t.lower() for t, v in b})
    vaults = sorted({v.lower() for t, v in b})
    params = [{"fromBlock": FROM_HEX, "toBlock": TO_HEX, "address": tokens,
               "topics": [TOPIC, ["0x" + v[2:].rjust(64, "0") for v in vaults]]}]
    r = subprocess.run(["python3", "/srv/farm/ws/tools/rpc.py", "base", "eth_getLogs",
                        json.dumps(params)], capture_output=True, text=True)
    if r.returncode != 0:
        print("QUERY FAIL:", r.stdout[:120], r.stderr[:120]); continue
    try:
        logs = json.loads(r.stdout)["result"]
    except Exception as e:
        print("PARSE FAIL:", r.stdout[:120]); continue
    for lg in logs:
        key = (lg.get("blockNumber"), lg.get("transactionHash"), lg.get("logIndex"))
        if key in seen: continue
        seen.add(key)
        all_logs.append(lg)

exact = 0
byvault = collections.Counter()
for lg in all_logs:
    addr = lg["address"].lower()
    frm = lg["topics"][1][-40:].lower() if len(lg["topics"]) > 1 else None
    if frm in vault_of_token.get(addr, set()):
        exact += 1
        byvault[frm] += 1
print(f"range {FROM_HEX}..{TO_HEX}: raw logs {len(all_logs)}, exact (token,vault) transfers {exact}")
for v, c in byvault.most_common(20):
    print(f"  vault {v}: {c} transfers out")
json.dump(all_logs, open(f'scratch/vaultlogs_{FROM_HEX[2:]}_{TO_HEX[2:]}.json', 'w'))
