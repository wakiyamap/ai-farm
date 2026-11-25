#!/usr/bin/env python3
"""Self-test of bots/paper/trial-flatmoney-arbitrum/bot.py's own paper path on the fork.
Reset arbitrum 525070833 (parent of the incumbent take 0xd5e1af2d..), mine one block at the
incumbent's timestamp, then call bot.handle() for the announced order of 0x8990f5e5.. with the
relay pointed at the fork and hermes() answering with the incumbent's Pyth blob. Expected:
an `opportunity` row and `paper_sim success` with gain 82602606487086 wei (= the fork proof).
Then at the real relay head: one reread (safety poll) and a real Hermes read.
Usage: python3 selftest.py
"""
import importlib.util, json, os, subprocess, sys, tempfile, time, urllib.request, shutil

BOT = "/srv/farm/ws/bots/paper/grad-flatmoney-arbitrum"
HERE = "/srv/farm/ws/scratch/trial-flatmoney"
FORK = "http://127.0.0.1:9002"
REAL_RELAY = os.environ.get("RPC_RELAY_URL", "http://127.0.0.1:8545")
RESET, WIN_TS = 525070833, 1794928829
ACCOUNT = "0x8990f5e57a8e0b5cabb68d1cd5bd790a92e32f5c"


def frpc(m, p=None):
    req = urllib.request.Request(FORK, data=json.dumps({"jsonrpc": "2.0", "id": 1, "method": m, "params": p or []}).encode(),
                                 headers={"Content-Type": "application/json"})
    r = json.loads(urllib.request.urlopen(req, timeout=120).read())
    if "error" in r:
        raise SystemExit(f"{m}: {r['error']}")
    return r["result"]


def sh(*a):
    out = subprocess.run(list(a), capture_output=True, text=True)
    print("$", " ".join(a), "->", (out.stdout + out.stderr).strip()[:200])
    return out.returncode


def load(relay):
    tmp = tempfile.mkdtemp(prefix="flat-selftest-")
    for f in ("bot.py", "executor-runtime.hex"):
        shutil.copy(f"{BOT}/{f}", tmp)
    os.environ.update(RPC_RELAY_URL=relay, RPC_LANE="research", BOT_MODE="paper")
    spec = importlib.util.spec_from_file_location("bot_" + str(time.time_ns()), tmp + "/bot.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m, tmp


def rows(tmp):
    return [json.loads(l) for l in open(tmp + "/logs/bot.jsonl")]


def decode_updates(inp):
    b = bytes.fromhex(inp[10:])
    base = int.from_bytes(b[32:64], "big")
    o = base + 32 + int.from_bytes(b[base + 32: base + 64], "big")
    ln = int.from_bytes(b[o:o + 32], "big")
    return b[o + 32:o + 32 + ln]


def main():
    blob = decode_updates(open(HERE + "/winner-input-0xd5e1af2d.hex").read().strip())
    if sh("fork", "lease", "arbitrum", "10", "grad-flatmoney-arbitrum selftest"):
        raise SystemExit("lease failed")
    try:
        if sh("fork", "reset", "arbitrum", str(RESET)):
            raise SystemExit("reset failed")
        frpc("evm_setNextBlockTimestamp", [hex(WIN_TS)])
        frpc("evm_mine")
        head = int(frpc("eth_blockNumber"), 16)
        print("fork head", head)
        # the bot's transport (rpc_raw) is pointed at the fork; everything above it is the bot's code
        bot, tmp = load(FORK)

        def fork_raw(method, params, rid):
            if method == "eth_gasPrice":
                return hex(20016000)   # anvil says 1 gwei; the chain's measured median is 0.020016 gwei
            req = urllib.request.Request(FORK, data=json.dumps(
                {"jsonrpc": "2.0", "id": rid, "method": method, "params": params}).encode(),
                headers={"Content-Type": "application/json"})
            ans = json.loads(urllib.request.urlopen(req, timeout=60).read())
            if "error" in ans:
                raise RuntimeError(f"{method}: {json.dumps(ans['error'])[:300]}")
            return ans["result"]
        bot.rpc_raw = fork_raw
        now = int(time.time())
        bot.hermes = lambda feed, binary: (now, 64000.0 if binary else 1790.0, blob if binary else None)
        s = {"done": {}}
        bot.handle(s, ACCOUNT, 5, 231, head - 20, now - bot.MIN_AGE)   # executable right now
        out = rows(tmp)
        for r in out:
            print(json.dumps(r)[:900])
        ok = [r for r in out if r["ev"] == "paper_sim" and r["result"] == "success"]
        assert ok and ok[0]["gain_wei"] == 82602606487086, "paper path did not reproduce the fork proof gain"
        opp = [r for r in out if r["ev"] == "opportunity"][0]
        assert opp["gas_cap_usd"] < 1.0 and opp["min_profit"] < opp["gain_wei"]
        print("FORK PAPER PATH OK: gain", ok[0]["gain_wei"], "gas_limit", opp["gas_limit"], "estimated", opp["gas_estimated"])
    finally:
        sh("fork", "release", "arbitrum")
    # real relay head + real Hermes
    bot, tmp = load(REAL_RELAY)
    pub, px, b = bot.hermes(bot.FEED_WBTC, True)
    print("hermes: publish lag s", round(time.time() - pub, 2), "wbtc", px, "bytes", len(b), "eth_ref", bot.eth_ref_usd())
    s = {"done": {}, "last_poll": 0}
    bot.reread(s, "selftest")
    for r in rows(tmp):
        print(json.dumps(r)[:600])
    print("SELFTEST OK")


if __name__ == "__main__":
    main()
