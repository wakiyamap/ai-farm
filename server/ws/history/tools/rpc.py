#!/usr/bin/env python3
"""One JSON-RPC read through the farm relay, without shell curl.

Why: sessions running under the harness "don't ask" permission mode have the
`curl ... "$RPC_RELAY_URL/..."` form refused (researcher ce71d6eb, meta d3c79d67,
2026-11-12), while `python3 /srv/farm/ws/tools/...` is allowed.

usage:
  python3 /srv/farm/ws/tools/rpc.py <chain> <method> ['<json params>'] [--lane research|paper|live] [--params-file scratch/p.json]
examples:
  python3 /srv/farm/ws/tools/rpc.py base eth_blockNumber
  python3 /srv/farm/ws/tools/rpc.py base eth_call '[{"to":"0x..","data":"0x.."},"latest"]'
Prints the raw JSON-RPC response (result or error) on stdout (with --out f:
saves it and prints bytes + result length); exit 1 on an error response or
HTTP/transport failure. eth_getLogs is refused before sending (exit 2) for
caller errors that give a silent [] or -32602: non-0x block bounds, addresses
not 40 hex digits, topics not 64 hex digits, a trailing null topic, or a topic
within 8 digits of a well-known topic0 (hand-typed Transfer etc.). Read-only: eth_send* and other
signing methods are refused here (sending is the gate's job).
stderr hints (never change stdout or exit code): empty-data reverts, an empty
eth_call/eth_getCode result, and an address that shares its first 8 digits with
a well-known token but is not it.
"""
import argparse
import json
import os
import sys
import urllib.error
import urllib.request

CHAINS = {"base", "arbitrum", "ethereum", "bsc", "polygon", "avalanche", "optimism", "hyperevm", "elysium"}
REFUSED_PREFIXES = ("eth_send", "eth_sign", "personal_", "anvil_", "hardhat_", "evm_", "admin_", "miner_")


# Canonical topic0s, each from `cast keccak "<sig>"` (meta d3c79d67, 2026-11-12).
KNOWN_TOPICS = {
    "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef": "Transfer(address,address,uint256)",
    "0x8c5be1e5ebec7d5bd14f71427d1e84f3dd0314c0f7b2291e5b200ac8c7c3b925": "Approval(address,address,uint256)",
    "0xc42079f94a6350d7e6235f29174924f928cc2ac818eb64fed8004e115fbcca67": "Swap(address,address,int256,int256,uint160,uint128,int24)",
    "0xd78ad95fa46c994b6551d0da85fc275fe613ce37657fb8d5e3d130840159d822": "Swap(address,uint256,uint256,uint256,uint256,address)",
    "0x1c411e9a96e071241c2f21f7726b17ae89e3cab4c78be50e062b03a9fffbbad1": "Sync(uint112,uint112)",
    "0xe1fffcc4923d04b559f4d29a8bfc6cda04eb5b0d3c460751c2402c5c5cc9109c": "Deposit(address,uint256)",
    "0x7fcf532c15f0a6db0bd6d0e038bea71d30d808c7d98cb3bf7268a95bf5081b65": "Withdrawal(address,uint256)",
}
HEX = set("0123456789abcdef")


def _is_hex(s: str, digits: int) -> bool:
    return isinstance(s, str) and s.startswith("0x") and len(s) == 2 + digits and set(s[2:].lower()) <= HEX


def check_getlogs(params: list) -> list:
    """Return caller errors that make eth_getLogs answer a silent [] or a -32602."""
    errs = []
    flt = params[0] if params and isinstance(params[0], dict) else {}
    for k in ("fromBlock", "toBlock"):
        v = flt.get(k)
        if isinstance(v, str) and v not in ("latest", "earliest", "pending", "safe", "finalized") and not v.startswith("0x"):
            errs.append(f"{k}={v!r}: block bounds must be 0x-hex (e.g. {hex(int(v)) if v.isdigit() else '0x...'})")
        if isinstance(v, int):
            errs.append(f"{k}={v}: block bounds must be 0x-hex strings, not JSON numbers ({hex(v)})")
    addrs = flt.get("address")
    for a in (addrs if isinstance(addrs, list) else [addrs] if addrs else []):
        if not _is_hex(a, 40):
            errs.append(f"address {a!r} is not 0x + 40 hex digits")
    topics = flt.get("topics") or []
    if topics and topics[-1] is None:
        errs.append("trailing null in topics returns a silent [] on some providers: drop it")
    for i, t in enumerate(topics):
        for x in (t if isinstance(t, list) else [t]):
            if x is None:
                continue
            if not _is_hex(x, 64):
                errs.append(f"topic[{i}] {x!r} is not 0x + 64 hex digits ({len(x) - 2 if isinstance(x, str) else '?'} given); build it with cast keccak")
                continue
            xl = x.lower()
            if xl in KNOWN_TOPICS:
                continue
            for good, sig in KNOWN_TOPICS.items():
                diff = sum(1 for p, q in zip(xl, good) if p != q)
                if diff <= 8 or xl[:10] == good[:10]:
                    errs.append(f"topic[{i}] {x} differs from {sig} = {good} in {diff} digits: hand-typed? use cast keccak")
    return errs


# A call that reverts with empty data is almost always the caller's calldata,
# not the node (11-13: a hand-typed decimals() selector 0xed42883a and an
# unpadded address argument were both filed as an "ethereum eth_call incident").
CALL_METHODS = {"eth_call", "eth_estimateGas", "debug_traceCall"}
KNOWN_SELECTORS = {  # from `cast sig`
    "0x313ce567": "decimals()", "0x70a08231": "balanceOf(address)", "0x18160ddd": "totalSupply()",
    "0x95d89b41": "symbol()", "0x06fdde03": "name()", "0xdd62ed3e": "allowance(address,address)",
    "0xa9059cbb": "transfer(address,uint256)", "0x095ea7b3": "approve(address,uint256)",
    "0x5c975abb": "paused()", "0x3850c7bd": "slot0()", "0x0902f1ac": "getReserves()", "0x8da5cb5b": "owner()",
}


def selector_near_miss(sel: str) -> list:
    """Known selectors within 2 hex digits of sel (11-13: balanceOf typed 0x70a08201 -> 'fork serves no ERC-20 state')."""
    return [f"{good} = {name}" for good, name in KNOWN_SELECTORS.items()
            if sel != good and sum(1 for p, q in zip(sel, good) if p != q) <= 2]


# Canonical token addresses, checked on-chain through the relay or fork with
# symbol()/totalSupply()/balanceOf()/getCode (meta cb13f5e0, 2026-11-13); the
# elysium USDC comes from common.md and was not read on-chain. 11-13: an earner used
# "DAI 0x6B175474E89094C44Da228e5..." and "USDC 0xA0b86991c6218b36c119B366..."
# (right prefix, invented tail, no code), read the empty answers as a broken
# fork and lost four sessions on lead 167.
KNOWN_ADDRESSES = {
    "ethereum": {
        "0x6b175474e89094c44da98b954eedeac495271d0f": "DAI",
        "0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48": "USDC",
        "0xdac17f958d2ee523a2206206994597c13d831ec7": "USDT",
        "0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2": "WETH",
        "0x2260fac5e5542a773aa44fbcfedf7c193bc2c599": "WBTC",
        "0x5f98805a4e8be255a32880fdec7f6728c6568ba0": "LUSD",
    },
    "base": {"0x833589fcd6edb6e08f4c7c32d4f71b54bda02913": "USDC"},
    "arbitrum": {
        "0xaf88d065e77c8cc2239327c5edb3a432268e5831": "USDC",
        "0x82af49447d8a07e3bd95bd0d56f35241523fbab1": "WETH",
    },
    "optimism": {"0x0b2c639c533813f4aa9d7837caf62653d097ff85": "USDC"},
    "polygon": {"0x3c499c542cef5e3811e1192ce70d8cc03d5c3359": "USDC"},
    "avalanche": {"0xb97ef9ef8734c71904d8002f8b6bc66dd9c48a6e": "USDC"},
    "bsc": {"0x8ac76a51cc950d9822d68b83fe1ad97b32cd580d": "USDC (18 decimals)"},
    "elysium": {"0xb47c4c8f73f009cc0c0d3f92b388d13e293f0b65": "USDC"},
}
ADDR_METHODS = CALL_METHODS | {"eth_getCode", "eth_getBalance", "eth_getStorageAt"}


def target_address(method: str, params: list):
    if method in CALL_METHODS:
        tx = params[0] if params and isinstance(params[0], dict) else {}
        return tx.get("to")
    return params[0] if params and isinstance(params[0], str) else None


def address_hints(chain: str, method: str, params: list, obj: dict) -> list:
    """Hints (stderr only) for a near-miss of a well-known address or an empty answer."""
    if method not in ADDR_METHODS:
        return []
    a = target_address(method, params)
    if not isinstance(a, str):
        return []
    al, hints = a.lower(), []
    known = KNOWN_ADDRESSES.get(chain, {})
    if al not in known:
        for good, name in known.items():
            if al[:10] == good[:10]:
                hints.append(f"{a} starts like {name} on {chain} ({good}) but is not it: "
                             "a hand-typed or remembered address? take addresses from the protocol docs or explorer")
    if method in ("eth_call", "eth_getCode") and obj.get("result") == "0x":
        hints.append(f"empty result: {a} may have no code on {chain} at this block. Check the address "
                     "(eth_getCode, docs, explorer) before calling the node or the fork broken")
    return hints


def revert_hints(params: list, err: dict) -> list:
    """Hints (stderr only) for an empty-data revert; never changes stdout or exit code."""
    if "revert" not in str(err.get("message", "")).lower() or err.get("data") not in (None, "0x", ""):
        return []
    tx = params[0] if params and isinstance(params[0], dict) else {}
    data = (tx.get("data") or tx.get("input") or "").lower()
    if not data.startswith("0x") or len(data) < 10:
        return []
    sel, args = data[:10], data[10:]
    hints = []
    if len(args) % 64:
        hints.append(f"{len(args)} hex digits after the selector is not a whole number of 32-byte words: "
                     "pad each address/uint argument to 64 digits (cast calldata '<sig>' <args>)")
    name = KNOWN_SELECTORS.get(sel)
    near = [] if name else selector_near_miss(sel)
    if near:
        hints.append(f"selector {sel} is 1-2 hex digits away from {', '.join(near)}: a typo? "
                     "build calldata with cast calldata '<sig>' <args>, never by hand")
    hints.append(f"selector {sel} = {name}" if name else
                 f"selector {sel} is not in the known-getter table: confirm it with cast sig '<fn(types)>' "
                 "(decimals() is 0x313ce567) and test one known getter before calling the node broken")
    return hints


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("chain")
    ap.add_argument("method")
    ap.add_argument("params", nargs="?", default="[]", help="JSON array (default [])")
    ap.add_argument("--lane", default="research", choices=["research", "paper", "live"])
    ap.add_argument("--params-file", help="read the params JSON array from this file instead")
    ap.add_argument("--timeout", type=float, default=60.0)
    ap.add_argument("--out", help="write the full response here; print only a summary (bytes, result length)")
    a = ap.parse_args()

    if a.chain not in CHAINS:
        print(f"unknown chain {a.chain!r}; one of {sorted(CHAINS)}", file=sys.stderr)
        return 2
    if a.method.startswith(REFUSED_PREFIXES):
        print(f"{a.method} refused: read-only tool", file=sys.stderr)
        return 2
    raw = open(a.params_file).read() if a.params_file else a.params
    try:
        params = json.loads(raw)
    except json.JSONDecodeError as e:
        print(f"params are not valid JSON ({e}); length {len(raw)}, tail {raw[-60:]!r}", file=sys.stderr)
        return 2
    if not isinstance(params, list):
        print("params must be a JSON array", file=sys.stderr)
        return 2
    if a.method == "eth_getLogs":
        errs = check_getlogs(params)
        if errs:
            for e in errs:
                print(f"refused before sending: {e}", file=sys.stderr)
            return 2
    base = os.environ.get("RPC_RELAY_URL")
    if not base:
        print("RPC_RELAY_URL is not set in this environment", file=sys.stderr)
        return 2
    url = f"{base.rstrip('/')}/{a.chain}?lane={a.lane}"
    body = json.dumps({"jsonrpc": "2.0", "id": 1, "method": a.method, "params": params}).encode()
    req = urllib.request.Request(url, data=body, headers={"content-type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=a.timeout) as r:
            text = r.read().decode()
    except urllib.error.HTTPError as e:
        print(e.read().decode(errors="replace") or f"HTTP {e.code}")
        return 1
    except (urllib.error.URLError, TimeoutError) as e:
        print(f"transport error: {e}", file=sys.stderr)
        return 1
    try:
        obj = json.loads(text)
    except json.JSONDecodeError:
        print(text)
        return 1
    for h in address_hints(a.chain, a.method, params, obj):
        print(f"hint: {h}", file=sys.stderr)
    if a.out and "error" not in obj:
        with open(a.out, "w") as f:
            f.write(text)
        res = obj.get("result")
        n = f"{len(res)} items" if isinstance(res, list) else f"result {str(res)[:80]!r}"
        print(f"wrote {len(text)} bytes to {a.out}: {n}")
        return 0
    print(text)
    if "error" in obj and a.method in CALL_METHODS:
        for h in revert_hints(params, obj["error"]):
            print(f"hint: {h}", file=sys.stderr)
    return 1 if "error" in obj else 0


if __name__ == "__main__":
    sys.exit(main())
