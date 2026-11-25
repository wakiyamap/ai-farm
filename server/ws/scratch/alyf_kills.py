import subprocess, json, sys

RPC = ["python3", "/srv/farm/ws/tools/rpc.py", "bsc"]
LATEST = 134609137
FROM = LATEST - 201600  # ~7d @ 3s blocks
KILL = "0x1f645d83d1940a1cb59e44eda10b9611d98402a975eef915b67160f46ee349e3"
RMD  = "0xc141cd58846e97354928242dcc7ddd92a6a0ecf03bdb5d3a411d260b9abc3272"
VAULTS = ["0xd7D069493685A581d27824Fc46EdA46B7EfC0063","0x7C9e73d4C71dae564d41F78d56439bB4ba87592f","0xbfF4a34A4644a113E8200D7F1D79b3555f723AfE","0xf1bE8ecC990cBcb90e166b71E368299f0116d421","0x158Da805682BdC8ee32d52833aD41E74bb951E59","0x08FC9Ba2cAc74742177e0afC3dC8Aed6961c24e7","0x3282d2a151ca00BfE7ed17Aa16E42880248CD3Cd","0x800933D685E7Dc753758cEb77C8bd34aBF1E26d7","0xfF693450dDa65df7DD6F45B4472655A986b147Eb"]

kills, rmds = [], []
chunk = 5000
start = FROM
calls = 0
b = start
while b <= LATEST:
    e = min(b + chunk - 1, LATEST)
    params = [{"fromBlock": hex(b), "toBlock": hex(e), "address": VAULTS, "topics": [[KILL, RMD]]}]
    r = subprocess.run(RPC + ["eth_getLogs", json.dumps(params)], capture_output=True, text=True)
    calls += 1
    try:
        logs = json.loads(r.stdout)["result"]
    except Exception:
        print("ERR", b, r.stdout[:200], r.stderr[:200]); b = e + 1; continue
    for lg in logs:
        (kills if lg["topics"][0].lower() == KILL else rmds).append(lg)
    b = e + 1
print(f"calls={calls} kills={len(kills)} removedebt={len(rmds)}")
for lg in kills:
    data = lg["data"][2:]
    word = lambda i: int(data[64*i:64*(i+1)], 16)
    print("KILL", lg["blockNumber"], lg["transactionHash"], "vault", lg["address"][:10],
          "killer", "0x"+lg["topics"][1][-40:], "prize", word(2), "left", word(3))
# killer tally for rmds (not indexed; use tx to? skip; tally vault distribution)
from collections import Counter
print("RMD per vault:", Counter(lg["address"] for lg in rmds))
