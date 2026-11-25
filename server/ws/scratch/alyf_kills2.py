import subprocess, json
from collections import Counter

RPC = ["python3", "/srv/farm/ws/tools/rpc.py", "bsc"]
KILL = "0x1f645d83d1940a1cb59e44eda10b9611d98402a975eef915b67160f46ee349e3"
TRANSFER = "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef"
VAULTS = ["0xd7D069493685A581d27824Fc46EdA46B7EfC0063","0x7C9e73d4C71dae564d41F78d56439bB4ba87592f","0xbfF4a34A4644a113E8200D7F1D79b3555f723AfE","0xf1bE8ecC990cBcb90e166b71E368299f0116d421","0x158Da805682BdC8ee32d52833aD41E74bb951E59","0x08FC9Ba2cAc74742177e0afC3dC8Aed6961c24e7","0x3282d2a151ca00BfE7ed17Aa16E42880248CD3Cd","0x800933D685E7Dc753758cEb77C8bd34aBF1E26d7","0xfF693450dDa65df7DD6F45B4472655A986b147Eb"]

def scan(topic, start, end, chunk=5000, max_logs_print=8):
    found = []
    b = start
    calls = 0
    while b <= end:
        e = min(b + chunk - 1, end)
        params = [{"fromBlock": hex(b), "toBlock": hex(e), "address": VAULTS, "topics": [[topic]]}]
        r = subprocess.run(RPC + ["eth_getLogs", json.dumps(params)], capture_output=True, text=True)
        calls += 1
        try:
            logs = json.loads(r.stdout)["result"]
        except Exception:
            b = e + 1; continue
        found.extend(logs)
        b = e + 1
    return calls, found

mode = __import__("sys").argv[1]
LATEST = int(__import__("sys").argv[2])
if mode == "control":  # Transfer over last 30k blocks
    c, f = scan(TRANSFER, LATEST - 30000, LATEST - 100)
    print(f"control Transfer: calls={c} logs={len(f)}")
    if f:
        print("sample:", f[-1]["transactionHash"], f[-1]["blockNumber"])
elif mode == "window":  # KILL over [LATEST-days*blocks ...]
    days = int(__import__("sys").argv[3])
    start = LATEST - days * 201600 - 201600
    end = LATEST - days * 201600
    c, f = scan(KILL, start, end)
    print(f"KILL window -{days}d..-{days+1}d blocks {start}..{end}: calls={c} logs={len(f)}")
    for lg in f[:max_logs_print] if 'max_logs_print' in dir() else f[:8]:
        print("KILL", lg["blockNumber"], lg["transactionHash"], "vault", lg["address"][:10], "killer", "0x"+lg["topics"][1][-40:], "prize", int(lg["data"][2:][128:192],16))
