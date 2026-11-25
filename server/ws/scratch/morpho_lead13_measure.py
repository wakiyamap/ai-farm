#!/usr/bin/env python3
"""Lead 13 (base Morpho liquidations): per-occurrence gross, price-age at capture, winner gas+tip."""
import json, subprocess, sys

MORPHO = "0xbbbbbbbbbb9cc5e90e3b3af64bdaf62c37eeffcb"
SEL_PARAMS = "0x2c3c9157"
SEL_PRICE = "0xa035b1fe"
SEL_ROUND = "0xfeaf968c"
SEL_DEC = "0x313ce567"
SCALE = 10**36


def rpc(method, params, block_tag=None):
    out = subprocess.run(["python3", "tools/rpc.py", "base", method, json.dumps(params), "--lane", "research"],
                         capture_output=True, text=True, cwd="/srv/farm/ws")
    try:
        d = json.loads(out.stdout)
    except Exception:
        return {"_err": (out.stdout or out.stderr)[:160]}
    if "error" in d:
        return {"_err": str(d["error"])[:160]}
    return d["result"]


def call(to, data, blk=None):
    tx = {"to": to, "data": data}
    tag = hex(blk) if blk is not None else "latest"
    r = rpc("eth_call", [tx, tag])
    return r


def word(r, i=0):
    if not isinstance(r, str) or not r.startswith("0x") or len(r) < 66:
        return None
    return int(r[2 + i * 64: 2 + (i + 1) * 64], 16)


SAMPLE = [
    # (label, liq_block, tx, marketId, repaid_loan_units_str, seized_coll_units_str)
    ("A_11-13_wstETHish", 56758326, "0xe5cbf35b40ab0f7aa7c30652232a0b9a5505264cfaff3ce469501442199dc8e8", "0x842e13441248394cf66c5f67973d7feca59eca7458528f14690607c3a40f9b8c", "15058766640273945136279", "25377251"),
    ("B_11-13", 56730042, "0x5d3bd3f43365be1a1a5895d8ce49d9f7680bfb1f2812961dd8b51f66de0cec68", "0x0b3bdf8627442f43607716b9e20475500fd62cb91bbb2c16c711e7c31038beb8", "4227431025082401103", "1773458293670457"),
    ("C_11-14", 57502663, "0x53ba0215de1a5939c577380e75c28fa33e28ef5939070b9e6d9a463da4721e78", "0xb5d424e4af49244b074790f1f2dc9c20df948ce291fc6bcc6b59149ecf91196d", "21354344734043876", "11056623634657"),
    ("D_11-14", 57501368, "0xe7dcdd29419590a08fa731deab88ab9f9db09dde40b5913396d9bc2e1966a848", "0x0915250ea86502d8b45684d82f776766411b684fd2c6694eb4d1ec375d70e712", "9041704617673059", "23933650117685539"),
    ("E_11-16_usdc", 58015037, "0x0102c183c34f82b36e9db198c7f2090505279ce5f1a261ae7fc7d5c01121e6a8", "0xdaa04f6819210b11fe4e3b65300c725c32e55755e3598671559b9ae3bac453d7", "10481470436", "28583168159400000000000"),
    ("F_11-16_usdc", 57997287, "0x4c0799b647ec1effb919850abcaa313361e7f52f058abad27d4ddb20ac64b5fd", "0x8793cf302b8ffd655ab97bd1c695dbd967807e8367a65cb2f4edaf1380ba1bda", "349658673", "201685932159000000"),
    ("G1_11-15_peel", 56374332, "0xf1c68254b2fa683151032b2bb8c3ebbd74746057baa224dc5be8aee088dbc81c", "0x8793cf302b8ffd655ab97bd1c695dbd967807e8367a65cb2f4edaf1380ba1bda", "29604097", "15103500310158248"),
    ("G2_11-15_peel", 56377187, "0xa447f92802e0158251c581f6d7b61059a634a10bb6d64c05a8bffae534d1242e", "0x8793cf302b8ffd655ab97bd1c695dbd967807e8367a65cb2f4edaf1380ba1bda", "3092827", "1580755172977941"),
    ("G3_11-15_peel", 56381105, "0x2cd68bf996fff6527d3ed829c6e63d3e520ec90ad39866551134bdbe24a97a03", "0x8793cf302b8ffd655ab97bd1c695dbd967807e8367a65cb2f4edaf1380ba1bda", "318230", "162957203627795"),
]

dec_cache = {}


def decimals(tok):
    if tok not in dec_cache:
        r = call(tok, SEL_DEC)
        dec_cache[tok] = word(r) if isinstance(r, str) else None
    return dec_cache[tok]


res = []
for label, blk, tx, mkt, repaid_s, seized_s in SAMPLE:
    row = {"label": label, "block": blk, "tx": tx}
    p = call(MORPHO, SEL_PARAMS + mkt[2:], blk)
    if not isinstance(p, str) or len(p) < 2 + 5 * 64:
        row["err_params"] = p
        res.append(row)
        continue
    loan = "0x" + p[2 + 0 * 64: 2 + 64][-40:]
    coll = "0x" + p[2 + 1 * 64: 2 + 128][-40:]
    oracle = "0x" + p[2 + 2 * 64: 2 + 192][-40:]
    lltv = word(p, 4)
    row.update(loan=loan, coll=coll, oracle=oracle, lltv=lltv)
    ld = decimals(loan) or 18
    cd = decimals(coll) or 18
    row["loan_dec"], row["coll_dec"] = ld, cd
    pr = call(oracle, SEL_PRICE, blk)
    price = word(pr)
    row["price_at_liq_blk"] = price
    repaid = int(repaid_s)
    seized = int(seized_s)
    if price:
        val_seized_loan = seized * price // SCALE
        row["value_seized_loan_units"] = val_seized_loan
        row["repaid_loan_units"] = repaid
        row["gross_loan_units"] = val_seized_loan - repaid
        row["gross_loan_human"] = (val_seized_loan - repaid) / 10 ** ld
        row["repaid_human"] = repaid / 10 ** ld
        row["bonus_pct"] = 100.0 * (val_seized_loan - repaid) / repaid if repaid else None
    # price age: last round known strictly BEFORE the liquidation block
    rd = call(oracle, SEL_ROUND, blk - 1)
    if isinstance(rd, str) and len(rd) >= 6 + 5 * 64:
        updated_before = word(rd, 1)
        row["round_updatedAt_before_blk"] = updated_before
    else:
        row["round_err_before"] = rd
    rd2 = call(oracle, SEL_ROUND, blk)
    if isinstance(rd2, str) and len(rd2) >= 6 + 5 * 64:
        row["round_updatedAt_at_blk"] = word(rd2, 1)
    rc = rpc("eth_getTransactionReceipt", [tx])
    if isinstance(rc, dict) and rc:
        row["gasUsed"] = int(rc.get("gasUsed", "0x0"), 16)
        row["effectiveGasPrice_wei"] = int(rc.get("effectiveGasPrice", "0x0"), 16)
    bh = rpc("eth_getBlockByNumber", [hex(blk), False])
    if isinstance(bh, dict) and bh:
        row["blk_baseFee_wei"] = int(bh.get("baseFeePerGas", "0x0"), 16)
        row["blk_ts"] = int(bh.get("timestamp", "0x0"), 16)
        if row.get("round_updatedAt_before_blk"):
            row["price_age_s_before_liq"] = row["blk_ts"] - row["round_updatedAt_before_blk"]
        if row.get("round_updatedAt_at_blk"):
            row["price_age_s_at_blk"] = row["blk_ts"] - row["round_updatedAt_at_blk"]
    res.append(row)

print(json.dumps(res, indent=1))
