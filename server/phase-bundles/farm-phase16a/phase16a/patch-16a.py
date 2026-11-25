#!/usr/bin/env python3
"""Phase 16a: Stellar, read only. Patches four files in place by exact string match.

  patch-16a.py <rpc-relay> <scout-enum> <context-scout> <scout.md>

Every replacement must match exactly once, or nothing is written for that file and the script exits 1.
- rpc-relay: a non-EVM chain section (relay.json "nonevm_chains"), Stellar RPC read methods only,
  only the lanes the chain lists (research, scout, paper), never a send; /health keeps "chains"
  EVM-only and adds "nonevm_chains".
- scout-enum: DefiLlama "Stellar" -> chain "stellar", queued at tier 2 (ahead of other protocols).
- context-scout: Stellar steps for protocol candidates on chain "stellar".
- scout.md: a short Stellar section (reads through the relay with curl, strkeys, require_auth).
"""
import sys

STELLAR_CU = '''DEFAULT_CU = 30

# 16a: Stellar RPC (JSON-RPC, object params). Read methods only: no sendTransaction anywhere.
# simulateTransaction only simulates (nothing is submitted). CU guesses: Alchemy publishes no
# Stellar table we rely on; the human reconciles against the dashboard as for the EVM chains.
STELLAR_CU = {
    "getHealth": 0, "getNetwork": 0, "getVersionInfo": 0, "getLatestLedger": 10, "getFeeStats": 10,
    "getLedgers": 30, "getLedgerEntries": 30, "getTransaction": 20, "getTransactions": 40,
    "getEvents": 60, "simulateTransaction": 40,
}
NONEVM_LANES = ("research", "scout", "paper")   # default when a non-EVM chain lists no "lanes"
'''

RELAY = [
    ("DEFAULT_CU = 30\n", STELLAR_CU),
    ('        self.chains = config["chains"]                  # name -> {"alchemy": slug, "public": [urls]}\n',
     '        self.chains = dict(config["chains"])            # name -> {"alchemy": slug, "public": [urls]}\n'
     '        self.nonevm = config.get("nonevm_chains") or {}  # 16a: stellar; own method list, read only\n'
     '        self.chains.update(self.nonevm)\n'),
    ('    def call(self, chain, lane, method, params, req_id, allow_send=False, route=None):\n'
     '        if method in SEND_METHODS and allow_send:\n',
     '    def call(self, chain, lane, method, params, req_id, allow_send=False, route=None):\n'
     '        if chain in self.nonevm and (method not in STELLAR_CU\n'
     '                                     or lane not in self.nonevm[chain].get("lanes", NONEVM_LANES)):\n'
     '            # 16a: a non-EVM chain is read only, on its listed lanes, send socket included\n'
     '            self.stats.record(chain, lane, "none", "refused", 0, 0)\n'
     '            return {"jsonrpc": "2.0", "id": req_id,\n'
     '                    "error": {"code": -32601, "message": f"{method} on lane {lane} is not allowed for {chain} "\n'
     '                              f"(read only: {sorted(STELLAR_CU)}; lanes "\n'
     '                              f"{list(self.nonevm[chain].get(\'lanes\', NONEVM_LANES))})"}}\n'
     '        if method in SEND_METHODS and allow_send and chain not in self.nonevm:\n'),
    ('        elif method not in ALLOWED_METHODS:\n',
     '        elif chain not in self.nonevm and method not in ALLOWED_METHODS:\n'),
    ('        cu = CU.get(method, DEFAULT_CU)\n',
     '        cu = CU.get(method, STELLAR_CU.get(method, DEFAULT_CU))\n'),
    ('        payload = json.dumps({"jsonrpc": "2.0", "id": 1, "method": method, "params": params}).encode()\n',
     '        req_body = {"jsonrpc": "2.0", "id": 1, "method": method, "params": params}\n'
     '        if chain in self.nonevm and params in (None, [], {}):\n'
     '            req_body.pop("params")       # 16a: Stellar RPC refuses a list (the relay\'s default) and wants none\n'
     '        payload = json.dumps(req_body).encode()\n'),
    ('"budget": self.relay.budget, "chains": sorted(self.relay.chains),\n',
     '"budget": self.relay.budget,\n'
     '                                 "chains": sorted(c for c in self.relay.chains if c not in self.relay.nonevm),\n'
     '                                 "nonevm_chains": sorted(self.relay.nonevm),\n'),
]

ENUM = [
    ('                "Hyperliquid L1": "hyperevm", "HyperEVM": "hyperevm"}\n',
     '                "Hyperliquid L1": "hyperevm", "HyperEVM": "hyperevm",\n'
     '                "Stellar": "stellar"}                     # 16a: read only, through the relay\n'
     'FIRST = {"stellar"}                                     # 16a: queued at tier 2, ahead of other protocols\n'),
    ('            tier = 3 if chain in CHEAP else 4\n',
     '            tier = 2 if chain in FIRST else 3 if chain in CHEAP else 4\n'),
]

STELLAR_STEPS = '''

# 16a: Stellar (Soroban) is read through the relay with curl; no rpc.py, no explorer, no cast.
RELAY = "curl -s -X POST 'http://127.0.0.1:8545/stellar' -H 'Content-Type: application/json' -d"
STELLAR_STEPS = {
"protocol": """Stellar is not EVM. Read the scout.md section "Stellar" first. Every chain read: """ + RELAY + """ '<json-rpc body>'.
1. Contracts: Soroban contract ids are strkeys starting with C (56 characters), accounts start with G. Take them from the DefiLlama adapter (`curl -s https://raw.githubusercontent.com/DefiLlama/DefiLlama-Adapters/main/projects/{slug}/index.js`; if 404, `curl -s https://api.llama.fi/protocol/{slug} | jq '.github, .url'`), the protocol's docs or GitHub (deployment json files). Confirm each id answers: `getLedgerEntries` of its instance, or `getEvents` with that contractId returning events.
2. Source: the protocol's GitHub (Rust, `#[contractimpl]`). A function that calls `require_auth()` on an admin, owner, manager or keeper address is role_gated; one that calls `require_auth()` only on the caller's own address, or none, is callable by anyone.
3. Look for functions anyone can call that pay the caller: reward, bounty, keeper fee, harvest, compound, rebalance, distribute, epoch or round advance, auction create / fill / bid, redemption. Liquidations are recorded but the farm does not build them now.
4. For each: its events over the last 7 days with `getEvents` (startLedger = latest minus about 120,000 ledgers, checked with `getLedgers` close times; filters [{{"type":"contract","contractIds":["C..."]}}], "xdrFormat":"json", pagination limit 100, follow the cursor at most 10 pages). Write the count, the distinct callers, what one call pays (gross USD, at most 5 sample calls via `getTransaction`) and the fee per call (stroops, 1 XLM = 10^7 stroops, XLM price from coins.llama.fi `coingecko:stellar` + time).
5. Verdict: pays_strangers / unpaid / role_gated / no_reward / not_found / unclear, as for EVM. If the KB refuses chain `stellar`, write chain `any` and start `target` with `stellar `.""",
}
'''

CTX = [
    ('\n\ndef take():\n', STELLAR_STEPS + '\n\ndef take():\n'),
    ('steps = item.get("steps") or STEPS.get(item["kind"], "Measure what the candidate describes; write numbers and a verdict.")\n',
     'steps = item.get("steps") or STEPS.get(item["kind"], "Measure what the candidate describes; write numbers and a verdict.")\n'
     'if not item.get("steps") and item.get("chain") == "stellar":\n'
     '    steps = STELLAR_STEPS.get(item["kind"], steps)    # 16a\n'),
]

SCOUT_MD = [
    ('## What to write\n',
     '''## Stellar (16a, read only)

- Stellar is not EVM: no `rpc.py`, `explorer`, `cast`, `eth_*`. Read through the relay: `curl -s -X POST 'http://127.0.0.1:8545/stellar' -H 'Content-Type: application/json' -d '{"jsonrpc":"2.0","id":1,"method":"getLatestLedger"}'`. This curl to the relay is the one allowed exception to "never curl a node". Methods: getLatestLedger, getLedgers, getLedgerEntries, getEvents, getTransaction, getTransactions, getFeeStats, simulateTransaction (simulates only). `params` is a JSON object, not a list.
- History is about 7 days (about 120,000 ledgers of 5-6 s): a 7-day window starts at a ledger whose close time you checked with `getLedgers`. Older ledgers return an error, which is not a zero.
- Ids are strkeys: contracts `C...`, accounts `G...`, 56 characters. Never from memory.
- Access control is `require_auth()` in the Rust source: on an admin / manager / keeper address = role_gated.
- Fees are in stroops (10^7 per XLM). Price XLM from `coins.llama.fi` (`coingecko:stellar`) with its time.
- A zero needs a control here too: the same `getEvents` shape returning events for a known-active contract.

## What to write
'''),
]


def apply(path, reps):
    text = open(path, encoding="utf-8").read()
    for old, new in reps:
        n = text.count(old)
        if n != 1:
            print(f"{path}: expected 1 match, found {n}: {old[:70]!r}", file=sys.stderr)
            return False
        text = text.replace(old, new)
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)
    print(f"  {path}: {len(reps)} replacements")
    return True


if __name__ == "__main__":
    if len(sys.argv) != 5:
        sys.exit(__doc__)
    ok = all([apply(sys.argv[1], RELAY), apply(sys.argv[2], ENUM),
              apply(sys.argv[3], CTX), apply(sys.argv[4], SCOUT_MD)])
    sys.exit(0 if ok else 1)
