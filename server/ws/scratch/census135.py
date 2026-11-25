import json, os, time, urllib.request

RELAY = os.environ["RPC_RELAY_URL"]
LANE = "research"

def call(method, params, tries=3):
    body = json.dumps({"jsonrpc": "2.0", "id": 1, "method": method, "params": params}).encode()
    for i in range(tries):
        try:
            req = urllib.request.Request(f"{RELAY}/polygon?lane={LANE}", body, headers={"content-type": "application/json"})
            r = json.loads(urllib.request.urlopen(req, timeout=30).read())
            if "error" in r:
                print(f"  {method} err[{i}]: {r['error'].get('message','')[:120]}")
                time.sleep(2)
                continue
            return r["result"]
        except Exception as e:
            print(f"  {method} exc[{i}]: {e}")
            time.sleep(3)
    return None

ADDRS = [
    "0xc011a7e12a19f7b1f670d46f03b03f3342e82dfb",  # P1 proxy
    "0xce84e053301a82937f90ee2c2c1889cab1db25de",  # P1 impl
    "0xc417fd8e9661c0d2120b64a04bb3278c17e99db1",  # P2 proxy
    "0xd206ac7fef53d83ed4563e770b28dba90d0d9ec8",  # P2 impl
    "0xa1200000d0002264c9a1698e001292d00e1b00af",  # A0
    "0xada100874d00e3331d00f2007a9c336a65009718",  # A3
    "0x4d97dcd97ec945f40cf65f87097ace5ea0476045",  # A4
    "0x93070a847efef7f70739046a929d47a521f5b8ee",  # A5
    "0xada200001000ef00d07553cee7006808f895c6f1",  # pool1 (from trace)
    "0xd91e80cf2e7be2e162c6513ced06f1dd0da35296",  # pool2 (from trace)
    "0xe111180000d2663c0091e4f400237545b87b996b",  # batch router 1
    "0xe2222d279d744050d28e00520010520000310f59",  # batch router 2
]
USDC = "0x2791bca1f2de4661ed88a30c99a7a9449aa84174"
TRANSFER = "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef"
COLLECT4 = "0x785efdf4708eb97e233613fb0f8a510dd3b5c2d2a577b0ce16ba6df1e293e431"  # Collect(address,uint256,uint256,uint128)
COLLECT6 = "0xbfa48967eaf5c7102525dab5406ee10f6c564e2a08c5fdc806b2977951b4b226"  # Collect(address,uint256,uint256,uint256,uint256,uint256)
SWAP = "0x983f567e4944b68267d1bbf7a75834d38420e27bff4f4af6d3988bb18c6ef37c"  # UniV3 pool Swap

head = int(call("eth_blockNumber", []), 16)
print("head:", head)
C_FROM, C_TO = head - 45000, head - 1000   # ~1 day window, below cached head
PAGE = 1100

def logs(frm, to, addr, topic0, tries=3):
    return call("eth_getLogs", [{"address": addr, "topics": [topic0],
                                 "fromBlock": hex(frm), "toBlock": hex(to)}], tries)

# control: Transfer on USDC over the last 30 blocks of the window, same shape+form
ctrl_rng = [C_TO - 29, C_TO]
ctrl = logs(ctrl_rng[0], ctrl_rng[1], USDC, TRANSFER)
print("control Transfer USDC blocks", ctrl_rng, "->", len(ctrl) if ctrl is not None else "FAIL", "logs")

results = {}
for name, t0 in [("collect4", COLLECT4), ("collect6", COLLECT6)]:
    found = []
    frm = C_FROM
    pages = 0
    while frm < C_TO:
        to = min(frm + PAGE - 1, C_TO)
        r = logs(frm, to, ADDRS, t0)
        if r is None:
            print(f"  {name} page {frm}-{to}: FAILED after retries")
        else:
            found.extend(r)
            pages += 1
        frm = to + 1
    results[name] = found
    print(f"{name}: {len(found)} logs in {pages} pages")
    for lg in found[:30]:
        print("  ", lg["address"], "block", int(lg["blockNumber"], 16), "tx", lg["transactionHash"],
              "data", lg["data"][:160])

json.dump(results, open("/srv/farm/ws/scratch/census135-collect.json", "w"))

# Swap activity control on the two trace pools + P2 proxy, last 4000 blocks, 1000-block pages
sw = []
frm = C_TO - 4000
while frm < C_TO:
    to = min(frm + 999, C_TO)
    r = logs(frm, to, [ADDRS[2], ADDRS[8], ADDRS[9]], SWAP)
    if r: sw.extend(r)
    frm = to + 1
print("Swap logs on P2/pool1/pool2 over 4000 blocks:", len(sw))
for a in [ADDRS[2], ADDRS[8], ADDRS[9]]:
    print(" ", a, ":", sum(1 for lg in sw if lg["address"].lower() == a))
