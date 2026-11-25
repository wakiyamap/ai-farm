"""Seamless V2 (leverage tokens) ethereum: 7-day rebalance/take scan, scout run bea55ede."""
import json, subprocess

RPC = "/srv/farm/ws/tools/rpc.py"
LM = "0x5C37EB148D4a261ACD101e2B997A0F163Fb3E351"
TAKER_ADAPTER = "0x42fc033435f4640affed1d5cf6f3bbe240d081af"   # LT 0x98c4 wstETH/WETH 25x
WATCH_ADAPTER = "0x5e4837e4672e8f84b53cf884aadea0e858b40d36"   # LT 0xce93 fixed 0.90 mult
LT1 = "0x98c4e43e3bde7b649e5aa2f88de1658e8d3ed1bf"
LT2 = "0xce937010b7e55da282e6161f7aa4744a0b732035"
REB_T0 = "0x1ece35fa7611d2dfc7e11d022888a20c4987d6ededbb34a26c93fd53f2073899"
CALLER = "0x000000000000000000000000000000000000b00b"


def call(method, params):
    o = subprocess.run(["python3", RPC, "ethereum", method, json.dumps(params)],
                       capture_output=True, text=True)
    try:
        j = json.loads(o.stdout)
    except Exception:
        raise RuntimeError("bad json: " + o.stdout[:300] + o.stderr[:300])
    if "error" in j:
        raise RuntimeError(str(j["error"])[:300])
    return j["result"]


def calldata(sig, arg=""):
    o = subprocess.run(["/opt/foundry/bin/cast", "calldata", sig, arg], capture_output=True, text=True)
    return o.stdout.strip()


head = int(call("eth_blockNumber", []), 16)
d7 = head - 50400  # ~7 d at 12 s
d30 = head - 720 * 30 * 10  # 30 d
d30 = head - 86400 // 12 * 30
print("head", head, "from7", d7, "from30", head - 21600 * 10)

# 1) Rebalance events on LM, last 7 d
logs7 = call("eth_getLogs", [{"address": LM, "topics": [REB_T0], "fromBlock": hex(head - 50400), "toBlock": hex(head)}])
print("\nRebalance 7d: n =", len(logs7))
for l in logs7:
    w = [int(l["data"][2 + 64 * i:2 + 64 * (i + 1)], 16) for i in range(8)]
    tok = "0x" + l["topics"][1][-40:]
    print("  blk", int(l["blockNumber"], 16), "tok", tok[:10], "eqLoss %.6f" % ((w[2] - w[6]) / 1e18), "tx", l["transactionHash"])

# 2) control: 30 d window, same shape
logs30 = call("eth_getLogs", [{"address": LM, "topics": [REB_T0], "fromBlock": hex(head - 216000), "toBlock": hex(head)}])
print("Rebalance 30d: n =", len(logs30), "blocks:", [int(l['blockNumber'],16) for l in logs30])

# 3) no-topic scan of paying adapter, last 7 d (AuctionCreated / Take / AuctionEnded)
al = call("eth_getLogs", [{"address": TAKER_ADAPTER, "fromBlock": hex(head - 50400), "toBlock": hex(head)}])
print("\nAdapter 0x42fc 7d no-topic logs: n =", len(al))
for l in al[-12:]:
    print("  blk", int(l["blockNumber"], 16), "t0", l["topics"][0][:18] if l["topics"] else None, "tx", l["transactionHash"][:20])

# 4) no-topic scan of watch adapter, last 7 d
wl = call("eth_getLogs", [{"address": WATCH_ADAPTER, "fromBlock": hex(head - 50400), "toBlock": hex(head)}])
print("Adapter 0x5e48 7d no-topic logs: n =", len(wl))
for l in wl[-8:]:
    print("  blk", int(l["blockNumber"], 16), "t0", l["topics"][0][:18] if l["topics"] else None)

# 5) current state: LM getLeverageTokenState for the two LTs (equity check)
for lt in (LT1, LT2):
    r = call("eth_call", [{"to": LM, "data": calldata("getLeverageTokenState(address)", lt)}, "latest"])
    w = [int(r[2 + 64 * i:2 + 64 * (i + 1)], 16) for i in range(4)]
    print("LT", lt[:10], "collateral %.4f debt %.4f equity %.6f CR %.6f" % (w[0]/1e18, w[1]/1e18, w[2]/1e18, w[3]/1e18))

# 6) adapter 0x42fc: auction state + fresh-address take(1e18) eth_call
a = call("eth_call", [{"to": TAKER_ADAPTER, "data": calldata("getAuction()")}, "latest"])
print("getAuction raw:", a[:2 + 64 * 6])
v = call("eth_call", [{"to": TAKER_ADAPTER, "data": calldata("isAuctionValid()")}, "latest"])
print("isAuctionValid:", v)
try:
    t = call("eth_call", [{"from": CALLER, "to": TAKER_ADAPTER, "data": calldata("take(uint256)", "1000000000000000000")}, "latest"])
    print("take(1e18) from fresh addr: OK", t[:66])
except RuntimeError as e:
    print("take(1e18) from fresh addr reverts:", str(e)[:160])
