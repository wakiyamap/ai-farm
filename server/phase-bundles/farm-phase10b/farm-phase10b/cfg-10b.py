#!/usr/bin/env python3
"""Phase 10b helper.

  cfg-10b.py verify <farmchains_dir>      through the relay (research lane): every chain in farmchains
                                         has the right chain id, its feed has 8 decimals, an accepted
                                         description and a plausible price, and the gate.json USDC (or
                                         the 10b address for a new chain) has the decimals farmchains
                                         says and the symbol USDC. Any mismatch stops the install.
  cfg-10b.py plan <gate.json>            print what `apply` would change; nothing is written
  cfg-10b.py apply <gate.json>           add the five chains to "chains", their USDC to "usdc",
                                         optimism 18 to "gas_wallet_cap_usd" (owner and mode kept)

USDC addresses: Circle (Polygon, Avalanche, OP, HyperEVM) and Binance-Peg (BSC), as given by the
human on 2026-11-10 and checked on chain by 10a (decimals, symbol).
"""
import json
import os
import sys
import urllib.request

RELAY = "http://127.0.0.1:8545"
NEW_USDC = {"bsc": "0x8AC76a51cc950d9822D68b83fE1Ad97B32Cd580d",
            "polygon": "0x3c499c542cEF5E3811e1192ce70d8cC03d5c3359",
            "avalanche": "0xB97EF9Ef8734C71904D8002F8b6Bc66Dd9c48a6E",
            "optimism": "0x0b2C639c533813f4Aa9D7837CAf62653d097Ff85",
            "hyperevm": "0xb88339CB7199b77E23DB6E890353E22632Ba630f"}
NEW_CAPS = {"optimism": 18}      # OP Stack, same reason and amount as base
SEL = {"decimals": "0x313ce567", "description": "0x7284e416", "latestAnswer": "0x50d25bcd", "symbol": "0x95d89b41"}
GATE_JSON = "/etc/farm/gate.json"


def rpc(chain, method, params):
    body = json.dumps({"jsonrpc": "2.0", "id": 1, "method": method, "params": params}).encode()
    req = urllib.request.Request(f"{RELAY}/{chain}?lane=research", data=body, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=30) as r:
        out = json.loads(r.read())
    if "error" in out:
        raise RuntimeError(str(out["error"].get("message")))
    return out["result"]


def abi_string(h):
    b = bytes.fromhex(h[2:])
    if len(b) >= 64:
        return b[64:64 + int.from_bytes(b[32:64], "big")].decode("utf-8", "replace")
    return b.rstrip(b"\0").decode("utf-8", "replace")


def load_fc(d):
    sys.path.insert(0, d)
    import farmchains
    return farmchains


def verify(fc_dir, gate_json=GATE_JSON):
    fc = load_fc(fc_dir)
    usdc = dict(NEW_USDC)
    try:
        usdc.update(json.load(open(gate_json, encoding="utf-8")).get("usdc") or {})
    except OSError:
        pass
    bad = 0
    for chain, c in fc.CHAINS.items():
        try:
            cid = int(rpc(chain, "eth_chainId", []), 16)
            call = lambda to, sel: rpc(chain, "eth_call", [{"to": to, "data": sel}, "latest"])   # noqa: E731
            dec = int(call(c["feed"], SEL["decimals"]), 16)
            desc = abi_string(call(c["feed"], SEL["description"]))
            price = int(call(c["feed"], SEL["latestAnswer"]), 16) / 10 ** dec
            ok = cid == c["id"] and dec == 8 and fc.desc_ok(chain, desc) and fc.price_ok(chain, price)
            line = f"  {chain:10} id {cid}, feed {dec} decimals \"{desc}\" {price:,.4f} USD"
            if chain in usdc:
                udec = int(call(usdc[chain], SEL["decimals"]), 16)
                sym = abi_string(call(usdc[chain], SEL["symbol"]))
                ok = ok and udec == c["usdc_dec"] and sym.upper() == "USDC"
                line += f", USDC {usdc[chain]} {udec} decimals \"{sym}\""
            print(line + ("  ok" if ok else "  MISMATCH"))
            bad += not ok
        except (OSError, ValueError, RuntimeError) as exc:
            print(f"  {chain:10} read FAILED: {str(exc)[:120]}")
            bad += 1
    if bad:
        sys.exit(f"verify: {bad} chain(s) do not match farmchains; nothing was changed")
    print("verify ok (farmchains matches the chains)")


def planned(cfg):
    """(new cfg, list of change lines). Refuses shapes it does not understand."""
    if not isinstance(cfg.get("chains"), list):
        sys.exit(f"gate.json 'chains' is {type(cfg.get('chains')).__name__}, expected a list; change nothing")
    for k in ("usdc", "gas_wallet_cap_usd"):
        if not isinstance(cfg.get(k, {}), dict):
            sys.exit(f"gate.json '{k}' is not an object; change nothing")
    new = json.loads(json.dumps(cfg))
    changes = []
    for chain in NEW_USDC:
        if chain not in new["chains"]:
            new["chains"].append(chain)
            changes.append(f"chains += {chain}")
    usdc = new.setdefault("usdc", {})
    for chain, a in NEW_USDC.items():
        if chain not in usdc:
            usdc[chain] = a
            changes.append(f"usdc.{chain} = {a}")
        elif usdc[chain].lower() != a.lower():
            sys.exit(f"gate.json usdc.{chain} is {usdc[chain]}, expected {a}; change nothing")
    caps = new.setdefault("gas_wallet_cap_usd", {})
    for chain, v in NEW_CAPS.items():
        if chain not in caps:
            caps[chain] = v
            changes.append(f"gas_wallet_cap_usd.{chain} = {v}")
    # other per-chain maps (keys that look like chain names): shown so nothing is missed
    for k, v in cfg.items():
        if isinstance(v, dict) and "base" in v and k not in ("usdc", "gas_wallet_cap_usd"):
            missing = [c for c in NEW_USDC if c not in v]
            if missing:
                changes.append(f"NOTE: gate.json '{k}' is per chain and has no entry for {missing} (left as is)")
    return new, changes


def plan(path):
    cfg = json.load(open(path, encoding="utf-8"))
    _, changes = planned(cfg)
    print("\n".join(f"  {c}" for c in changes) or "  nothing to change")


def apply(path):
    cfg = json.load(open(path, encoding="utf-8"))
    new, changes = planned(cfg)
    if not [c for c in changes if not c.startswith("NOTE")]:
        print("  gate.json: nothing to change")
        return
    st = os.stat(path)
    tmp = path + ".tmp-10b"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(new, f, indent=2)
        f.write("\n")
    os.chown(tmp, st.st_uid, st.st_gid)
    os.chmod(tmp, st.st_mode & 0o7777)
    os.replace(tmp, path)
    print("\n".join(f"  gate.json: {c}" for c in changes))


if __name__ == "__main__":
    a = sys.argv[1:]
    if a[:1] == ["verify"] and len(a) == 2:
        verify(a[1])
    elif a[:1] == ["plan"] and len(a) == 2:
        plan(a[1])
    elif a[:1] == ["apply"] and len(a) == 2:
        apply(a[1])
    else:
        sys.exit(__doc__)
