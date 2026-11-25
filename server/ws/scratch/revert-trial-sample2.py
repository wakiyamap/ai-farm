#!/usr/bin/env python3
"""Corrected scan: liquidatable <=> word3 (liquidationCost) > 0.
Layout (from deployed ABI, 5 uints): (word0, fullValue?, word2, liqCost, liqValue)."""
import json, subprocess, statistics

VAULT = "0x74e6afef5705beb126c6d3bf46f8fad8f3e07825"
RPC = ["python3", "/srv/farm/ws/tools/rpc.py", "arbitrum"]
LOANINFO = "0x8349d6be"

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
    return out.get("result") if "error" not in out else None

def liq_state(tok, block):
    data = LOANINFO + hex(tok)[2:].rjust(64, "0")
    res = rpc("eth_call", [{"to": VAULT, "data": data}, hex(block)])
    if not res:
        return None
    res = res[2:]
    vals = [int(res[i:i+64], 16) for i in range(0, len(res), 64)]
    if len(vals) < 5:
        return None
    return {"w0": vals[0], "fv": vals[1], "w2": vals[2], "cost": vals[3], "val": vals[4],
            "liquidatable": vals[3] > 0}

rows = []
for label, tx, E, tok, cost_ev in EVENTS:
    li = liq_state(tok, E - 1)
    if li is None:
        # token may not exist at E-1 (minted in E?) — record and skip
        rows.append({"label": label, "err": "no-state-E-1"})
        print(json.dumps(rows[-1])); continue
    if not li["liquidatable"]:
        takeable, blocks = E, 0
        li_at = None
    else:
        li_at = li
        last_liq = E - 1
        takeable = None
        for s in [2, 3, 4, 6, 8, 12, 16, 24, 32]:
            li2 = liq_state(tok, E - s)
            if li2 is None:
                takeable = last_liq; break
            if not li2["liquidatable"]:
                takeable = last_liq; break
            last_liq = E - s
        else:
            takeable = last_liq  # floor (>=)
        blocks = E - takeable
    rec = rpc("eth_getTransactionReceipt", [tx])
    blk = rpc("eth_getBlockByNumber", [hex(E), False])
    prio = eff = None
    if rec and blk:
        eff = int(rec["effectiveGasPrice"], 16)
        prio = (eff - int(blk["baseFeePerGas"], 16)) / 1e9
    gross = None
    if li_at:
        gross = (li_at["val"] - li_at["cost"]) / 1e6
    gross_lb = cost_ev * 0.02 if gross is None else gross
    rows.append({"label": label, "taker": rec["from"] if rec else None,
                 "blocks_take_to_taken": blocks,
                 "gross_Eminus1_usd": round(gross, 2) if gross is not None else None,
                 "gross_lb_usd": round(gross_lb, 2),
                 "liqCost_Eminus1": round(li["cost"] / 1e6, 2),
                 "liq_val_Eminus1": round(li["val"] / 1e6, 2),
                 "penalty_pct_Eminus1": round((li["val"] / li["cost"] - 1) * 100, 2) if li["cost"] else None,
                 "gas_used": int(rec["gasUsed"], 16) if rec else None,
                 "eff_gas_price_gwei": round(eff / 1e9, 4) if eff else None,
                 "prio_gwei": round(prio, 4) if prio is not None else None})
    print(json.dumps(rows[-1]))

ok = [r for r in rows if "err" not in r]
def med(key):
    vals = [r[key] for r in ok if r[key] is not None]
    return round(statistics.median(vals), 4) if vals else None
print("MEDIAN blocks_take_to_taken:", med("blocks_take_to_taken"))
print("MEDIAN prio_gwei:", med("prio_gwei"))
print("MEDIAN gross_lb_usd:", med("gross_lb_usd"))
print("N:", len(ok))
