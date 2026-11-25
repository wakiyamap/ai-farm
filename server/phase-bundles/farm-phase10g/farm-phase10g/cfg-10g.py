#!/usr/bin/env python3
"""Phase 10g helper: elysium (Kinetiq's Arbitrum Orbit chain on HyperEVM, chain id 99901).

  cfg-10g.py preflight            chain id from the public RPC and the Alchemy endpoint, directly,
                                  before anything is changed (a wrong URL stops the install here)
  cfg-10g.py apply <etc_dir>      add elysium to <etc>/chains and <etc>/relay.json, write
                                  <etc>/fork-elysium.env (idempotent; existing entries are kept)
  cfg-10g.py verify               through the relay (research lane): chain id, USDC (decimals 6,
                                  symbol), the HYPE / USD feed on hyperevm, and what a plain
                                  transfer costs in gas. A mismatch stops the install before the
                                  money path is touched
  cfg-10g.py ledger <etc_dir>     measure the block time and add elysium to <etc>/ledger.json
  cfg-10g.py gate-plan <gate.json> / gate-apply <gate.json>
                                  chains += elysium, usdc.elysium (owner and mode kept)

Chain id 99901 and the public RPC https://rpc.elysium.kinetiq.xyz are from Kinetiq's own domain and
agree across independent sources (2026-11-11). The USDC address was given by the human. The Alchemy
subdomain defaults to elysium-mainnet (Alchemy's docs still listed only elysium-testnet when this
was written); set FARM_ELYSIUM_ALCHEMY=<subdomain> to use another one.
"""
import json
import os
import sys
import urllib.error
import urllib.request

NAME = "elysium"
C = {"id": 99901, "alchemy": os.environ.get("FARM_ELYSIUM_ALCHEMY", "elysium-mainnet"),
     "public": ["https://rpc.elysium.kinetiq.xyz"], "port": 9009,
     "usdc": "0xb47c4C8F73F009CC0C0d3f92B388d13E293F0B65", "usdc_decimals": 6,
     "feed_chain": "hyperevm", "feed": "0xa5a72eF19F82A579431186402425593a559ed352", "desc": ["HYPE / USD"]}
RELAY = "http://127.0.0.1:8545"
KEY_PATH = "/etc/farm/alchemy.key"
UA = {"Content-Type": "application/json", "User-Agent": "farm-relay/1.0 (phase10g preflight)"}
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
    try:
        key = open(KEY_PATH, encoding="utf-8").read().strip()
    except OSError:
        sys.exit(f"no Alchemy key at {KEY_PATH}")
    bad = 0
    for u in C["public"]:
        try:
            got = int(rpc(u, "eth_chainId", []), 16)
            ok = got == C["id"]
            bad += not ok
            print(f"  {NAME} public  {u}: chain id {got} {'ok' if ok else 'MISMATCH (want %d)' % C['id']}")
        except (OSError, ValueError, RuntimeError) as exc:
            print(f"  {NAME} public  {u}: unreachable ({str(exc)[:80]}) - kept, the relay falls back")
    url = f"https://{C['alchemy']}.g.alchemy.com/v2/{key}"
    try:
        got = int(rpc(url, "eth_chainId", []), 16)
        ok = got == C["id"]
        bad += not ok
        print(f"  {NAME} alchemy {C['alchemy']}: chain id {got} {'ok' if ok else 'MISMATCH (want %d)' % C['id']}")
    except (OSError, ValueError, RuntimeError) as exc:
        bad += 1
        print(f"  {NAME} alchemy {C['alchemy']}: FAILED ({str(exc).replace(key, '<key>')[:160]})")
    if bad:
        sys.exit("preflight: the Alchemy endpoint is wrong or not enabled; nothing was changed. Check the network's "
                 "endpoint name in the Alchemy dashboard (enable Elysium Mainnet for the app) and re-run with "
                 "FARM_ELYSIUM_ALCHEMY=<subdomain> if it is not 'elysium-mainnet'. Chain id 99801 means the testnet.")
    print("preflight ok")


def write_like(path, text):
    """Replace a file keeping its owner, group and mode."""
    st = os.stat(path)
    tmp = path + ".tmp-10g"
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(text)
    os.chown(tmp, st.st_uid, st.st_gid)
    os.chmod(tmp, st.st_mode & 0o7777)
    os.replace(tmp, path)


def apply(etc):
    p = f"{etc}/chains"                              # kb: one chain per line, '#' comments
    lines = open(p, encoding="utf-8").read().splitlines()
    have = {l.strip() for l in lines if l.strip() and not l.lstrip().startswith("#")}
    if NAME not in have:
        write_like(p, "\n".join(lines + [NAME]) + "\n")
    print(f"  chains: {'added ' + NAME if NAME not in have else 'nothing to add'}")
    p = f"{etc}/relay.json"
    cfg = json.load(open(p, encoding="utf-8"))
    if NAME not in cfg["chains"]:
        cfg["chains"][NAME] = {"alchemy": C["alchemy"], "public": C["public"]}
        write_like(p, json.dumps(cfg, indent=2) + "\n")
        print(f"  relay.json chains: added {NAME} (alchemy {C['alchemy']})")
    else:
        print(f"  relay.json chains: {NAME} exists, kept ({cfg['chains'][NAME].get('alchemy')})")
    p = f"{etc}/fork-{NAME}.env"
    if not os.path.exists(p):
        with open(p, "w", encoding="utf-8") as f:
            f.write(f"FORK_PORT={C['port']}\nFORK_CHAIN_ID={C['id']}\nFORK_UPSTREAM={NAME}\n")
        os.chmod(p, 0o644)
        print(f"  fork-{NAME}.env: port {C['port']}, chain id {C['id']}")
    else:
        print(f"  fork-{NAME}.env: exists, kept")


def call(chain, to, sel):
    return rpc(f"{RELAY}/{chain}?lane=research", "eth_call", [{"to": to, "data": sel}, "latest"], timeout=30)


def verify():
    u = f"{RELAY}/{NAME}?lane=research"
    bad = 0
    try:
        got = int(rpc(u, "eth_chainId", []), 16)
        print(f"  {NAME} relay: chain id {got} {'ok' if got == C['id'] else 'MISMATCH'}")
        bad += got != C["id"]
        code = rpc(u, "eth_getCode", [C["usdc"], "latest"])
        if code in (None, "0x"):
            print(f"  {NAME} usdc {C['usdc']}: NO CODE at this address")
            bad += 1
        else:
            udec = int(call(NAME, C["usdc"], SEL["decimals"]), 16)
            sym = abi_string(call(NAME, C["usdc"], SEL["symbol"]))
            uok = udec == C["usdc_decimals"] and "USDC" in sym.upper()
            print(f"  {NAME} usdc {C['usdc']}: decimals {udec}, \"{sym}\" {'ok' if uok else 'MISMATCH (want 6 decimals, symbol USDC)'}")
            bad += not uok
        fc = C["feed_chain"]
        dec = int(call(fc, C["feed"], SEL["decimals"]), 16)
        desc = abi_string(call(fc, C["feed"], SEL["description"]))
        price = int(call(fc, C["feed"], SEL["latestAnswer"]), 16) / 10 ** dec
        fok = dec == 8 and desc in C["desc"]
        print(f"  {NAME} price: feed {C['feed']} on {fc}: decimals {dec}, \"{desc}\", {price:,.4f} USD {'ok' if fok else 'MISMATCH'}")
        bad += not fok
        z = "0x000000000000000000000000000000000000dEaD"
        gas = int(rpc(u, "eth_estimateGas", [{"from": z, "to": z, "value": "0x0"}]), 16)
        gp = int(rpc(u, "eth_gasPrice", []), 16)
        print(f"  {NAME} plain transfer: {gas:,} gas (not 21,000: Nitro), gas price {gp / 1e9:.6f} gwei "
              f"= {gas * gp / 1e18 * price:.6f} USD")
    except (OSError, ValueError, RuntimeError) as exc:
        print(f"  {NAME} read FAILED ({str(exc)[:140]})")
        bad += 1
    if bad:
        sys.exit("verify: elysium does not match what 10g expects; the gate, signer and watchdog were NOT changed "
                 "(the relay, kb and fork config for elysium stay, which is harmless)")
    print("verify ok (relay)")


def ledger(etc):
    p = f"{etc}/ledger.json"
    cfg = json.load(open(p, encoding="utf-8"))
    if NAME in cfg["blocks_per_call"] and NAME in cfg["block_time_s"]:
        print(f"  {NAME} ledger: already configured")
        return
    u = f"{RELAY}/{NAME}?lane=research"
    head = int(rpc(u, "eth_blockNumber", []), 16)
    span = min(20000, head - 1)
    t1 = int(rpc(u, "eth_getBlockByNumber", [hex(head), False])["timestamp"], 16)
    t0 = int(rpc(u, "eth_getBlockByNumber", [hex(head - span), False])["timestamp"], 16)
    bt = round(max((t1 - t0) / span, 0.05), 3)
    bpc = int(min(10000, max(1000, round(7200 / bt, -2))))
    cfg["blocks_per_call"].setdefault(NAME, bpc)
    cfg["block_time_s"].setdefault(NAME, bt)
    print(f"  {NAME} ledger: block time {bt} s (measured over {span} blocks), blocks_per_call {bpc} "
          f"(= {bpc * bt / 60:.0f} min of chain per getLogs call; a 7-day backfill is {7 * 86400 / bt / bpc:,.0f} calls)")
    write_like(p, json.dumps(cfg, indent=2) + "\n")


def gate_planned(cfg):
    if not isinstance(cfg.get("chains"), list) or not isinstance(cfg.get("usdc", {}), dict):
        sys.exit("gate.json 'chains' / 'usdc' do not have the expected shape; change nothing")
    new = json.loads(json.dumps(cfg))
    changes = []
    if NAME not in new["chains"]:
        new["chains"].append(NAME)
        changes.append(f"chains += {NAME}")
    usdc = new.setdefault("usdc", {})
    if NAME not in usdc:
        usdc[NAME] = C["usdc"]
        changes.append(f"usdc.{NAME} = {C['usdc']}")
    elif usdc[NAME].lower() != C["usdc"].lower():
        sys.exit(f"gate.json usdc.{NAME} is {usdc[NAME]}, expected {C['usdc']}; change nothing")
    return new, changes


def gate(path, write):
    cfg = json.load(open(path, encoding="utf-8"))
    new, changes = gate_planned(cfg)
    if write and changes:
        write_like(path, json.dumps(new, indent=2) + "\n")
    print("\n".join(f"  gate.json: {c}" for c in changes) or "  gate.json: nothing to change")


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
    elif a[:1] == ["gate-plan"] and len(a) == 2:
        gate(a[1], False)
    elif a[:1] == ["gate-apply"] and len(a) == 2:
        gate(a[1], True)
    else:
        sys.exit(__doc__)
