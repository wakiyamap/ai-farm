#!/usr/bin/env python3
"""Phase 12b text patches: a private send route (Flashbots Protect, ethereum only).

  patch-12b.py check <rpc-relay> <farm-signer>          every old text occurs exactly once
  patch-12b.py apply <rpc-relay> <farm-signer> <outdir> write patched copies into <outdir>

rpc-relay: relay.json "private_send" {chain: url}; on the farmgate send socket a request with
  ?route=private goes to that url and nowhere else (no fallback to Alchemy or a public node:
  a transaction meant to stay private must never be published because the private route failed).
farm-signer: a bot whose manifest says `send_route: private` is sent through that route on the
  chains in gate.json "private_send_chains" (default ["ethereum"]); every other chain and every
  other bot goes out as before. The policy checks are unchanged. signer.log records the route.
"""
import sys

RELAY = [
    ("""        self.key = alchemy_key
""",
     """        self.key = alchemy_key
        self.private_send = config.get("private_send") or {}   # chain -> url (12b)
"""),
    ("""    def providers(self, chain, lane, method="", params=None):
""",
     """    def providers(self, chain, lane, method="", params=None, route=None):
"""),
    ("""        if method in SEND_METHODS:
            # Transactions go to Alchemy only (private/MEV-protected submission on Ethereum;
            # no reason to show calldata to a public node anywhere). No Alchemy = no broadcast.
            return alchemy
""",
     """        if method in SEND_METHODS:
            if route == "private":
                # 12b: the private route and nothing else. No fallback: a transaction meant to
                # stay out of the public mempool is dropped, never published, when this fails.
                url = self.private_send.get(chain)
                return [("private", url)] if url else []
            # Public sends go to Alchemy only (no reason to show calldata to a public node
            # anywhere). No Alchemy = no broadcast.
            return alchemy
"""),
    ("""    def call(self, chain, lane, method, params, req_id, allow_send=False):
        if method in SEND_METHODS and allow_send:
            pass
""",
     """    def call(self, chain, lane, method, params, req_id, allow_send=False, route=None):
        if method in SEND_METHODS and allow_send:
            if route not in (None, "private"):
                return {"jsonrpc": "2.0", "id": req_id,
                        "error": {"code": -32602, "message": f"unknown send route {route!r}; nothing was sent"}}
            if route == "private" and not self.private_send.get(chain):
                self.stats.record(chain, lane, "private", "refused", 0, 0)
                return {"jsonrpc": "2.0", "id": req_id,
                        "error": {"code": -32000,
                                  "message": f"no private send route for {chain}; nothing was sent"}}
"""),
    ("""        provs = self.providers(chain, lane, method, params)
""",
     """        provs = self.providers(chain, lane, method, params, route)
"""),
    ("""        lane = urllib.parse.parse_qs(parsed.query).get("lane", ["research"])[0]
""",
     """        lane = urllib.parse.parse_qs(parsed.query).get("lane", ["research"])[0]
        route = urllib.parse.parse_qs(parsed.query).get("route", [None])[0]   # send socket only (12b)
"""),
    ("""                                       allow_send=self.allow_send))
""",
     """                                       allow_send=self.allow_send,
                                       route=route if self.allow_send else None))
"""),
]

SIGNER = [
    ("""    def call(self, chain, method, params, lane="live"):
        body = json.dumps({"jsonrpc": "2.0", "id": 1, "method": method, "params": params}).encode()
        if method == "eth_sendRawTransaction":
            out = self._unix(f"/{chain}?lane={lane}", body)
""",
     """    def call(self, chain, method, params, lane="live", route=None):
        body = json.dumps({"jsonrpc": "2.0", "id": 1, "method": method, "params": params}).encode()
        if method == "eth_sendRawTransaction":
            out = self._unix(f"/{chain}?lane={lane}" + ("&route=private" if route == "private" else ""), body)
"""),
    ("""        # executor contracts deployed by the gate are always callable
""",
     """        # 12b: `send_route: private` keeps this bot's transactions out of the public mempool on
        # the chains that have a private route. The live manifest is read-only: the reviewer saw it.
        sr = manifest_list(text, "send_route")
        m["send_route"] = sr[0].lower() if sr else "public"
        # executor contracts deployed by the gate are always callable
"""),
    ("""            chain = req["chain"]
            nonce = int(self.rpc.call(chain, "eth_getTransactionCount", [addr, "pending"]), 16)
""",
     """            chain = req["chain"]
            if m.get("send_route") not in ("public", "private"):
                why = f"manifest send_route {m.get('send_route')!r} is neither public nor private"
                log(bot=bot_id, op="send", decision="reject", why=why, chain=chain, to=req.get("to"))
                return {"ok": False, "error": why}
            # A private transaction is invisible to the node until it is mined, so "pending" is the
            # mined nonce: a second private send before the first is mined reuses its nonce and
            # replaces it. At most one of the two can ever be mined.
            route = ("private" if m["send_route"] == "private"
                     and chain in self.cfg.get("private_send_chains", ["ethereum"]) else None)
            nonce = int(self.rpc.call(chain, "eth_getTransactionCount", [addr, "pending"]), 16)
"""),
    ("""                h = self.rpc.call(chain, "eth_sendRawTransaction", ["0x" + raw.hex()])
""",
     """                h = self.rpc.call(chain, "eth_sendRawTransaction", ["0x" + raw.hex()], route=route)
"""),
    ("""                log(bot=bot_id, op="send", decision="broadcast_failed", why=str(exc) or repr(exc), chain=chain, nonce=nonce)
""",
     """                log(bot=bot_id, op="send", decision="broadcast_failed", why=str(exc) or repr(exc), chain=chain, nonce=nonce,
                    route=route or "public")
"""),
    ("""            log(bot=bot_id, op="send", decision="sent", chain=chain, nonce=nonce, to=req["to"], txHash=h, worst_usd=round(worst, 4))
            return {"ok": True, "txHash": h, "nonce": nonce}
""",
     """            log(bot=bot_id, op="send", decision="sent", chain=chain, nonce=nonce, to=req["to"], txHash=h, worst_usd=round(worst, 4),
                route=route or "public")
            return {"ok": True, "txHash": h, "nonce": nonce, "route": route or "public"}
"""),
]


def patched(path, pairs, check_only=False):
    text = open(path, encoding="utf-8").read()
    for i, (old, new) in enumerate(pairs, 1):
        n = text.count(old)
        if n != 1:
            sys.exit(f"{path}: patch {i} matches {n} times (expected 1); nothing was changed")
        if not check_only:
            text = text.replace(old, new)
    return text


def main():
    if len(sys.argv) < 4 or sys.argv[1] not in ("check", "apply"):
        sys.exit(__doc__)
    relay, signer = sys.argv[2], sys.argv[3]
    if sys.argv[1] == "check":
        patched(relay, RELAY, True)
        patched(signer, SIGNER, True)
        print(f"  rpc-relay: {len(RELAY)} patches match, farm-signer: {len(SIGNER)} patches match")
        return
    out = sys.argv[4]
    for path, pairs, name in ((relay, RELAY, "rpc-relay"), (signer, SIGNER, "farm-signer")):
        with open(f"{out}/{name}", "w", encoding="utf-8") as f:
            f.write(patched(path, pairs))
    print(f"  patched copies written to {out}")


if __name__ == "__main__":
    main()
