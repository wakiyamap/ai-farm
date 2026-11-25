#!/usr/bin/env python3
"""Lead 42 closure: fork-probe the aave v4 Base liquidation window + bonus params.

For each of the five 14 d LiquidationCall captures (attempt 346), reset the shared
Base fork to E-offset for the ladder offsets and read getUserAccountData(user).
healthFactor. liquidatable <=> HF < 1e18 (LiquidationLogic.HEALTH_FACTOR_LIQUIDATION_THRESHOLD=1e18).
Window question: did the position cross HF<1 at least ~64 blocks before its capture
(poll-catchable) or only inside the capture block (race -> blocked_infra per the
2026-11-06 no-latency decision)?

Run under a fork lease: fork lease base 15 ... ; fork release base when done.
"""
import json, subprocess, sys

SPOKE = "0x17905db0e4a3514467539956c084180616ae7b8d"
WAD = 10**18
SEL_HF = "0xbf92857c"           # getUserAccountData(address)
SEL_BONUS = "0x46fbf741"        # getLiquidationBonus(uint256,address,uint256)
SEL_CFG = "0xe0fd5c5c"          # getLiquidationConfig()
SEL_RES = "0x77778db3"          # getReserve(uint256)

EVENTS = [
    # (capture block, collateralReserveId, user, debtAmountRestored(USDC 6dp), collateralAmountRemoved)
    (53550168, 6, "0xb8cd2cc5b8ce8d6a3ec43f998528a5209a9f7e8d"),
    (53550614, 5, "0x41dc9b870fd51d5b8030bd8b3aacb0778e8b1604"),
    (53552255, 6, "0xa2d8f64ca3c14a5801cdf2a8fee51a82d0a3741d"),
    (53612209, 5, "0x69efac17fb7ae0da656db4aeab130339cdfc05d0"),
    (53652038, 4, "0x80bc92a163c227b99883d285f9d1b42e98d12c1e"),
]
# event log data words (10): w0 liquidator, w2 debtAmountRestored, w7 collateralAmountRemoved
LOG_DATA = {  # from scratch/aave4-liq14d.json, re-extracted below from the file
}

def load_log_fields():
    logs = json.load(open("scratch/aave4-liq14d.json"))
    out = {}
    for lo in logs:
        blk = int(lo["blockNumber"], 16)
        d = lo["data"][2:]
        w = [d[i:i+64] for i in range(0, len(d), 64)]
        out[blk] = (int(w[2], 16), int(w[7], 16), int(w[9], 16))  # debtRestored, collRemoved, collToLiquidator
    return out

def fork(*args):
    r = subprocess.run(["fork", *args], capture_output=True, text=True)
    if r.returncode != 0:
        raise SystemExit(f"fork {' '.join(args)} failed rc={r.returncode}: {r.stderr.strip()[:200]}")
    return r.stdout

def call(tx):
    out = fork("call", "base", json.dumps(tx))
    return out.strip()

def hf_of(user):
    data = SEL_HF + user[2:].lower().rjust(64, "0")
    ret = call({"from": "0x5ac9bc14376bf2727c6211960cf3cec1e2f295bd", "to": SPOKE, "data": data})
    ret = ret.removeprefix("0x").removeprefix("0X")
    w = [ret[i:i+64] for i in range(0, len(ret), 64)]
    # UserAccountData memory: [riskPremium, avgCollateralFactor, healthFactor, totalCollateralValue, totalDebtValueRay, activeCollateralCount, borrowCount]
    return int(w[2], 16)

def bonus(reserveId, user, hf):
    data = SEL_BONUS + hex(reserveId)[2:].rjust(64, "0") + user[2:].lower().rjust(64, "0") + hex(hf)[2:].rjust(64, "0")
    ret = call({"from": "0x5ac9bc14376bf2727c6211960cf3cec1e2f295bd", "to": SPOKE, "data": data}).removeprefix("0x")
    return int(ret, 16)

def main():
    fields = load_log_fields()
    out = open("scratch/aave4-window.json", "w")
    # reserve identities at the fork default block
    ident = {}
    for rid in (4, 5, 6):
        data = SEL_RES + hex(rid)[2:].rjust(64, "0")
        ret = call({"from": "0x5ac9bc14376bf2727c6211960cf3cec1e2f295bd", "to": SPOKE, "data": data}).removeprefix("0x")
        w = [ret[i:i+64] for i in range(0, len(ret), 64)]
        # memory struct: offset, underlying, hub, assetId, decimals, collateralRisk, flags, dynamicConfigKey
        ident[rid] = {"underlying": "0x"+w[1][-40:], "decimals": int(w[4], 16)}
    # liquidation config at the current fork block
    ret = call({"from": "0x5ac9bc14376bf2727c6211960cf3cec1e2f295bd", "to": SPOKE, "data": SEL_CFG}).removeprefix("0x")
    w = [ret[i:i+64] for i in range(0, len(ret), 64)]
    cfg = {"targetHealthFactor": int(w[0], 16), "healthFactorForMaxBonus": int(w[1], 16), "liquidationBonusFactor": int(w[2], 16)}
    result = {"spoke": SPOKE, "reserve_identity": ident, "liquidation_config": cfg, "events": []}
    for (blk, rid, user) in EVENTS:
        row = {"block": blk, "reserve": rid, "user": user, "hf": {}, "cross": None,
               "debtRestored_usdc": fields[blk][0]/1e6}
        ladder = [1, 2, 4, 8, 16, 32, 64, 128]
        for o in ladder:
            fork("reset", "base", str(blk - o))
            hf = hf_of(user)
            row["hf"][o] = hf
            if hf < WAD:
                row["cross"] = o   # latest known liquidatable offset (smallest o is E-1)
                if o >= 64:
                    break
        # bonus at the E-1 HF
        fork("reset", "base", str(blk - 1))
        hf1 = row["hf"].get(1, hf_of(user))
        try:
            row["bonus_bps_e1"] = bonus(rid, user, hf1)
        except SystemExit as e:
            row["bonus_bps_e1"] = str(e)
        if row["cross"] is not None and row["cross"] < 64:
            # narrow the crossing: probe larger offsets until the position is healthy again
            for o in (3, 5, 12, 24, 48):
                if o > row["cross"]:
                    fork("reset", "base", str(blk - o))
                    row["hf"][o] = hf_of(user)
                    if row["hf"][o] < WAD:
                        row["cross"] = o
                    else:
                        break
        result["events"].append(row)
        print(f"block {blk}: " + json.dumps({k: v for k, v in row.items() if k != 'hf'}) + f" hf_ladder={row['hf']}", file=sys.stderr)
        out.write(json.dumps(row) + "\n")
    out.write(json.dumps(result) + "\n")
    out.close()

main()
