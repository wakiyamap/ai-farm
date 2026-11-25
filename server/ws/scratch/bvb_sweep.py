#!/usr/bin/env python3
"""Bridge-vs-bridge quote sweep (decision 2026-11-16-bridge-vs-bridge-quotes).
Quotes only, no transactions. USDC across the 8 non-elysium farm chains.
Sources: Relay (local proxy POST /quote) + LiFi-routed per-bridge quotes
(across, stargateV2, cctp, mayan). Writes JSONL rows."""
import json, time, threading, urllib.request, urllib.error, itertools, sys
from concurrent.futures import ThreadPoolExecutor

OUT = "/srv/farm/ws/scratch/bvb_quotes2.jsonl"
LOCK = threading.Lock()
USER = "0x000000000000000000000000000000000000dEaD"
CHAINS = {1:"ethereum", 8453:"base", 42161:"arbitrum", 10:"optimism",
          137:"polygon", 43114:"avalanche", 56:"bsc", 999:"hyperevm"}
USDC = {1:"0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48",
        8453:"0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913",
        42161:"0xaf88d065e77c8cC2239327C5EDb3A432268e5831",
        10:"0x0b2C639c533813f4Aa9D7837CAf62653d097Ff85",
        137:"0x3c499c542cEF5E3811e1192ce70d8cC03d5c3359",
        43114:"0xB97EF9Ef8734C71904D8002F8b6Bc66Dd9c48a6E",
        56:"0x8AC76a51cc950d9822D68b83fE1Ad97B32Cd580d",
        999:"0xb88339CB7199b77E23DB6E890353E22632Ba630f"}
DEC = {c:(18 if c==56 else 6) for c in CHAINS}
TOOLS = ["across","stargateV2","cctp","mayan"]
AMOUNTS = [200, 2000]

def http_json(url, payload=None, tries=3):
    for i in range(tries):
        try:
            ua = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) farm-measure-quote"}
            if payload is None:
                req = urllib.request.Request(url, headers={**ua, "Accept":"application/json"})
            else:
                req = urllib.request.Request(url, data=json.dumps(payload).encode(),
                    headers={**ua, "Content-Type":"application/json","Accept":"application/json"})
            with urllib.request.urlopen(req, timeout=40) as r:
                return json.loads(r.read().decode())
        except urllib.error.HTTPError as e:
            body = e.read().decode()[:200] if e.fp else ""
            if e.code in (429,500,502,503,504) and i < tries-1:
                time.sleep(2.0*(i+1)); continue
            return {"_err": f"HTTP {e.code} {body}"}
        except Exception as e:
            if i < tries-1: time.sleep(1.5*(i+1)); continue
            return {"_err": f"{type(e).__name__} {e}"}

def relay_quote(a, b, amt):
    p = {"user": USER, "originChainId": a, "destinationChainId": b,
         "amount": str(int(amt * 10**DEC[a])),
         "originCurrency": USDC[a], "destinationCurrency": USDC[b],
         "toWallet": USER, "tradeType": "EXACT_INPUT", "slippageTolerance": "50"}
    d = http_json("http://127.0.0.1:29485/quote", p)
    if "_err" in d: return {"err": d["_err"]}
    try:
        det = d["details"]
        gas = float(d.get("fees",{}).get("gas",{}).get("amountUsd") or 0)
        rel = float(d.get("fees",{}).get("relayer",{}).get("amountUsd") or 0)
        out = det["currencyOut"]
        return {"recv": float(out["amount"])/10**DEC[b],
                "recv_min": float(out["minimumAmount"])/10**DEC[b],
                "gas_usd": gas, "relayer_usd": rel}
    except Exception as e:
        return {"err": f"parse {type(e).__name__} {list(d.keys())[:5]}"}

def lifi_quote(a, b, amt, tool):
    u = ("https://li.quest/v1/quote?fromChain=%d&toChain=%d&fromToken=%s&toToken=%s"
         "&fromAmount=%d&fromAddress=%s&order=CHEAPEST&slippage=0.5&tools=%s"
         % (a, b, USDC[a], USDC[b], int(amt*10**DEC[a]), USER, tool))
    d = http_json(u)
    if "_err" in d: return {"err": d["_err"]}
    if "estimate" not in d: return {"err": str(d.get("message") or d.get("code") or d)[:120]}
    e = d["estimate"]
    try:
        gas = sum(float(g.get("amountUSD") or 0) for g in e.get("gasCosts", []))
        return {"recv": float(e["toAmount"])/10**DEC[b],
                "recv_min": float(e["toAmountMin"])/10**DEC[b],
                "gas_usd": gas}
    except Exception as ex:
        return {"err": f"parse {type(ex).__name__}"}

def row(src, a, b, amt, r):
    rec = {"ts": time.strftime("%H:%M:%S", time.gmtime()), "src": src,
           "from": CHAINS[a], "to": CHAINS[b], "amt": amt}
    rec.update(r)
    with LOCK:
        with open(OUT, "a") as f:
            f.write(json.dumps(rec)+"\n")

def main():
    pairs = list(itertools.combinations(sorted(CHAINS), 2))
    jobs = []
    for a, b in pairs:
        for (x, y) in ((a, b), (b, a)):
            for amt in AMOUNTS:
                jobs.append(("relay", x, y, amt, None))
                for t in TOOLS:
                    jobs.append((t, x, y, amt, t))
    print("jobs:", len(jobs), flush=True)
    with ThreadPoolExecutor(max_workers=3) as ex:
        futs = []
        for src, x, y, amt, tool in jobs:
            if src == "relay":
                futs.append(ex.submit(lambda x=x,y=y,amt=amt: row("relay", x, y, amt, relay_quote(x,y,amt))))
            else:
                futs.append(ex.submit(lambda x=x,y=y,amt=amt,tool=tool: row(tool, x, y, amt, lifi_quote(x,y,amt,tool))))
            time.sleep(0.12)
        done = 0
        for f in futs:
            f.result(); done += 1
            if done % 50 == 0: print("done", done, flush=True)

if __name__ == "__main__":
    main()
