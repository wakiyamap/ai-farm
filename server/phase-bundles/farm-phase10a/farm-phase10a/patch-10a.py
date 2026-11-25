#!/usr/bin/env python3
"""Phase 10a: exact-text patches for the installed fork CLI, farm.nft, common.md and ledger-ingest.

  patch-10a.py check <fork> <farm.nft> <common.md> <ledger-ingest>
  patch-10a.py apply <fork> <farm.nft> <common.md> <ledger-ingest> <outdir>

Every old text must occur exactly once, or nothing is written. Safe to re-run (markers).
"""
import os
import sys

FORK = [
("five new fork ports 9004-9008",
'''PORTS = {"base": 9001, "arbitrum": 9002, "ethereum": 9003, "ethereum-review": 9013}
''',
'''PORTS = {"base": 9001, "arbitrum": 9002, "ethereum": 9003, "ethereum-review": 9013,
         "bsc": 9004, "polygon": 9005, "avalanche": 9006, "optimism": 9007, "hyperevm": 9008}   # 10a
''',
'"hyperevm": 9008}'),
("help lists the new chains",
'''  (chains: base | arbitrum | ethereum | ethereum-review — the last is the paper-reviewer's own
   ethereum fork, unreachable from the earner and the bots)
''',
'''  (chains: base | arbitrum | ethereum | bsc | polygon | avalanche | optimism | hyperevm |
   ethereum-review — the last is the paper-reviewer's own ethereum fork, unreachable from the
   earner and the bots. `fund` sets the chain's native token: BNB, POL, AVAX, ETH or HYPE)
''',
"optimism | hyperevm |\n   ethereum-review"),
]

NFT = [
("comment: fork ports 9001-9008",
"# 9001-9003 (fork nodes),",
"# 9001-9008 (fork nodes),",
"# 9001-9008 (fork nodes),"),
("earner may reach forks 9001-9008",
"8545, 9001-9003, 29483 }",
"8545, 9001-9008, 29483 }",
"8545, 9001-9008, 29483 }"),
("bots may reach forks 9001-9008",
"{ 53, 8545, 9001-9003 }",
"{ 53, 8545, 9001-9008 }",
"{ 53, 8545, 9001-9008 }"),
]

COMMON = [
("eight chains, and what is different on the five new ones",
'''The chains are the **real public mainnets**: Base (chain id 8453), Arbitrum One (42161), Ethereum (1). Nothing is simulated or forked.''',
'''The chains are the **real public mainnets**: Base (chain id 8453), Arbitrum One (42161), Ethereum (1), BNB Smart Chain (56), Polygon PoS (137), Avalanche C-Chain (43114), OP Mainnet (10) and HyperEVM (999). Nothing is simulated or forked.''',
"BNB Smart Chain (56)"),
("new-chain paragraph",
'''"The farm" names this system (its relay, ledger, KB, bots), never a chain.
''',
'''"The farm" names this system (its relay, ledger, KB, bots), never a chain.

Their farm names (relay path, `fork`, `kb` and ledger `chain` values) are `base`, `arbitrum`, `ethereum`, `bsc`, `polygon`, `avalanche`, `optimism`, `hyperevm`. The last five were added on 2026-11-10: reads, the ledger, the KB and forks work on them, but **the gate cannot fund or promote a bot there yet** and refuses such a manifest. Research, build and paper-test there; promotion follows once the human extends the money path (the KB and decisions will say so). Differences that bite: USDC on BNB Smart Chain has **18 decimals**, not 6; Alchemy serves no `trace_*` methods on Polygon and HyperEVM; the public BNB node does not answer `eth_getLogs`, so log scans there fall back to Alchemy and cost quota; OP Mainnet is an OP Stack chain like Base (see L). Native tokens: BNB, POL (formerly MATIC), AVAX, ETH (OP Mainnet), HYPE.
''',
"Their farm names (relay path"),
]

LEDGER = [
("docstring: chains come from the config",
'''"""Ledger ingest: pull selected events from the three chains into ledger.db.
''',
'''"""Ledger ingest: pull selected events from the farm's chains (ledger.json blocks_per_call) into ledger.db.
''',
"from the farm's chains (ledger.json"),
("heads: only chains a source uses; an unreadable head skips that chain for this run",
'''    heads = {chain: int(rpc.call(chain, "eth_blockNumber", []), 16) for chain in cfg["blocks_per_call"]}
''',
'''    # Only chains some source uses, and one unreadable head skips that chain for this run instead of
    # failing the whole run (10a: eight chains, any public node can be down).
    heads = {}
    for chain in sorted({c for s in seed + agent for c in s["chains"]}):
        try:
            heads[chain] = int(rpc.call(chain, "eth_blockNumber", []), 16)
        except (OSError, RuntimeError, ValueError) as exc:
            stats["errors"].append(f"{chain} head unreadable: {exc}")
''',
"one unreadable head skips that chain"),
("ingest_source skips a chain without a head",
'''    for chain, addrs in s["chains"].items():
        head = heads[chain] - cfg["confirmations"]
''',
'''    for chain, addrs in s["chains"].items():
        if chain not in heads:
            continue                                  # head unreadable this run (runs.note says why)
        head = heads[chain] - cfg["confirmations"]
''',
"if chain not in heads:"),
]

FILES = [("fork", FORK), ("farm.nft", NFT), ("common.md", COMMON), ("ledger-ingest", LEDGER)]


def patch(text, hunks, name):
    for title, old, new, marker in hunks:
        if marker in text:
            print(f"  {name}: already applied: {title}")
            continue
        n = text.count(old)
        if n != 1:
            raise SystemExit(f"{name}: cannot apply '{title}': old text found {n} times (expected 1); "
                             "nothing was changed")
        text = text.replace(old, new)
        print(f"  {name}: applied: {title}")
    return text


def main(argv):
    if len(argv) == 5 and argv[0] == "check":
        out = None
    elif len(argv) == 6 and argv[0] == "apply":
        out = argv[5]
    else:
        sys.exit(__doc__)
    results = []
    for path, (name, hunks) in zip(argv[1:5], FILES):
        with open(path, encoding="utf-8") as f:
            results.append((name, patch(f.read(), hunks, name)))
    if out:
        for name, text in results:
            with open(os.path.join(out, name), "w", encoding="utf-8") as f:
                f.write(text)


if __name__ == "__main__":
    main(sys.argv[1:])
