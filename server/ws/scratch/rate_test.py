#!/usr/bin/env python3
"""Rate-test candidate events: count logs from an address over recent blocks,
report rate/hour using actual block timestamps (2 extra reads)."""
import json, sys, urllib.request, collections, time

RELAY = "http://127.0.0.1:8545"

def rpc(chain, method, params, lane="research"):
    req = urllib.request.Request(f"{RELAY}/{chain}?lane={lane}", data=json.dumps(
        {"jsonrpc": "2.0", "id": 1, "method": method, "params": params}).encode(),
        headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=60) as r:
        out = json.loads(r.read())
    if "error" in out:
        return {"_error": out["error"]}
    return out["result"]

def rate(chain, address, topic0, span_blocks, label):
    latest = int(rpc(chain, "eth_blockNumber", []), 16)
    from_b = latest - span_blocks
    params = [{"address": address, "fromBlock": hex(from_b), "toBlock": hex(latest)}]
    if topic0:
        params[0]["topics"] = [topic0]
    logs = rpc(chain, "eth_getLogs", params)
    if isinstance(logs, dict):  # error
        print(f"{label} {chain} ERROR {logs['_error']}")
        return
    blocks = sorted({int(l["blockNumber"], 16) for l in logs})
    ts = {}
    for b in (blocks[:1] + blocks[-1:]):
        blk = rpc(chain, "eth_getBlockByNumber", [hex(b), False])
        if isinstance(blk, dict) and blk.get("timestamp"):
            ts[b] = int(blk["timestamp"], 16)
    span_s = (ts.get(blocks[-1], 0) - ts.get(blocks[0], 0)) if blocks else 0
    # topics histogram
    topics = collections.Counter(l["topics"][0][:10] for l in logs)
    span_blocks_s = ""
    if blocks:
        span_blocks_s = f"blocks {blocks[0]}..{blocks[-1]} span {span_s}s"
    else:
        span_blocks_s = "no logs"
    rate_h = f"{len(logs)/max(span_s,1)*3600:.1f}/h" if span_s > 60 else "?"
    print(f"{label} {chain} n={len(logs)} {rate_h} {span_blocks_s} topics={dict(topics.most_common(4))}")

if __name__ == "__main__":
    a = sys.argv
    rate(a[1], a[2], a[3] if a[3] != "-" else None, int(a[4]), a[5] if len(a) > 5 else "")
