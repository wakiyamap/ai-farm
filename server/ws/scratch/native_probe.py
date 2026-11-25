import subprocess, json, sys

V = "0xBA8dB0CAf781cAc69b6acf6C848aC148264Cc05d"
FRESH = "0x1111111111111111111111111111111111111111"
RPC = ["python3", "/srv/farm/ws/tools/rpc.py", "bsc", "eth_call"]

SEL = {
 "epochUpdate": "0x98221e94",
 "settle": "0x9be41fdb",
 "repay": "0x81377bfd",
 "removeCollateral": "0x4e293ee9",
 "liquidate": "0x12411772",
 "pay": "0xc4076876",
 "addCollateral": "0xb6bdff03",
 "withdrawReserve": "0xae1914f8",
 "swapCallback": "0x7362ecbe",
}
ERRS = {
 "897e65bd": "OnlyTrader",
 "99b01c47": "OnlyLiquidator",
 "16ced9a8": "OnlyEpochUpdater",
 "dcdd32f1": "OnlyFeeWithdrawer",
 "918aa47f": "OnlyLpToken",
 "d687c5f2": "OnlyCreditPool",
 "8baa579f": "InvalidSignature",
 "fef01cd2": "RequestExpired",
 "d92e233d": "ZeroAddress",
 "fb837df4": "NotTrustedOperator",
}

def enc(types, args):
    r = subprocess.run(["cast", "abi-encode", f"f({types})", *args],
                       capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(f"encode fail {types}: {r.stderr[:200]}")
    return "0x" + r.stdout.strip()[2:]

def call(name, types, args):
    data = SEL[name] + enc(types, args)[2:]
    payload = json.dumps([{"from": FRESH, "to": V, "data": data}, "latest"])
    r = subprocess.run(RPC + [payload], capture_output=True, text=True)
    try:
        j = json.loads(r.stdout)
    except Exception:
        print(f"{name:18s} RPC-ERR rc={r.returncode} {r.stdout[:100]} {r.stderr[:100]}")
        return
    if "result" in j:
        res = j["result"]
        print(f"{name:18s} OK result={res[:80]}")
    else:
        msg = j.get("error", {}).get("message", "?")
        # custom error selector may be inside message or data
        errdata = j.get("error", {}).get("data", "") or ""
        sel4 = ""
        if isinstance(errdata, str) and errdata.startswith("0x") and len(errdata) >= 10:
            sel4 = errdata[2:10]
        elif "0x" in msg:
            for k in ERRS:
                if k in msg:
                    sel4 = k
        print(f"{name:18s} revert={ERRS.get(sel4, msg[:80])} (raw {sel4 or msg[:60]})")

call("epochUpdate", "(address,(address,uint256,uint256)[])[]", ["[]"])
call("settle", "(uint256,uint256,address,(address,int256)[],bytes)",
     ["(1,99999999999,0x1111111111111111111111111111111111111111,[],0x)"])
call("repay", "(address,int256)[],address",
     ["[]", "0x1111111111111111111111111111111111111111"])
call("removeCollateral", "(uint256,uint256,address,(address,uint256)[],bytes)",
     ["(1,99999999999,0x1111111111111111111111111111111111111111,[],0x)"])
call("liquidate", "(uint256,uint256,address,(address,int256)[],(address,uint256)[],bytes)",
     ["(1,99999999999,0x1111111111111111111111111111111111111111,[],[],0x)"])
call("pay", "address,uint256",
     ["0x1111111111111111111111111111111111111111", "0"])
call("withdrawReserve", "address,address,uint256",
     ["0x8ac76a48d5e0d3b1f18f6c955cca8b563b2267ff",
      "0x1111111111111111111111111111111111111111", "0"])
call("addCollateral", "(address,uint256)[],address",
     ["[]", "0x1111111111111111111111111111111111111111"])
call("swapCallback", "address,address,int256,address,int256",
     ["0x1111111111111111111111111111111111111111",
      "0x8ac76a48d5e0d3b1f18f6c955cca8b563b2267ff", "1",
      "0x8ac76a48d5e0d3b1f18f6c955cca8b563b2267ff", "-1"])
