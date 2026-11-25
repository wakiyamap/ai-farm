import subprocess, json, sys

RPC = ["python3", "/srv/farm/ws/tools/rpc.py", "arbitrum"]
VAULTS = [
 "0xDDD4f2A962BB9e8394C8E748d8Fd343cA870682C",
 "0x2E6c54DCf1C14A2E36C3eD63bA690Bd3867c4961",
 "0x01F90a7b1C749F4a0B7D115120dedA0e2343381d",
 "0x4fE17dEFc597cC3bD6fBe16135d8Ac42D421907e",
 "0x3ca8F12D7B376E9Ef338d1C432CA1b51DD319009",
 "0x263b7B6499874E6E2758cD1aBe288Ea83b55da11",
 "0x0792dcAa8e4ce37Cb5A32C5fbe2610872F9A29CA",
 "0x54602E5cBa09e01EeE9B2050F1F4f0Dc902CeE34",
 "0xF37Fe9396Bb95f7823A29090c939847f1817bC8a",
]

def call(to, data):
    r = subprocess.run(RPC + ["eth_call", json.dumps([{"to": to, "data": data}, "latest"])],
                       capture_output=True, text=True, timeout=60)
    if r.returncode != 0:
        return ("ERR", r.stdout.strip()[:120] + r.stderr.strip()[:120])
    try:
        return ("OK", json.loads(r.stdout).get("result"))
    except Exception as e:
        return ("ERR", r.stdout[:120])

def sel(sig):
    r = subprocess.run(["cast", "sig", sig], capture_output=True, text=True)
    return r.stdout.strip() if r.returncode == 0 else None

import functools
sels = {}
for sig in ["getCode", "totalBalance()", "symbol()", "vaultParams()", "keeper()", "currentRound()", "asset()"]:
    if sig != "getCode":
        sels[sig] = sel(sig)
print("selectors:", sels)

for v in VAULTS:
    code = call(v, "0x")
    has = code[1] not in (None, "0x")
    out = {"v": v, "code": has}
    for sig in ["symbol()", "totalBalance()", "currentRound()"]:
        st, res = call(v, sels[sig])
        out[sig] = res if st == "OK" else "ERR"
    print(json.dumps(out))
