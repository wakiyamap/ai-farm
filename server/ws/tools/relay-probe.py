#!/usr/bin/env python3
"""Bounded relay behaviour probe (meta/researcher diagnostic, read-only).

Checks one suspected relay quirk with a positive control in the same run, so an
inbox/meta note can be closed or confirmed from measured output. Each check makes
at most 5 JSON-RPC calls on the research lane.

  python3 tools/relay-probe.py getlogs-topic-only --chain ethereum
      eth_getLogs for ERC-20 Transfer over one block 30 below head:
      topic-only (no address) vs the same filter with a busy token address.
      A topic-only count of 0 while the control is > 0 = vacuous empty.

  python3 tools/relay-probe.py getlogs-range --chain ethereum
      USDC Transfer over 8 blocks: address+topics+fromBlock/toBlock vs the same
      range without topics (filtered client-side). Counts must match; an error on
      the first = the 11-09 "-32602 Variadic on topics+fromBlock" report.

  python3 tools/relay-probe.py storage-slot --chain ethereum --address 0x.. [--slot 0x..]
      "eth_getStorageAt returns 0x0 at the implementation slot": reads the quoted
      slot and the PUSH32 slot constants of the proxy's own bytecode (11-21).
"""
import argparse
import json
import os
import sys
import urllib.request

TRANSFER = "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef"
CONTROL_TOKEN = {  # busy USDC deployments (checked addresses)
    "ethereum": "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48",  # fixed 11-09 (was a wrong address)
    "base": "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913",
    "arbitrum": "0xaf88d065e77c8cC2239327C5EDb3A432268e5831",
    # chains added 2026-11-10 (meta 5acefe05); a 0 on both sides of a check = quiet
    # range, not a relay answer: retry with --from-block on a busier range
    "bsc": "0x8AC76a51cc950d9822D68b83fE1Ad97B32Cd580d",  # Binance-Peg USDC, 18 decimals
    "polygon": "0x3c499c542cEF5E3811e1192ce70d8cC03d5c3359",
    "avalanche": "0xB97EF9Ef8734C71904D8002F8b6Bc66Dd9c48a6E",
    "optimism": "0x0b2C639c533813f4Aa9D7837CAf62653d097Ff85",
    "hyperevm": "0xb88339CB7199b77E23DB6E890353E22632Ba630f",
    # added 2026-11-11 (meta 718540da, phase 10g); human-given, 6 decimals. Chain is days
    # old and 100-200 ms blocks: an 8-block range is ~1 s, expect 0=0 often
    "elysium": "0xb47c4C8F73F009CC0C0d3f92B388d13E293F0B65",
}


def rpc(url, chain, method, params):
    body = json.dumps({"jsonrpc": "2.0", "id": 1, "method": method, "params": params}).encode()
    req = urllib.request.Request(f"{url}/{chain}?lane=research", data=body,
                                 headers={"content-type": "application/json"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read())


def getlogs_topic_only(url, chain):
    head = int(rpc(url, chain, "eth_blockNumber", [])["result"], 16)
    blk = hex(head - 30)
    tok, top, counts = CONTROL_TOKEN[chain], None, {}
    out = {"chain": chain, "head": head, "block": head - 30}
    for name, flt in (("topic_only", {"fromBlock": blk, "toBlock": blk, "topics": [TRANSFER]}),
                      ("control_usdc", {"fromBlock": blk, "toBlock": blk, "address": tok, "topics": [TRANSFER]}),
                      ("control_usdc_lower", {"fromBlock": blk, "toBlock": blk, "address": tok.lower(),
                                              "topics": [TRANSFER]})):
        r = rpc(url, chain, "eth_getLogs", [flt])
        if "result" not in r:
            out[name] = {"error": json.dumps(r.get("error"))[:300]}
            continue
        out[name] = len(r["result"])
        if name == "topic_only":  # cross-check: control-address logs inside the unfiltered answer
            out["topic_only_from_usdc"] = sum(1 for x in r["result"] if x["address"].lower() == tok.lower())
            counts = {}
            for x in r["result"]:
                counts[x["address"]] = counts.get(x["address"], 0) + 1
            top = max(counts, key=counts.get) if counts else None
    if top:  # address filter on the busiest emitter must return the same count
        r = rpc(url, chain, "eth_getLogs", [{"fromBlock": blk, "toBlock": blk, "address": top, "topics": [TRANSFER]}])
        out["control_top"] = {"address": top, "in_topic_only": counts[top],
                              "address_filtered": len(r["result"]) if "result" in r else r.get("error")}
    return out


def getlogs_range(url, chain, start=None):
    """topics + fromBlock/toBlock over an 8-block range (the shape reported as -32602
    Variadic on 11-09 03:30Z) vs the same range with no topics, filtered client-side."""
    head = int(rpc(url, chain, "eth_blockNumber", [])["result"], 16)
    start = start if start is not None else head - 40
    lo, hi = hex(start), hex(start + 7)
    tok = CONTROL_TOKEN[chain]
    out = {"chain": chain, "head": head, "range": [start, start + 7]}
    r = rpc(url, chain, "eth_getLogs", [{"fromBlock": lo, "toBlock": hi, "address": tok, "topics": [TRANSFER]}])
    out["with_topics"] = len(r["result"]) if "result" in r else {"error": json.dumps(r.get("error"))[:300]}
    r = rpc(url, chain, "eth_getLogs", [{"fromBlock": lo, "toBlock": hi, "address": tok}])
    out["no_topics_filtered"] = (sum(1 for x in r["result"] if x["topics"] and x["topics"][0] == TRANSFER)
                                 if "result" in r else {"error": json.dumps(r.get("error"))[:300]})
    return out


EIP1967_IMPL = "0x360894a13ba1a3210667c828492db98dca3e2076cc3735a920a3ca505d382bbc"


KNOWN_SLOTS = [EIP1967_IMPL,
               "0x7050c9e0f4ca769c69bd3a8ef740bc37934f8e2c036e5a723fd8ee048ed3f8c3",  # OZ zos impl (USDC)
               "0xa3f0ad74e5423aebfd80d3ef4346578335a9a72aeaee59ff6cb3582b35133d50"]  # EIP-1967 beacon
EMPTY_CODEHASH = "0xc5d2460186f7233c927e7db2dcc703c0e500b653ca82273b7bfad8045d85a470"


def _ascii_like(h):
    b = bytes.fromhex(h)
    return (sum(32 <= c < 127 for c in b) >= 24  # message strings
            or h.startswith("0" * 16) or h.endswith("0" * 40)  # padded addresses, selectors
            or "0x" + h == EMPTY_CODEHASH)


def storage_slot(url, chain, address, slot=None):
    """A '0x0 at the implementation slot' report (11-21 scout, ethereum: a mistyped
    constant) vs the slot constants the proxy's own bytecode PUSH32es
    (pitfalls/proxy-implementation-slot-lookup.md). Nonzero at a bytecode constant =
    relay storage reads work; the quoted slot was wrong. <= 5 calls."""
    code = rpc(url, chain, "eth_getCode", [address, "latest"]).get("result", "0x")[2:].lower()
    out = {"chain": chain, "address": address, "code_bytes": len(code) // 2}
    consts, i = [], 0
    while True:  # walk opcodes so PUSH data is not misread as a 0x7f opcode
        if i >= len(code):
            break
        op = int(code[i:i + 2], 16)
        if 0x60 <= op <= 0x7f:
            n = op - 0x5f
            if op == 0x7f:
                c = code[i + 2:i + 2 + 64]
                if len(c) == 64 and not _ascii_like(c) and "0x" + c not in consts:
                    consts.append("0x" + c)
            i += 2 + 2 * n
        else:
            i += 2
    out["eip1967_in_bytecode"] = EIP1967_IMPL in consts
    reads = []
    if slot:
        out["quoted_slot_in_bytecode"] = slot.lower() in consts
        reads.append(slot.lower())
    for c in [k for k in KNOWN_SLOTS if k in consts] + consts:
        if c not in reads and len(reads) < 4:
            reads.append(c)
    out["reads"] = {}
    for s in reads:
        r = rpc(url, chain, "eth_getStorageAt", [address, s, "latest"])
        out["reads"][s] = r.get("result", {"error": json.dumps(r.get("error"))[:200]})
    nz = [s for s, v in out["reads"].items() if isinstance(v, str) and int(v, 16) != 0]
    out["verdict"] = ("relay storage reads work (nonzero at %s); a zero elsewhere = wrong slot" % nz[0]
                      if nz else "all zero: not a proxy with a PUSH32 slot, or a beacon; no relay bug shown")
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("check", choices=["getlogs-topic-only", "getlogs-range", "storage-slot"])
    ap.add_argument("--chain", choices=sorted(CONTROL_TOKEN), required=True)
    ap.add_argument("--from-block", type=int, help="getlogs-range: first block (default head-40)")
    ap.add_argument("--address", help="storage-slot: the proxy that read 0x0")
    ap.add_argument("--slot", help="storage-slot: the slot you read (checked against the bytecode)")
    a = ap.parse_args()
    url = os.environ.get("RPC_RELAY_URL", "").rstrip("/")
    if not url:
        sys.exit("RPC_RELAY_URL not set")
    if a.check == "getlogs-topic-only":
        print(json.dumps(getlogs_topic_only(url, a.chain)))
    elif a.check == "storage-slot":
        if not a.address:
            sys.exit("storage-slot needs --address")
        print(json.dumps(storage_slot(url, a.chain, a.address, a.slot)))
    else:
        print(json.dumps(getlogs_range(url, a.chain, a.from_block)))


if __name__ == "__main__":
    main()
