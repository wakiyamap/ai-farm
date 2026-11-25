#!/usr/bin/env python3
"""Phase 10a helper: five new chains on the read side (relay, ledger, kb, forks).

  cfg-10a.py preflight            chain id from every public RPC and Alchemy endpoint, directly,
                                  before anything is changed (a wrong URL stops the install here)
  cfg-10a.py apply <etc_dir>      add the chains to <etc>/chains, <etc>/relay.json and write
                                  <etc>/fork-<chain>.env (idempotent; existing entries are kept)
  cfg-10a.py verify               through the relay (research lane): chain id, Chainlink feeds
                                  (decimals, description, price) and USDC (decimals, symbol)
  cfg-10a.py ledger <etc_dir>     measure each chain's block time through the relay and add
                                  blocks_per_call / block_time_s to <etc>/ledger.json

Addresses: Chainlink Standard proxies and USDC as given by the human (2026-11-10); public RPCs
and Alchemy subdomains from each chain's official docs and Alchemy's network pages.
"""
import json
import os
import sys
import urllib.error
import urllib.request

NEW = {
    "bsc": {"id": 56, "alchemy": "bnb-mainnet", "public": ["https://bsc-dataseed.bnbchain.org"], "port": 9004,
            "feed": "0x0567F2323251f0Aab15c8dFb1967E4e8A7D42aeE", "desc": ["BNB / USD"],
            "usdc": "0x8AC76a51cc950d9822D68b83fE1Ad97B32Cd580d", "usdc_decimals": 18},
    "polygon": {"id": 137, "alchemy": "polygon-mainnet", "public": ["https://polygon.drpc.org"], "port": 9005,
                "feed": "0xAB594600376Ec9fD91F8e885dADF0CE036862dE0", "desc": ["POL / USD", "MATIC / USD"],
                "usdc": "0x3c499c542cEF5E3811e1192ce70d8cC03d5c3359", "usdc_decimals": 6},
    "avalanche": {"id": 43114, "alchemy": "avax-mainnet", "public": ["https://api.avax.network/ext/bc/C/rpc"],
                  "port": 9006, "feed": "0x0A77230d17318075983913bC2145DB16C7366156", "desc": ["AVAX / USD"],
                  "usdc": "0xB97EF9Ef8734C71904D8002F8b6Bc66Dd9c48a6E", "usdc_decimals": 6},
    "optimism": {"id": 10, "alchemy": "opt-mainnet", "public": ["https://mainnet.optimism.io"], "port": 9007,
                 "feed": "0x13e3Ee699D1909E989722E753853AE30b17e08c5", "desc": ["ETH / USD"],
                 "usdc": "0x0b2C639c533813f4Aa9D7837CAf62653d097Ff85", "usdc_decimals": 6},
    "hyperevm": {"id": 999, "alchemy": "hyperliquid-mainnet", "public": ["https://rpc.hyperliquid.xyz/evm"],
                 "port": 9008, "feed": "0xa5a72eF19F82A579431186402425593a559ed352", "desc": ["HYPE / USD"],
                 "usdc": "0xb88339CB7199b77E23DB6E890353E22632Ba630f", "usdc_decimals": 6},
}
RELAY = "http://127.0.0.1:8545"
KEY_PATH = "/etc/farm/alchemy.key"
UA = {"Content-Type": "application/json", "User-Agent": "farm-relay/1.0 (phase10a preflight)"}
SEL = {"decimals": "0x313ce567", "description": "0x7284e416", "latestAnswer": "0x50d25bcd", "symbol": "0x95d89b41"}


def rpc(url, method, params, timeout=20):
    body = json.dumps({"jsonrpc": "2.0", "id": 1, "method": method, "params": params}).encode()
    req = urllib.request.Request(url, data=body, headers=UA)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            out = json.loads(r.read())
    except urllib.error.HTTPError as exc:          # keep the provider's reason (e.g. network not enabled)
        detail = " ".join(exc.read(400).decode("utf-8", "replace").split())
        raise RuntimeError(f"HTTP {exc.code} {detail}") from None
    if "error" in out:
        raise RuntimeError(str(out["error"].get("message")))
    return out["result"]


def abi_string(hexdata):
    b = bytes.fromhex(hexdata[2:])
    if len(b) >= 64:
        n = int.from_bytes(b[32:64], "big")
        return b[64:64 + n].decode("utf-8", "replace")
    return b.rstrip(b"\0").decode("utf-8", "replace")      # bytes32-style symbol


def preflight():
    key = ""
    try:
        key = open(KEY_PATH, encoding="utf-8").read().strip()
    except OSError:
        sys.exit(f"no Alchemy key at {KEY_PATH}")
    bad = 0
    for name, c in NEW.items():
        for u in c["public"]:
            try:
                got = int(rpc(u, "eth_chainId", []), 16)
                ok = got == c["id"]
                bad += not ok
                want = c["id"]
                print(f"  {name:10} public  {u}: chain id {got} {'ok' if ok else f'MISMATCH (want {want})'}")
            except (OSError, ValueError, RuntimeError) as exc:
                print(f"  {name:10} public  {u}: unreachable ({str(exc)[:80]}) - kept, the relay falls back")
        url = f"https://{c['alchemy']}.g.alchemy.com/v2/{key}"
        try:
            got = int(rpc(url, "eth_chainId", []), 16)
            ok = got == c["id"]
            bad += not ok
            print(f"  {name:10} alchemy {c['alchemy']}: chain id {got} {'ok' if ok else 'MISMATCH'}")
        except (OSError, ValueError, RuntimeError) as exc:
            bad += 1
            print(f"  {name:10} alchemy {c['alchemy']}: FAILED ({str(exc).replace(key, '<key>')[:120]})")
    if bad:
        sys.exit(f"preflight: {bad} endpoint(s) wrong; nothing was changed. An Alchemy failure (403, "
                 "'not enabled') usually means the network is not enabled for the app in the Alchemy dashboard")
    print("preflight ok")


def write_like(path, text):
    """Replace a file keeping its owner, group and mode."""
    st = os.stat(path)
    tmp = path + ".tmp-10a"
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(text)
    os.chown(tmp, st.st_uid, st.st_gid)
    os.chmod(tmp, st.st_mode & 0o7777)
    os.replace(tmp, path)


def apply(etc):
    # kb: one chain per line, '#' comments
    p = f"{etc}/chains"
    lines = open(p, encoding="utf-8").read().splitlines()
    have = {l.strip() for l in lines if l.strip() and not l.lstrip().startswith("#")}
    add = [n for n in NEW if n not in have]
    if add:
        write_like(p, "\n".join(lines + add) + "\n")
    print(f"  chains: added {add or 'nothing'}")
    # relay
    p = f"{etc}/relay.json"
    cfg = json.load(open(p, encoding="utf-8"))
    added = []
    for n, c in NEW.items():
        if n not in cfg["chains"]:
            cfg["chains"][n] = {"alchemy": c["alchemy"], "public": c["public"]}
            added.append(n)
    if added:
        write_like(p, json.dumps(cfg, indent=2) + "\n")
    print(f"  relay.json chains: added {added or 'nothing'}")
    # forks
    for n, c in NEW.items():
        p = f"{etc}/fork-{n}.env"
        if not os.path.exists(p):
            with open(p, "w", encoding="utf-8") as f:
                f.write(f"FORK_PORT={c['port']}\nFORK_CHAIN_ID={c['id']}\nFORK_UPSTREAM={n}\n")
            os.chmod(p, 0o644)
            print(f"  fork-{n}.env: port {c['port']}, chain id {c['id']}")
        else:
            print(f"  fork-{n}.env: exists, kept")


def call(chain, to, sel):
    return rpc(f"{RELAY}/{chain}?lane=research", "eth_call", [{"to": to, "data": sel}, "latest"], timeout=30)


def verify():
    bad = 0
    for n, c in NEW.items():
        try:
            got = int(rpc(f"{RELAY}/{n}?lane=research", "eth_chainId", []), 16)
        except (OSError, ValueError, RuntimeError) as exc:
            print(f"  {n:10} relay: FAILED ({str(exc)[:100]})")
            bad += 1
            continue
        if got != c["id"]:
            print(f"  {n:10} relay: chain id {got} MISMATCH")
            bad += 1
            continue
        try:
            dec = int(call(n, c["feed"], SEL["decimals"]), 16)
            desc = abi_string(call(n, c["feed"], SEL["description"]))
            price = int(call(n, c["feed"], SEL["latestAnswer"]), 16) / 10 ** dec
            fok = dec == 8 and desc in c["desc"]
            print(f"  {n:10} feed {c['feed']}: decimals {dec}, \"{desc}\", {price:,.4f} USD {'ok' if fok else 'CHECK'}")
            udec = int(call(n, c["usdc"], SEL["decimals"]), 16)
            sym = abi_string(call(n, c["usdc"], SEL["symbol"]))
            uok = udec == c["usdc_decimals"] and "USDC" in sym.upper()
            print(f"  {n:10} usdc {c['usdc']}: decimals {udec}, \"{sym}\" {'ok' if uok else 'CHECK'}")
            if not (fok and uok):
                print(f"  {n:10} -> the money side (10b) will not use this chain until this is resolved")
        except (OSError, ValueError, RuntimeError) as exc:
            print(f"  {n:10} feed/usdc read FAILED ({str(exc)[:100]})")
    if bad:
        sys.exit(f"verify: {bad} chain(s) not reachable through the relay")
    print("verify ok (relay)")


def ledger(etc):
    p = f"{etc}/ledger.json"
    cfg = json.load(open(p, encoding="utf-8"))
    for n in NEW:
        if n in cfg["blocks_per_call"] and n in cfg["block_time_s"]:
            print(f"  {n:10} ledger: already configured")
            continue
        u = f"{RELAY}/{n}?lane=research"
        head = int(rpc(u, "eth_blockNumber", []), 16)
        span = 20000
        t1 = int(rpc(u, "eth_getBlockByNumber", [hex(head), False])["timestamp"], 16)
        t0 = int(rpc(u, "eth_getBlockByNumber", [hex(head - span), False])["timestamp"], 16)
        bt = round(max((t1 - t0) / span, 0.05), 3)
        # about two hours of blocks per getLogs call, like base (5000 x 2 s); the ingester shrinks it on range errors
        bpc = int(min(10000, max(1000, round(7200 / bt, -2))))
        cfg["blocks_per_call"].setdefault(n, bpc)
        cfg["block_time_s"].setdefault(n, bt)
        print(f"  {n:10} ledger: block time {bt} s (measured over {span} blocks), blocks_per_call {bpc}")
    write_like(p, json.dumps(cfg, indent=2) + "\n")


if __name__ == "__main__":
    a = sys.argv[1:]
    if a[:1] == ["preflight"]:
        preflight()
    elif a[:1] == ["apply"] and len(a) == 2:
        apply(a[1])
    elif a[:1] == ["verify"]:
        verify()
    elif a[:1] == ["ledger"] and len(a) == 2:
        ledger(a[1])
    else:
        sys.exit(__doc__)
