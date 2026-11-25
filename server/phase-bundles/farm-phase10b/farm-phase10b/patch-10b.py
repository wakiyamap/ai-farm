#!/usr/bin/env python3
"""Phase 10b: exact-text patches - the money path (gate-ctl, farm-signer, farm-watchdog) on the
five chains added in 10a, plus common.md.

  patch-10b.py check <gate-ctl> <farm-signer> <farm-watchdog> <common.md>
  patch-10b.py apply <gate-ctl> <farm-signer> <farm-watchdog> <common.md> <outdir>

Every old text must occur exactly once, or nothing is written. Safe to re-run (markers).
"""
import os
import sys

OLD_CONSTS = '''CHAIN_IDS = {"ethereum": 1, "base": 8453, "arbitrum": 42161}
ETH_USD_FEED = {"ethereum": "0x5f4eC3Df9cbd43714FE2740f5E3616155c5b8419",
                "base": "0x71041dddad3595F9CEd3DcCFBe3D1F4b0a16Bb70",
                "arbitrum": "0x639Fe6ab55C921f74e7fac1ee960C0B6293ba612"}
'''

GATE = [
("chain constants come from /opt/farm/lib/farmchains.py",
OLD_CONSTS,
'''# chain ids, native/USD feeds, USDC decimals, gas limits: /opt/farm/lib/farmchains.py (10b)
from farmchains import CHAIN_IDS, ETH_USD_FEED, CORE, usdc_scale, price_ok, native, max_tx_gas  # noqa: E402
''',
"from farmchains import"),
("native/USD price must be plausible for the chain",
'''            self._price[chain] = int(res, 16) / 1e8
        return self._price[chain]
''',
'''            price = int(res, 16) / 1e8
            if not price_ok(chain, price):
                die(f"implausible {native(chain)}/USD price {price} on {chain} (feed {ETH_USD_FEED[chain]})")
            self._price[chain] = price
        return self._price[chain]
''',
"implausible {native(chain)}/USD price"),
("USDC comments: decimals per chain",
'''    # --- USDC (6 decimals; addresses from gate.json) ---------------------
''',
'''    # --- USDC (decimals per chain: farmchains.usdc_scale, 18 on bsc; addresses from gate.json) ---
''',
"farmchains.usdc_scale, 18 on bsc"),
("fees: newer chains honour eth_maxPriorityFeePerGas (Polygon minimum tip)",
'''        tip = max(base // 10, 100_000) if chain != "ethereum" else max(base // 10, 10**9)
        return base * 2 + tip, tip
''',
'''        tip = max(base // 10, 100_000) if chain != "ethereum" else max(base // 10, 10**9)
        if chain not in CORE:
            # chains added in phase 10: take the node's suggested tip when higher (Polygon rejects
            # transactions below its minimum priority fee)
            try:
                tip = max(tip, int(self.rpc.call(chain, "eth_maxPriorityFeePerGas", []), 16))
            except (RuntimeError, ValueError, OSError):
                pass
        return base * 2 + tip, tip
''',
"if chain not in CORE:\n            # chains added in phase 10"),
("fund_reserve_wei: gas for the funding transfers on the newer chains",
'''        room = cap_wei - self.balance_wei(chain, bot_addr)
        return max(0, min(wanted_wei, room))
''',
'''        room = cap_wei - self.balance_wei(chain, bot_addr)
        return max(0, min(wanted_wei, room))

    def fund_reserve_wei(self, chain, with_usdc):
        """Native the intermediate wallet keeps for the funding transfers themselves. 0.001 of the
        native token on the original chains (unchanged); on the chains added in phase 10 at least
        the actual gas of the native + USDC transfers, twice (0.001 POL would not pay one)."""
        if chain in CORE:
            return 10**15
        return max(10**15, (21000 + (90_000 if with_usdc else 0)) * self.fees(chain)[0] * 2)
''',
"def fund_reserve_wei"),
("X: USDC counted with the chain's decimals (intermediate)",
"            u = self.usdc_raw(chain, inter) / 1e6\n",
"            u = self.usdc_raw(chain, inter) / usdc_scale(chain)\n",
"self.usdc_raw(chain, inter) / usdc_scale(chain)"),
("X: USDC counted with the chain's decimals (bots)",
"                u = self.usdc_raw(chain, a) / 1e6\n",
"                u = self.usdc_raw(chain, a) / usdc_scale(chain)\n",
"self.usdc_raw(chain, a) / usdc_scale(chain)"),
("promote: USDC principal in each chain's units",
"        per_chain_usdc = int(principal / len(chains) * 1e6)\n",
"        per_chain_usdc = {c: int(principal / len(chains) * usdc_scale(c)) for c in chains}   # raw units (10b)\n",
"for c in chains}   # raw units (10b)"),
("promote: precheck reserve and USDC per chain",
'''            if self.balance_wei(chain, inter) < wei + 10**15:
''',
'''            if self.balance_wei(chain, inter) < wei + self.fund_reserve_wei(chain, bool(per_chain_usdc[chain])):
''',
"wei + self.fund_reserve_wei(chain, bool(per_chain_usdc[chain]))"),
("promote: USDC precheck per chain",
'''            if per_chain_usdc and self.usdc_raw(chain, inter) < per_chain_usdc:
                die(f"intermediate wallet on {chain} has less than {per_chain_usdc / 1e6:.2f} USDC; deposit first")
        r = subprocess.run(''',
'''            if per_chain_usdc[chain] and self.usdc_raw(chain, inter) < per_chain_usdc[chain]:
                die(f"intermediate wallet on {chain} has less than {principal / len(chains):.2f} USDC; deposit first")
        self.check_deploy_gas(bot_id, text, chains, bot_addr)    # before anything moves (10b, hyperevm)
        r = subprocess.run(''',
"self.check_deploy_gas(bot_id, text, chains, bot_addr)    # before"),
("promote: USDC funding per chain",
'''            if per_chain_usdc:
                h, _ = self.send_usdc(chain, "intermediate", bot_addr, per_chain_usdc)
                p["baseline_usdc"][bot_id][chain] = per_chain_usdc
                log(op="fund_usdc", bot=bot_id, chain=chain, usdc=per_chain_usdc, txHash=h)
''',
'''            if per_chain_usdc[chain]:
                h, _ = self.send_usdc(chain, "intermediate", bot_addr, per_chain_usdc[chain])
                p["baseline_usdc"][bot_id][chain] = per_chain_usdc[chain]
                log(op="fund_usdc", bot=bot_id, chain=chain, usdc=per_chain_usdc[chain], txHash=h)
''',
"send_usdc(chain, \"intermediate\", bot_addr, per_chain_usdc[chain])"),
("executor_code() split out of deploy_executor; check_deploy_gas() for small-block chains",
'''        # the path may be quoted (YAML string) and may carry a trailing comment (9j)
        m = re.search(r"^executor:\\s*['\\"]?([^'\\"\\s#]+)", manifest_text, re.M)
        if not m:
            return None
''',
'''        priv = self.key(f"bot:{bot_id}")
        frm = farmkeys.address_of(priv)
        code = self.executor_code(manifest_text, frm)
        if code is None:
            return None
        out = {}
        for chain in chains:
            max_fee, tip = self.fees(chain)
            nonce = self.nonce(chain, frm)
            gas = int(self.rpc.call(chain, "eth_estimateGas", [{"from": frm, "data": code}]), 16)
            if int(gas * 1.2) > max_tx_gas(chain):
                die(f"executor deployment on {chain} needs {int(gas * 1.2):,} gas, above the {max_tx_gas(chain):,} "
                    "that chain includes for farm keys; shrink the contract")
            tx = {"chainId": CHAIN_IDS[chain], "nonce": nonce, "to": None, "value": 0, "data": code,
                  "gas": int(gas * 1.2), "maxFeePerGas": max_fee, "maxPriorityFeePerGas": tip}
            raw = farmkeys.sign_eip1559(priv, tx)
            h = self.rpc.call(chain, "eth_sendRawTransaction", ["0x" + raw.hex()])
            # logged before waiting for the receipt: the watchdog checks bot nonces every 15 s and
            # treats a bot-key tx it cannot attribute as a key compromise
            log(op="deploy_executor_sent", bot=bot_id, chain=chain, txHash=h, nonce=nonce)
            # address = keccak(rlp([sender, nonce]))[12:]
            import rlp as _rlp
            addr = "0x" + farmkeys.keccak256(_rlp.encode([bytes.fromhex(frm[2:]), nonce]))[-20:].hex()
            for _ in range(60):                       # do not hand out an address that has no code
                rcpt = self.rpc.call(chain, "eth_getTransactionReceipt", [h])
                if rcpt:
                    break
                import time as _t
                _t.sleep(3)
            if not rcpt or rcpt.get("status") != "0x1":
                die(f"executor deployment on {chain} failed or not mined (tx {h}); check executor_args")
            out[chain] = {"address": addr, "txHash": h, "nonce": nonce}
            log(op="deploy_executor", bot=bot_id, chain=chain, address=addr, txHash=h, nonce=nonce)
        with open(f"{LIVE}/{bot_id}/state/executor.json", "w", encoding="utf-8") as f:
            json.dump(out, f, indent=1)
        # the signer also allows the executor addresses it finds in state/executor.json
        return out

    def check_deploy_gas(self, bot_id, manifest_text, chains, bot_addr):
        """On chains that include only small transactions for farm keys (farmchains.max_tx_gas
        below the usual 3M: hyperevm), refuse a promote whose executor deployment would not fit,
        before any funds move (10b)."""
        small = [c for c in chains if max_tx_gas(c) < 3_000_000]
        if not small:
            return
        code = self.executor_code(manifest_text, bot_addr)
        if code is None:
            return
        for chain in small:
            try:
                gas = int(self.rpc.call(chain, "eth_estimateGas", [{"from": bot_addr, "data": code}]), 16)
            except (RuntimeError, ValueError, OSError) as exc:
                die(f"cannot estimate the executor deployment on {chain}: {exc}")
            if int(gas * 1.2) > max_tx_gas(chain):
                die(f"executor deployment on {chain} needs {int(gas * 1.2):,} gas; {chain} includes at most "
                    f"{max_tx_gas(chain):,} per transaction for farm keys (small blocks). Shrink the contract")

    def executor_code(self, manifest_text, frm):
        """Creation code + constructor arguments for the manifest's executor, or None if the
        manifest names no executor. `frm` is the bot address that replaces {bot}."""
        # the path may be quoted (YAML string) and may carry a trailing comment (9j)
        m = re.search(r"^executor:\\s*['\\"]?([^'\\"\\s#]+)", manifest_text, re.M)
        if not m:
            return None
''',
"def executor_code(self, manifest_text, frm):"),
("executor_code(): keeps the artifact/args logic, returns the code",
'''        if not code.startswith("0x") or len(code) < 10:
            die("executor artifact has no bytecode")
        priv = self.key(f"bot:{bot_id}")
        frm = farmkeys.address_of(priv)
        # constructor arguments''',
'''        if not code.startswith("0x") or len(code) < 10:
            die("executor artifact has no bytecode")
        # constructor arguments''',
'''            die("executor artifact has no bytecode")
        # constructor arguments'''),
("executor_code(): end (the old deploy loop now lives in deploy_executor)",
'''            code = code + args.lower()
        out = {}
        for chain in chains:
            max_fee, tip = self.fees(chain)
            nonce = self.nonce(chain, frm)
            gas = int(self.rpc.call(chain, "eth_estimateGas", [{"from": frm, "data": code}]), 16)
            tx = {"chainId": CHAIN_IDS[chain], "nonce": nonce, "to": None, "value": 0, "data": code,
                  "gas": int(gas * 1.2), "maxFeePerGas": max_fee, "maxPriorityFeePerGas": tip}
            raw = farmkeys.sign_eip1559(priv, tx)
            h = self.rpc.call(chain, "eth_sendRawTransaction", ["0x" + raw.hex()])
            # logged before waiting for the receipt: the watchdog checks bot nonces every 15 s and
            # treats a bot-key tx it cannot attribute as a key compromise
            log(op="deploy_executor_sent", bot=bot_id, chain=chain, txHash=h, nonce=nonce)
            # address = keccak(rlp([sender, nonce]))[12:]
            import rlp as _rlp
            addr = "0x" + farmkeys.keccak256(_rlp.encode([bytes.fromhex(frm[2:]), nonce]))[-20:].hex()
            for _ in range(60):                       # do not hand out an address that has no code
                rcpt = self.rpc.call(chain, "eth_getTransactionReceipt", [h])
                if rcpt:
                    break
                import time as _t
                _t.sleep(3)
            if not rcpt or rcpt.get("status") != "0x1":
                die(f"executor deployment on {chain} failed or not mined (tx {h}); check executor_args")
            out[chain] = {"address": addr, "txHash": h, "nonce": nonce}
            log(op="deploy_executor", bot=bot_id, chain=chain, address=addr, txHash=h, nonce=nonce)
        with open(f"{LIVE}/{bot_id}/state/executor.json", "w", encoding="utf-8") as f:
            json.dump(out, f, indent=1)
        # the signer also allows the executor addresses it finds in state/executor.json
        return out
''',
'''            code = code + args.lower()
        return code
''',
'''            code = code + args.lower()
        return code
'''),
("fund --usdc: amount in each chain's units",
'''            raw = int(per * 1e6)
            for chain in chains:
                if self.usdc_raw(chain, inter) < raw:
                    die(f"intermediate wallet on {chain} has less than {per:.2f} USDC")
            for chain in chains:
                h, _ = self.send_usdc(chain, "intermediate", bot_addr, raw)
                b = p.setdefault("baseline_usdc", {}).setdefault(bot_id, {})
                b[chain] = b.get(chain, 0) + raw
                log(op="fund_usdc", bot=bot_id, chain=chain, usdc=raw, txHash=h)
''',
'''            raw = {c: int(per * usdc_scale(c)) for c in chains}      # raw units per chain (10b)
            for chain in chains:
                if self.usdc_raw(chain, inter) < raw[chain]:
                    die(f"intermediate wallet on {chain} has less than {per:.2f} USDC")
            for chain in chains:
                h, _ = self.send_usdc(chain, "intermediate", bot_addr, raw[chain])
                b = p.setdefault("baseline_usdc", {}).setdefault(bot_id, {})
                b[chain] = b.get(chain, 0) + raw[chain]
                log(op="fund_usdc", bot=bot_id, chain=chain, usdc=raw[chain], txHash=h)
''',
"raw = {c: int(per * usdc_scale(c)) for c in chains}"),
("sweep: USDC PnL in the chain's units",
"                    uusd = round((uraw - ubase) / 1e6, 4)\n",
"                    uusd = round((uraw - ubase) / usdc_scale(chain), 4)\n",
"round((uraw - ubase) / usdc_scale(chain), 4)"),
("sweep: lost principal in the chain's units",
'''                    p["realized_usd"][bot_id] = p["realized_usd"].get(bot_id, 0.0) - ubase / 1e6
                log(op="sweep_usdc", bot=bot_id, chain=chain, usdc=0, usd=-ubase / 1e6, note="principal gone")
''',
'''                    p["realized_usd"][bot_id] = p["realized_usd"].get(bot_id, 0.0) - ubase / usdc_scale(chain)
                log(op="sweep_usdc", bot=bot_id, chain=chain, usdc=0, usd=-ubase / usdc_scale(chain), note="principal gone")
''',
"usd=-ubase / usdc_scale(chain)"),
("in-flight USDC settles in the chain's units",
'''            uusd = round((fl["usdc"] - ubase) / 1e6, 4)
''',
'''            uusd = round((fl["usdc"] - ubase) / usdc_scale(chain), 4)
''',
'round((fl["usdc"] - ubase) / usdc_scale(chain), 4)'),
]

SIGNER = [
("chain constants come from /opt/farm/lib/farmchains.py",
'''CHAIN_IDS = {"ethereum": 1, "base": 8453, "arbitrum": 42161}
# Chainlink ETH/USD aggregators (latestAnswer() returns 8 decimals)
ETH_USD_FEED = {"ethereum": "0x5f4eC3Df9cbd43714FE2740f5E3616155c5b8419",
                "base": "0x71041dddad3595F9CEd3DcCFBe3D1F4b0a16Bb70",
                "arbitrum": "0x639Fe6ab55C921f74e7fac1ee960C0B6293ba612"}
''',
'''# chain ids, Chainlink native/USD feeds (8 decimals), USDC decimals, gas limits: farmchains (10b)
from farmchains import CHAIN_IDS, ETH_USD_FEED, CORE, usdc_scale, price_ok, desc_ok, native, max_tx_gas  # noqa: E402
''',
"from farmchains import"),
("verify_feeds: per-chain description; a bad feed on a new chain disables only that chain",
'''    def verify_feeds(self):
        """Refuse to start unless every feed really is an 8-decimal ETH / USD aggregator."""
        for chain, feed in ETH_USD_FEED.items():
            dec = int(self.rpc.call(chain, "eth_call", [{"to": feed, "data": farmkeys.selector("decimals()")}, "latest"]), 16)
            raw = self.rpc.call(chain, "eth_call", [{"to": feed, "data": farmkeys.selector("description()")}, "latest"])
            b = bytes.fromhex(raw[2:])
            desc = b[64:64 + int.from_bytes(b[32:64], "big")].decode("utf-8", "replace") if len(b) >= 64 else ""
            if dec != 8 or "ETH / USD" not in desc:
                raise SystemExit(f"farm-signer: {chain} feed {feed} is not ETH/USD (decimals={dec}, description={desc!r})")
''',
'''    def verify_feeds(self):
        """Every feed must be an 8-decimal native/USD aggregator with the expected description
        (farmchains). A bad feed on an original chain stops the signer, as before; on a chain added
        in phase 10 it disables signing on that chain only (logged), so one new chain's RPC trouble
        at start cannot stop every live bot."""
        self.disabled = {}
        for chain, feed in ETH_USD_FEED.items():
            try:
                dec = int(self.rpc.call(chain, "eth_call", [{"to": feed, "data": farmkeys.selector("decimals()")}, "latest"]), 16)
                raw = self.rpc.call(chain, "eth_call", [{"to": feed, "data": farmkeys.selector("description()")}, "latest"])
                b = bytes.fromhex(raw[2:])
                desc = b[64:64 + int.from_bytes(b[32:64], "big")].decode("utf-8", "replace") if len(b) >= 64 else ""
                ok, why = dec == 8 and desc_ok(chain, desc), f"decimals={dec}, description={desc!r}"
            except Exception as exc:                       # noqa: BLE001 - any failure means unverified
                ok, why = False, f"read failed: {exc}"
            if ok:
                continue
            if chain in CORE:
                raise SystemExit(f"farm-signer: {chain} feed {feed} is not {native(chain)}/USD ({why})")
            self.disabled[chain] = why
            log(op="chain_disabled", chain=chain, feed=feed, why=why)
            print(f"farm-signer: {chain} disabled, feed {feed} not verified ({why})", file=sys.stderr)
''',
"self.disabled[chain] = why"),
("price plausibility per chain",
'''        if not 100 < price < 100000:
            raise RuntimeError("implausible ETH price")
''',
'''        if not price_ok(chain, price):
            raise RuntimeError(f"implausible {native(chain)}/USD price {price} on {chain}")
''',
"implausible {native(chain)}/USD price {price} on {chain}"),
("check: a chain whose feed failed at start is refused",
'''        if chain not in CHAIN_IDS or chain not in m["chains"]:
            return f"chain {chain} not allowed for {bot_id}"
''',
'''        if chain not in CHAIN_IDS or chain not in m["chains"]:
            return f"chain {chain} not allowed for {bot_id}"
        if chain in getattr(self.prices, "disabled", {}):
            return (f"{chain} is disabled: its price feed was not verified when the signer started "
                    f"({self.prices.disabled[chain]}); restart farm-signer once the relay reads it")
''',
"is disabled: its price feed was not verified"),
("check: only this chain's USDC counts as the USDC token (eight addresses now)",
"        usdc_tokens = {v.lower() for v in (self.cfg.get(\"usdc\") or {}).values()}\n",
"        usdc_tokens = {(self.cfg.get(\"usdc\") or {}).get(chain, \"\").lower()} - {\"\"}   # this chain's only (10b)\n",
"this chain's only (10b)"),
("spend: only this chain's USDC transfer counts as USDC sent",
"            if req[\"to\"].lower() in {v.lower() for v in (self.cfg.get(\"usdc\") or {}).values()} and d.startswith(SEL_TRANSFER):\n",
"            if req[\"to\"].lower() == (self.cfg.get(\"usdc\") or {}).get(chain, \"\").lower() and d.startswith(SEL_TRANSFER):\n",
"== (self.cfg.get(\"usdc\") or {}).get(chain, \"\").lower() and d.startswith"),
("check: USDC moved out counted with the chain's decimals",
"                transferred_usd = amount / 1e6\n",
"                transferred_usd = amount / usdc_scale(chain)\n",
"transferred_usd = amount / usdc_scale(chain)"),
("check: per-chain gas limit (hyperevm small blocks: 2M)",
'''        if gas > 3_000_000:
            return "gas limit above 3M"
''',
'''        if gas > max_tx_gas(chain):
            return (f"gas limit above {max_tx_gas(chain):,} on {chain}"
                    + (" (larger transactions only land in big blocks, which farm keys do not use)" if chain == "hyperevm" else ""))
''',
"if gas > max_tx_gas(chain):"),
("spend: USDC sent counted with the chain's decimals",
"                worst += (int(d[74:138], 16) if len(d) >= 138 else 0) / 1e6\n",
"                worst += (int(d[74:138], 16) if len(d) >= 138 else 0) / usdc_scale(chain)\n",
"else 0) / usdc_scale(chain)"),
]

WATCHDOG = [
("chain constants come from /opt/farm/lib/farmchains.py",
OLD_CONSTS,
'''# chain ids, native/USD feeds, USDC decimals: /opt/farm/lib/farmchains.py (10b)
from farmchains import CHAIN_IDS, ETH_USD_FEED, usdc_scale, price_ok  # noqa: E402
''',
"from farmchains import"),
("READ_FAILED: chains whose reads fail are reported once",
'''UNREADABLE = set()   # live bots whose manifest names no known chain (reported once)
''',
'''UNREADABLE = set()   # live bots whose manifest names no known chain (reported once)
READ_FAILED = set()  # (bot, chain) whose reads failed; reported once until they read again (10b)
''',
"READ_FAILED = set()"),
("one chain's RPC failure no longer skips the remaining chains and bots",
'''                for chain in chains:
                    bal = int(rpc(url, chain, "eth_getBalance", [addr, "latest"]), 16)
                    nonce = int(rpc(url, chain, "eth_getTransactionCount", [addr, "latest"]), 16)
                    price = int(rpc(url, chain, "eth_call", [{"to": ETH_USD_FEED[chain], "data": farmkeys.selector("latestAnswer()")}, "latest"]), 16) / 1e8
                    token = (cfg.get("usdc") or {}).get(chain)
                    usdc = 0
                    if token:
                        r = rpc(url, chain, "eth_call", [{"to": token, "data": farmkeys.encode_call("balanceOf(address)", addr)}, "latest"])
                        usdc = int(r, 16) if r and r != "0x" else 0
''',
'''                for chain in chains:
                    try:
                        bal = int(rpc(url, chain, "eth_getBalance", [addr, "latest"]), 16)
                        nonce = int(rpc(url, chain, "eth_getTransactionCount", [addr, "latest"]), 16)
                        price = int(rpc(url, chain, "eth_call", [{"to": ETH_USD_FEED[chain], "data": farmkeys.selector("latestAnswer()")}, "latest"]), 16) / 1e8
                        if not price_ok(chain, price):
                            raise RuntimeError(f"implausible native/USD price {price}")
                        token = (cfg.get("usdc") or {}).get(chain)
                        usdc = 0
                        if token:
                            r = rpc(url, chain, "eth_call", [{"to": token, "data": farmkeys.encode_call("balanceOf(address)", addr)}, "latest"])
                            usdc = int(r, 16) if r and r != "0x" else 0
                    except Exception as exc:              # noqa: BLE001 - keep watching the other chains (10b)
                        if (bot, chain) not in READ_FAILED:
                            READ_FAILED.add((bot, chain))
                            print(f"watchdog: {bot}@{chain}: read failed ({exc!r}); skipping this chain until it reads again",
                                  file=sys.stderr)
                        continue
                    if (bot, chain) in READ_FAILED:
                        READ_FAILED.discard((bot, chain))
                        print(f"watchdog: {bot}@{chain}: reading again", file=sys.stderr)
''',
"keep watching the other chains (10b)"),
("loss check: USDC in the chain's units",
"                        drop_usd = (pbal - bal) / 1e18 * price + (pusdc - usdc) / 1e6\n",
"                        drop_usd = (pbal - bal) / 1e18 * price + (pusdc - usdc) / usdc_scale(chain)\n",
"(pusdc - usdc) / usdc_scale(chain)"),
]

COMMON = [
("new chains: the gate, signer and watchdog work there now",
'''The last five were added on 2026-11-10: reads, the ledger, the KB and forks work on them, but **the gate cannot fund or promote a bot there yet** and refuses such a manifest. Research, build and paper-test there; promotion follows once the human extends the money path (the KB and decisions will say so). Differences that bite: ''',
'''The last five were added on 2026-11-10 and now work like the first three: reads, the ledger, the KB, forks, and the gate, signer and watchdog. A promotion there still needs native gas (and USDC, if the manifest asks for principal) in the intermediate wallet on that chain; `gate status` shows what it holds per chain, and a shortfall is the usual gate refusal (ask the human through `inbox/human/`). Differences that bite: on HyperEVM every transaction, the executor deployment included, must fit in **2,000,000 gas** (larger ones only land in big blocks, which farm keys cannot opt into); the gate and the signer refuse more. ''',
"now work like the first three"),
("L: OP Stack chains are Base and OP Mainnet",
'''  On **OP Stack chains (Base)** the L1 data fee and operator fee are charged at inclusion and are not bounded by any field of the signed transaction. There the enforceable worst case is the bot's native wallet balance: the gate never funds a Base bot's native wallet above `gas_wallet_cap_usd` (18 USD), and the signer refuses to sign while the balance is above it. A Base bot therefore pays gas from that wallet only''',
'''  On **OP Stack chains (Base, OP Mainnet)** the L1 data fee and operator fee are charged at inclusion and are not bounded by any field of the signed transaction. There the enforceable worst case is the bot's native wallet balance: the gate never funds such a bot's native wallet above `gas_wallet_cap_usd` (18 USD on each), and the signer refuses to sign while the balance is above it. Such a bot therefore pays gas from that wallet only''',
"OP Stack chains (Base, OP Mainnet)"),
("L: priced with each chain's native/USD feed",
"(the signer's ETH/USD price, which refuses anything above L)",
"(the signer's Chainlink price for the chain's native token, which refuses anything above L)",
"Chainlink price for the chain's native token"),
]

FILES = [("gate-ctl", GATE), ("farm-signer", SIGNER), ("farm-watchdog", WATCHDOG), ("common.md", COMMON)]


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
