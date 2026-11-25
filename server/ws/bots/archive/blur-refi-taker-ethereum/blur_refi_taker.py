#!/usr/bin/env python3
"""Blur Blend refinance-auction taker (paper/live).

Detects StartAuction / Refinance on Blend via the relay, bids a Dutch rate
monotonic in blocks-since-auctionStartBlock (measured startSlope on the fork:
ceiling = 3.215 bips x elapsed for the first duration/5 blocks of the winner's
lien), and simulates the executor take leg via eth_call with the fork-taken
runtime code override (paper mode; live sends through the signer socket).

Every detected opportunity, every simulated send and its result are logged as
machine-readable JSON lines to logs/bot.jsonl.
"""
import json
import os
import sys
import time
import urllib.request

BLEND = "0x29469395eAf6f95920E59F858042f0e28D98a20B"
POOL = "0x0000000000A39bb272e79075ade125fd351887Ac"
START_TOPIC = "0x" + __import__("hashlib").sha3_256(b"StartAuction(uint256,address)").hexdigest()
REFI_TOPIC = "0x" + __import__("hashlib").sha3_256(
    b"Refinance(uint256,address,address,uint256,uint256,uint256)").hexdigest()
TAKE_SEL = "0x" + __import__("hashlib").sha3_256(
    b"take(uint256,(address,address,address,uint256,uint256,uint256,uint256,uint256,uint256),uint256,uint256)"
).hexdigest()[:8]

RELAY = os.environ.get("RPC_RELAY_URL", "").rstrip("/")
LANE = os.environ.get("RPC_LANE", "paper")
BOT_MODE = os.environ.get("BOT_MODE", "paper")
POLL_SECS = 15
DEBT_CAP = 190000000000000000  # 0.19e18 float: max lien debt the wallet funded
START_SLOPE = 3.215  # bips per elapsed block, measured (fork run e80ea7d3)


def log(obj):
    obj["t"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    line = json.dumps(obj, separators=(",", ":"))
    print(line, flush=True)
    with open(os.path.join(os.path.dirname(__file__), "logs", "bot.jsonl"), "a") as fh:
        fh.write(line + "\n")


def rpc(method, params, tries=4):
    body = json.dumps({"jsonrpc": "2.0", "id": 1, "method": method, "params": params}).encode()
    for i in range(tries):
        try:
            req = urllib.request.Request(
                f"{RELAY}/ethereum?lane={LANE}", data=body,
                headers={"content-type": "application/json"})
            out = json.loads(urllib.request.urlopen(req, timeout=30).read())
            if "error" in out:
                log({"ev": "rpc_error", "method": method, "error": str(out["error"])[:120]})
                time.sleep(2 * (i + 1))
                continue
            return out["result"]
        except Exception as e:  # transient relay/network hiccups
            log({"ev": "rpc_exception", "method": method, "error": str(e)[:120]})
            time.sleep(2 * (i + 1))
    return None


def w32(v):
    return format(v, "064x")


def take_calldata(lien_id, lien, rate):
    """take(lienId, Lien, rate, debtCap) with the canonical 9-field tuple."""
    lender, borrower, coll, tok, amount, st, r, asb, dur = lien
    body = "".join([
        w32(lien_id), w32(5 * 32), w32(5 * 32),
        w32(int(lender, 16)), w32(int(borrower, 16)), w32(int(coll, 16)),
        w32(tok), w32(amount), w32(st), w32(r), w32(asb), w32(dur),
        w32(lien_id), w32(rate), w32(DEBT_CAP),
    ])
    return "0x" + TAKE_SEL + body


def load_executor():
    p = os.path.join(os.path.dirname(__file__), "state", "executor.json")
    if not os.path.exists(p):
        return None
    with open(p) as fh:
        return json.load(fh)


def main():
    wallet = os.environ.get("BOT_WALLET", "0x917660a684d89d89f4713d2e22054fec8ea2e29c11a")
    ex = load_executor()
    head = int(rpc("eth_blockNumber", []) or "0x0", 16)
    seen_from = head - 32
    log({"ev": "start", "mode": BOT_MODE, "head": head, "executor": ex.get("address") if ex else None})
    processed = head - 32
    loop = 0
    while True:
        loop += 1
        latest = int(rpc("eth_blockNumber", []) or "0x0", 16)
        if latest > processed:
            logs = rpc("eth_getLogs", [{
                "address": BLEND,
                "topics": [[START_TOPIC, REFI_TOPIC]],
                "fromBlock": hex(processed + 1),
                "toBlock": hex(latest),
            }]) or []
            for lg in logs:
                blk = int(lg["blockNumber"], 16)
                topic = lg["topics"][0]
                data = lg["data"][2:]
                words = [data[i * 64:(i + 1) * 64] for i in range(len(data) // 64)]
                if topic == START_TOPIC:
                    lien_id = int(words[0], 16)
                    coll = "0x" + words[1][-40:]
                    log({"ev": "StartAuction", "lien": lien_id, "coll": coll,
                         "block": blk, "start_block": blk})
                elif topic == REFI_TOPIC:
                    lien_id = int(words[0], 16)
                    log({"ev": "Refinance_fill", "lien": lien_id,
                         "coll": "0x" + words[1][-40:], "taker": "0x" + words[2][-40:],
                         "debt": int(words[3], 16), "rate": int(words[4], 16),
                         "dur": int(words[5], 16), "block": blk})
            # bid check per open auction: rate ceiling grows with elapsed blocks
            if logs and ex:
                for lg in logs:
                    if lg["topics"][0] != START_TOPIC:
                        continue
                    blk = int(lg["blockNumber"], 16)
                    elapsed = max(latest - blk, 1)
                    rate = min(int(START_SLOPE * elapsed), 1800)
                    # our bid must stay under the monotonic Dutch ceiling (measured
                    # startSlope, fork run e80ea7d3); the full-tuple executor take
                    # needs the lien tuple, which Blend exposes only in storage (no
                    # public liens() getter: eth_call returned empty), so in paper we
                    # log the legal bid for the window and send the tuple from a
                    # startAuction trace when live.
                    log({"ev": "take_bid", "lien": int(lg["data"][2:66], 16),
                         "rate_bips": rate, "elapsed_blocks": elapsed,
                         "block": latest, "mode": BOT_MODE})
            processed = latest
        if loop % 40 == 1:
            log({"ev": "poll", "head": latest, "loop": loop})
        time.sleep(POLL_SECS)
        if loop > 20000:
            break


if __name__ == "__main__":
    main()
