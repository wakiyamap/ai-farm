import subprocess, json, sys

TOPICS = {
    "Deposit": "0x97e6c213c123075e233a6f2323f33d8319141b993ab05e9e2f7eb2eda08cb944",
    "Withdrawal": "0xfad3d7f9ed107ffa7fc8ce8baa521effc3650ec48a4d1dd36bdb9c4b91db1295",
    "TransactionExecuted": "0x14464fb67b1871a79e726fa7af525f8fff56e9e5649d511e47f3a357ae31d207",
    "ManagerFeeMinted": "0x755a8059d66d8d243bc9f6913f429a811f154599d0538bb0b6a2ac23f23d2ccd",
}
TOPIC_NAME = {v: k for k, v in TOPICS.items()}
FROM, TO = 97337536, 97637536  # ~7d at 2.0s blocks

vaults = [l.strip() for l in open("scratch/chamber_vaults.txt") if l.strip()]
print("vaults:", len(vaults))

counts = {k: 0 for k in TOPICS}
vault_evt = {}   # (vault, name) -> count
samples = []
errors = []

def rpc(method, params):
    for attempt in range(2):
        out = subprocess.run(["python3", "/srv/farm/ws/tools/rpc.py", "polygon", method, json.dumps(params)],
                             capture_output=True, text=True)
        try:
            d = json.loads(out.stdout)
            if "result" in d:
                return d["result"]
            err = d.get("error", {}).get("message", "?")
        except Exception:
            err = out.stdout[:150] + out.stderr[:100]
        if attempt == 1:
            errors.append(err)
    return None

for i in range(0, len(vaults), 32):
    chunk = vaults[i:i+32]
    res = rpc("eth_getLogs", [{"address": chunk, "topics": [list(TOPICS.values())],
                               "fromBlock": hex(FROM), "toBlock": hex(TO)}])
    if res is None:
        print(f"chunk {i//32} FAILED: {errors[-1] if errors else '?'}", flush=True)
        continue
    for lg in res:
        t = lg["topics"][0].lower()
        name = TOPIC_NAME.get(t, "?")
        counts[name] += 1
        key = (lg["address"].lower(), name)
        vault_evt[key] = vault_evt.get(key, 0) + 1
        if len(samples) < 60:
            samples.append({"vault": lg["address"], "evt": name, "block": int(lg["blockNumber"],16),
                            "tx": lg["transactionHash"], "data": lg["data"]})
    print(f"chunk {i//32}: {len(res)} logs", flush=True)

json.dump({"counts": counts, "vault_evt": {f"{k[0]}|{k[1]}": v for k, v in vault_evt.items()},
           "samples": samples, "errors": errors},
          open("scratch/chamber_scan_out.json", "w"))
print("TOTALS:", counts)
print("active vaults:", len(set(k[0] for k in vault_evt)))
