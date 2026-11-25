#!/usr/bin/env python3
"""Sample measurement for lead 57 (Revert Lend V3Vault liquidations, Arbitrum)."""
import json, subprocess, statistics

VAULT = "0x74e6afef5705beb126c6d3bf46f8fad8f3e07825"
RPC = ["python3", "/srv/farm/ws/tools/rpc.py", "arbitrum"]
LOANINFO = "0x8349d6be"

# (label, tx, block E, tokenId, cost_event_usd)
EVENTS = [
    ("A-top1", "0x242a4d38b263a2719d9994b52e86b015453fafd63fce38438b44d1eb7efda0a9", 523760363, 5767191, 21624.08),
    ("B-top2", "0x88d136d02930fc17778c68df3d72d03c163bae752034a37fc4bff52be42e3d1b", 524319842, 5728891, 3822.21),
    ("C-top3", "0x5d197140d8dafb03c8c894100a46159a3f1811b77f08aa5cddb41c03299f9079", 523752838, 5769084, 1585.93),
    ("D-top4", "0x17e1c5b3098a9776bfc0c08450de9e51e794171c6a692a889fb1550dabb6e76f", 524280420, 5773833, 1527.05),
    ("E-top5", "0xfa9ee5503591eef88a17deeb22cf51705a9d1cd67d560769bc58211e47eaff5a", 523020368, 5729334, 894.46),
    ("F-latest", "0xfe6fedf39f345a61f6fd781241d2a604d8fc53a73d929efc344329aa68d13721", 524327778, 5751116, 7.76),
    ("G-smallest", "0x58b85144844f313a0edb92e734a897fcda127e7d4a286c1454959be6c59a552b", 522990116, 5667601, 0.58),
    ("H-mid", "0x089350e7d83f14546386e115bf139fb8cd11f68e0e13c9ac07fe8ff16cec3879", 523752956, 5742484, 28.62),
    ("I-mid", "0x4f2faac78e30a1aa9dec5f2373f0e43bfc5d123bee88135da5c58aaba3ea4bc1", 523980894, 5606769, 10.75),
    ("J-mid", "0xdb4f148216bbf07567b63a6d105c57de326f6522f1565ec6c6d91e35d964876a", 522990277, 5700143, 20.60),
]

def rpc(method, params):
    r = subprocess.run(RPC + [method, json.dumps(params), "--lane", "research"],
                       capture_output=True, text=True)
    out = json.loads(r.stdout)
    if "error" in out:
        return None
    return out["result"]

def loaninfo(tok, block):
    data = LOANINFO + hex(tok)[2:].rjust(64, "0")
    res = rpc("eth_call", [{"to": VAULT, "data": data}, hex(block)])
    if not res:
        return None
    res = res[2:] if res.startswith("0x") else res
    w = [res[i:i+64] for i in range(0, len(res), 64)]
    vals = [int(x, 16) for x in w]
    # (isHealthy, fullValue, collateralValue, liquidationCost, liquidationValue)
    return {"healthy": vals[0] == 1, "fullValue": vals[1], "collateralValue": vals[2],
            "liqCost": vals[3], "liqValue": vals[4]}

rows = []
for label, tx, E, tok, cost in EVENTS:
    # backward scan for takeable block
    steps = [2, 3, 4, 6, 8, 12, 20, 32]
    takeable = None
    li_prev = None
    li = loaninfo(tok, E - 1)
    if li and li["healthy"]:
        takeable = E  # crossed exactly in capture block
        li_at = None
    else:
        li_at = li  # E-1 state (last pre-capture) -> gross
        last_liq = E - 1
        for s in steps:
            li2 = loaninfo(tok, E - s)
            if li2 is None:
                break
            if li2["healthy"]:
                takeable = last_liq  # first known-liquidatable block
                break
            last_liq = E - s
        else:
            takeable = None
        if takeable is None and li is not None:
            takeable = E - 32  # floor; still liquidatable 32 blocks back
    # receipt + base fee
    rec = rpc("eth_getTransactionReceipt", [tx])
    blk = rpc("eth_getBlockByNumber", [hex(E), False])
    prio = None; gas_used = None; gas_usd = None
    if rec and blk:
        eff = int(rec["effectiveGasPrice"], 16)
        base = int(blk["baseFeePerGas"], 16)
        prio = eff - base
        gas_used = int(rec["gasUsed"], 16)
    rows.append({"label": label, "tok": tok, "E": E, "takeable": takeable,
                 "blocks_takeable_to_taken": (E - takeable) if takeable else None,
                 "liqValue_minus_cost_usd": (round((li_at["liqValue"] - li_at["liqCost"]) / 1e6, 2) if li_at else None),
                 "liqCost_Eminus1_usd": (round(li_at["liqCost"] / 1e6, 2) if li_at else None),
                 "healthy_Eminus1": (li["healthy"] if li else None),
                 "prio_fee_gwei": (round(prio / 1e9, 4) if prio is not None else None),
                 "gas_used": gas_used, "taker": (rec["from"] if rec else None)})
    print(json.dumps(rows[-1]))

# medians
def med(key):
    vals = [r[key] for r in rows if r[key] is not None]
    return round(statistics.median(vals), 4) if vals else None
print("MEDIAN blocks_takeable_to_taken:", med("blocks_takeable_to_taken"))
print("MEDIAN prio_fee_gwei:", med("prio_fee_gwei"))
print("MEDIAN gross_usd:", med("liqValue_minus_cost_usd"))
