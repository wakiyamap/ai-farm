#!/usr/bin/env python3
"""Phase 15h text patches of rpc-relay.

  patch-15h.py check <rpc-relay>
  patch-15h.py apply <rpc-relay> <outdir>

meta (inbox/meta/2026-11-19-bsc-fork-missing-trie-node.md): a bsc fork reset to a block 4 days old
got `missing trie node` now and then, and the same call worked seconds later; once the fork went
down with `no provider available`. Cause: the fork lane's list is Alchemy, then the public nodes.
The relay keeps one cooldown per upstream URL for all lanes, so when another lane's call on bsc made
Alchemy time out or rate-limit, Alchemy was skipped for 10-30 s and the fork's read of old state went
to bsc-dataseed, which keeps recent state only and answers `missing trie node` (an error anvil does
not retry). With the public node also cooling down, nothing was left: `no provider available`.

1. Fork lane, a state read pinned to a block older than public nodes keep (is_historical): Alchemy
   only. Public nodes cannot answer it.
2. Cooldown: a fork's only archive provider, and any send (eth_sendRawTransaction, Alchemy only), are
   tried even while the URL is cooling down. Before, a burst of reads on one chain could make a live
   bot's send on that chain fail with `no provider available` for 10-30 s.
3. Fork lane: when the call failed on a rate limit, the error goes back with code 429 ("rate
   limited, retry"), which anvil's RPC client retries with backoff, instead of -32000.
Every other lane and method is unchanged.
"""
import sys

PAIRS = [
    # 1. providers: fork lane, old state -> Alchemy only
    ('''        if lane == "fork" and alchemy and spent < self.budget.get(lane, 0):
''',
     '''        if lane == "fork" and alchemy and params is not None and self.is_historical(chain, method, params):
            # 15h: a fork's old state needs an archive node; public nodes answer "missing trie node"
            return alchemy
        if lane == "fork" and alchemy and spent < self.budget.get(lane, 0):
'''),
    # 3a. remember whether the last failure was a rate limit
    ('''        last_error = "no provider available"
''',
     '''        last_error = "no provider available"
        limited = False                               # 15h: a provider answered with a rate limit
'''),
    # 2. cooldown: sends and a fork's only archive provider are tried anyway
    ('''            if self.cooldown.get(url, 0) > time.monotonic():
                continue
''',
     '''            if self.cooldown.get(url, 0) > time.monotonic() and not (
                    method in SEND_METHODS or (lane == "fork" and name == "alchemy" and not more)):
                continue                              # 15h: sends and a fork's last provider: try anyway
'''),
    # 3b. HTTP 429
    ('''                if exc.code == 429:
                    self.cooldown[url] = time.monotonic() + 10
''',
     '''                if exc.code == 429:
                    self.cooldown[url] = time.monotonic() + 10
                    limited = True                    # 15h
'''),
    # 3c. rate limit in the JSON-RPC body
    ('''                self.cooldown[url] = time.monotonic() + 10
                last_error = f"{name}: {body['error'].get('message')}"
''',
     '''                self.cooldown[url] = time.monotonic() + 10
                last_error = f"{name}: {body['error'].get('message')}"
                limited = limited or err.get("code") in (-32005, 429, -32029)    # 15h
'''),
    # 3d. fork lane: a rate limit goes back as code 429 so anvil retries
    ('''        return {"jsonrpc": "2.0", "id": req_id,
                "error": {"code": -32000, "message": f"all providers failed: {last_error}"}}
''',
     '''        if limited and lane == "fork":
            # 15h: anvil's RPC client retries code 429 with backoff; -32000 fails the fork's call
            return {"jsonrpc": "2.0", "id": req_id,
                    "error": {"code": 429, "message": f"rate limited, retry: {last_error}"}}
        return {"jsonrpc": "2.0", "id": req_id,
                "error": {"code": -32000, "message": f"all providers failed: {last_error}"}}
'''),
]


def patched(path, check_only=False):
    text = open(path, encoding="utf-8").read()
    for i, (old, new) in enumerate(PAIRS, 1):
        n = text.count(old)
        if n != 1:
            sys.exit(f"{path}: patch {i} matches {n} times (expected 1); nothing was changed")
        if not check_only:
            text = text.replace(old, new)
    return text


def main():
    a = sys.argv
    if len(a) == 3 and a[1] == "check":
        patched(a[2], True)
        return print(f"  rpc-relay: {len(PAIRS)} patches match")
    if len(a) == 4 and a[1] == "apply":
        with open(f"{a[3]}/rpc-relay", "w", encoding="utf-8") as f:
            f.write(patched(a[2]))
        return print(f"  patched copy written to {a[3]}")
    sys.exit(__doc__)


if __name__ == "__main__":
    main()
