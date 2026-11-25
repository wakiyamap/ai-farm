#!/usr/bin/env python3
"""Fork proof for trial-oraclejob-hai-optimism with a NON-anvil bot wallet (run 4886c647).
Same shape as scratch/trial-hai-oraclejob/proof2.py, but the bot wallet is a fresh funded,
impersonated address, so the wallet balance delta itself shows the profit, and the success
call carries the bot's real minProfit (gas cap + L1 estimate + 1).
One lease: reset optimism 159623936, time-align to 1794846655, deploy, then
  0) eth_call of act(WETH,1,minProfit) -> returned profit
  1) SUCCESS act(WETH,1,minProfit): wallet delta + gas paid = profit > 0
  2) REVERT same item again (already updated): wallet delta = -gas
  3) GUARD-REVERT act(OP,1,100 ETH): NoProfit, wallet delta = -gas
"""
import json, re, subprocess, sys, time, urllib.request

URL = "http://127.0.0.1:9007"
RESET = 159623936
T = 1794846655
BOT = "0x4886c6477b2942a698bd1897b2334dfd000000b0"
ART = "/srv/farm/ws/scratch/trial-hai-oraclejob/contracts/out/HaiOracleJobTrial.sol/HaiOracleJobTrial.json"
HAI = "0x10398AbC267496E49106B07dd6BE13364D10dC71"
WETH = "0x4200000000000000000000000000000000000006"
CAST = "/opt/foundry/bin/cast"
ACT = subprocess.run([CAST, "sig", "act(bytes32,uint256,uint256)"], capture_output=True, text=True).stdout.strip()
MIN_PROFIT = 500_000 * 30_059_570 + 50_000_000_000 + 1   # bot.py: cap (max_fee = 2*base+prio) + L1 est + 1
GAS_PRICE = 30_100_000                                   # 0.0301 gwei, like a live send


def b32(name):
    return "0x" + name.encode().hex().ljust(64, "0")


def rpc(method, params):
    req = urllib.request.Request(URL, data=json.dumps({"jsonrpc": "2.0", "id": 1, "method": method, "params": params}).encode(),
                                 headers={"Content-Type": "application/json"})
    out = json.loads(urllib.request.urlopen(req, timeout=60).read())
    if "error" in out:
        raise RuntimeError(f"{method}: {out['error']}")
    return out["result"]


def forkcli(*args):
    r = subprocess.run(["fork"] + list(args), capture_output=True, text=True)
    print(f"$ fork {' '.join(args)[:90]}\n" + r.stdout[-400:] + r.stderr[-300:])
    return r.stdout


def calldata(name, min_weth, min_profit):
    return ACT + b32(name)[2:] + format(min_weth, "064x") + format(min_profit, "064x")


def send(to, data):
    h = rpc("eth_sendTransaction", [{"from": BOT, "to": to, "gas": hex(500_000), "gasPrice": hex(GAS_PRICE), "data": data}])
    for _ in range(40):
        r = rpc("eth_getTransactionReceipt", [h])
        if r:
            return h, r
        time.sleep(0.5)
    sys.exit("no receipt")


def bal(a):
    return int(rpc("eth_getBalance", [a, "latest"]), 16)


def tok(t, a):
    return int(rpc("eth_call", [{"to": t, "data": "0x70a08231" + a[2:].lower().rjust(64, "0")}, "latest"]), 16)


def cost(r):
    return int(r["gasUsed"], 16) * int(r["effectiveGasPrice"], 16) + int(r.get("l1Fee", "0x0") or "0x0", 16)


subprocess.run(["fork", "lease", "optimism", "15", "trial-oraclejob proof4 run 4886c647"], check=True)
try:
    forkcli("reset", "optimism", str(RESET))
    rpc("evm_setNextBlockTimestamp", [T])
    rpc("evm_mine", [])
    head = int(rpc("eth_blockNumber", []), 16)
    print(f"head={head} ts={int(rpc('eth_getBlockByNumber', [hex(head), False])['timestamp'], 16)}")
    args = subprocess.run([CAST, "abi-encode", "constructor(address)", BOT], capture_output=True, text=True).stdout.strip()
    out = forkcli("deploy", "optimism", ART, "--args", args)
    m = re.findall(r"0x[0-9a-fA-F]{40}(?![0-9a-fA-F])", out)
    if not m:
        sys.exit("deploy address not found")
    ex = m[0]
    print("executor:", ex, "bot():", "0x" + rpc("eth_call", [{"to": ex, "data": "0x10814c37"}, "latest"])[26:])
    rpc("anvil_setBalance", [BOT, hex(10**16)])
    rpc("anvil_impersonateAccount", [BOT])

    d_ok = calldata("WETH", 1, MIN_PROFIT)
    sim = int(rpc("eth_call", [{"from": BOT, "to": ex, "data": d_ok, "gas": hex(500_000)}, "latest"]), 16)
    print(f"0) eth_call profit={sim} wei  minProfit={MIN_PROFIT}")

    b0 = bal(BOT)
    h1, r1 = send(ex, d_ok)
    b1 = bal(BOT)
    c1 = cost(r1)
    print(f"1) SUCCESS tx {h1} status={int(r1['status'], 16)} gas={int(r1['gasUsed'], 16)} block={int(r1['blockNumber'], 16)} "
          f"wallet_delta={b1 - b0} fee_paid={c1} gross={b1 - b0 + c1}")
    print("   executor after: HAI", tok(HAI, ex), "WETH", tok(WETH, ex), "ETH", bal(ex))
    rights_data = "0x06eb54df" + ex[2:].lower().rjust(64, "0") + "30Ce72230A47A0967B7e52A1bAE0178DbD7c6eA3".lower().rjust(64, "0")
    print("   SAFEEngine CoinJoin rights", int(rpc("eth_call", [{"to": "0x9Ff826860689483181C5FAc9628fd2F70275A700", "data": rights_data}, "latest"]), 16))

    h2, r2 = send(ex, d_ok)
    b2 = bal(BOT)
    print(f"2) REVERT tx {h2} status={int(r2['status'], 16)} gas={int(r2['gasUsed'], 16)} wallet_delta={b2 - b1} fee_paid={cost(r2)}")

    h3, r3 = send(ex, calldata("OP", 1, 10**20))
    b3 = bal(BOT)
    print(f"3) GUARD-REVERT tx {h3} status={int(r3['status'], 16)} gas={int(r3['gasUsed'], 16)} wallet_delta={b3 - b2} fee_paid={cost(r3)}")
finally:
    subprocess.run(["fork", "release", "optimism"], check=True)
print("DONE")
