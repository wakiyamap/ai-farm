#!/usr/bin/env python3
"""Phase 12d text patches: the holding frame (USDC -> another asset -> USDC, 200 USD in total).

  patch-12d.py check <gate-ctl> <farm-watchdog>          every old text occurs exactly once
  patch-12d.py apply <gate-ctl> <farm-watchdog> <outdir> write patched copies into <outdir>

Design: farm/design/design-2026-11-15-holding-frame.md (human decisions of 2026-11-15 13:45 JST).

gate-ctl
  promote  a manifest with `holding_usd: <usd>` is refused, before anything moves, unless:
           gate.json has max_holding_usd_total / max_holding_usd_per_bot (the frame is enabled),
           holding_usd <= max_holding_usd_per_bot (100), holding_usd <= principal_usdc, the bot
           names an executor whose ABI has exitAll() with no inputs, `holding_max_hours` is
           0 < h <= 168, and holding_usd + the holding_usd of every live bot (unfinished stops
           included) <= max_holding_usd_total (200).
  stop     for such a bot, before the sweep: the bot key calls exitAll() on every executor the
           gate deployed for it (addresses from gate.log, not from the bot-writable state file).
           Logged with the nonce as exit_sent before waiting, then exit or exit_failed. If any
           exit fails - it does not estimate, is not mined, reverts, or leaves USDC / native in
           the executor - nothing is swept, the bot stays live, exit code 3 ("unfinished stop").
           After 3 exitAll() transactions that failed on chain no further one is sent until a
           human runs `gate-ctl stop <id> --exit-again` (the watchdog repeats unfinished stops
           every 10 min, and each try costs gas).
  status   shows the frame: holding_usd per live bot, the total and the two limits.
farm-watchdog
  A bot with `holding_usd` (capped by gate.json max_holding_usd_per_bot; 0 when that key is
  absent) is stopped at max_live_loss_usd + holding_usd instead of max_live_loss_usd, and its
  drop between two balance reads may reach L + holding_usd: up to holding_usd the money is
  "in another asset", not "gone". The asset's price is not watched.
  exit_sent / exit / exit_failed nonces in gate.log are the gate's own, not a key compromise.
Bots without holding_usd are judged exactly as before.
"""
import sys

GATE = [
    # --- docstring -------------------------------------------------------------------------
    ("""  gate-ctl stop <id>               stop service, cancel pending, revoke approvals, sweep, archive
""",
     """  gate-ctl stop <id> [--exit-again]  stop service, cancel pending, exitAll() for a holding bot (12d), sweep, archive
"""),
    # --- manifest helpers ------------------------------------------------------------------
    ("""CONF = "/etc/farm/gate.json"
STATE = "/var/lib/farmgate"
LOG = f"{STATE}/gate.log"
""",
     """
def manifest_value(text, key):
    \"\"\"Number on the top-level `key:` line of a manifest, or None when the key is absent.\"\"\"
    for line in text.splitlines():
        if line.startswith(key + ":"):
            return manifest_number(line)
    return None


def manifest_holding(text):
    \"\"\"`holding_usd` of a manifest (12d): USD the bot may keep in another asset, inside its
    executor. 0.0 when absent or left empty. Raises ValueError on anything else that is not a
    finite number >= 0.\"\"\"
    for line in text.splitlines():
        if line.startswith("holding_usd:"):
            raw = line.split(":", 1)[1].split("#", 1)[0].strip().strip("'\\"")
            if not raw:                               # the key left empty, as in the manifest template
                return 0.0
            v = float(raw)
            if not 0 <= v < float("inf"):
                raise ValueError(f"holding_usd {v}")
            return v
    return 0.0


CONF = "/etc/farm/gate.json"
STATE = "/var/lib/farmgate"
LOG = f"{STATE}/gate.log"
EXIT_TRIES = 3     # exitAll() transactions that failed on chain before a human must say --exit-again (12d)
"""),
    # --- status ----------------------------------------------------------------------------
    ("""               "gas_wallet_cap_usd": self.cfg.get("gas_wallet_cap_usd", {}), "live": {}}
""",
     """               "gas_wallet_cap_usd": self.cfg.get("gas_wallet_cap_usd", {}), "live": {}}
        held = {b: v for b, v in self.live_holding_usd().items() if v}
        out["holding_usd"] = {"live": held, "total": round(sum(held.values()), 2),
                              "max_total": self.cfg.get("max_holding_usd_total", 0),
                              "max_per_bot": self.cfg.get("max_holding_usd_per_bot", 0)}
"""),
    # --- promote: the frame is checked before anything moves ---------------------------------
    ("""        self.executor_code(text, bot_addr)
        self.check_deploy_gas(bot_id, text, chains, bot_addr)    # before anything moves (10b, hyperevm)
""",
     """        self.executor_code(text, bot_addr)
        holding = self.check_holding(text, principal)            # before anything moves (12d)
        self.check_deploy_gas(bot_id, text, chains, bot_addr)    # before anything moves (10b, hyperevm)
"""),
    ("""        log(op="promote", bot=bot_id, chains=chains, capital_usd=cap, principal_usdc=principal, address=bot_addr, executor=executor)
        print(f"ok promoted {bot_id} ({farmkeys.checksum(bot_addr)}) on {chains}, {cap} USD (USDC principal {principal})")
""",
     """        log(op="promote", bot=bot_id, chains=chains, capital_usd=cap, principal_usdc=principal, address=bot_addr, executor=executor,
            holding_usd=holding)
        print(f"ok promoted {bot_id} ({farmkeys.checksum(bot_addr)}) on {chains}, {cap} USD (USDC principal {principal})"
              + (f", holding frame {holding:g} USD" if holding else ""))
"""),
    # --- the artifact's ABI, for the exitAll() check -------------------------------------------
    ("""            code = artifact["bytecode"]["object"] if isinstance(artifact.get("bytecode"), dict) else artifact["bytecode"]
        except (OSError, ValueError, KeyError) as exc:
            die(f"executor artifact unreadable: {exc}")
""",
     """            code = artifact["bytecode"]["object"] if isinstance(artifact.get("bytecode"), dict) else artifact["bytecode"]
        except (OSError, ValueError, KeyError) as exc:
            die(f"executor artifact unreadable: {exc}")
        self._executor_abi = artifact.get("abi")     # for check_holding (12d)
"""),
    # --- the holding frame: promote check, executors from gate.log, exitAll() -----------------
    ("""    def fund(self, bot_id, usd, usdc=False):
        if bot_id not in self.live_bots():
            die(f"{bot_id} is not live")
""",
     """    # --- holding frame (12d): USDC -> another asset kept in the executor -> USDC ------------------
    def live_holding_usd(self):
        \"\"\"{bot: holding_usd} of every live bot. A bot whose stop is unfinished is still live and
        still counts. A live manifest that cannot be read counts as a full per-bot share.\"\"\"
        out = {}
        for bot in self.live_bots():
            try:
                with open(f"{LIVE}/{bot}/manifest.yaml", encoding="utf-8") as f:
                    out[bot] = manifest_holding(f.read())
            except (OSError, ValueError):
                out[bot] = float(self.cfg.get("max_holding_usd_per_bot", 0))
        return out

    def check_holding(self, manifest_text, principal):
        \"\"\"promote: the manifest's holding_usd (0.0 = not a holding bot), or refuse. Call after
        executor_code(), which reads the artifact. Nothing has moved when this runs.\"\"\"
        try:
            holding = manifest_holding(manifest_text)
        except ValueError:
            die("manifest holding_usd must be a bare number >= 0; nothing was moved or funded")
        if holding == 0:
            return 0.0
        total, per = self.cfg.get("max_holding_usd_total"), self.cfg.get("max_holding_usd_per_bot")
        if not total or not per:
            die("manifest sets holding_usd, but gate.json has no max_holding_usd_total / max_holding_usd_per_bot: "
                "the holding frame is not enabled; nothing was moved or funded")
        if holding > per:
            die(f"holding_usd {holding:g} is above the per-bot limit {per:g} USD; nothing was moved or funded")
        if holding > principal:
            die(f"holding_usd {holding:g} is above principal_usdc {principal:g}: the other asset is bought with "
                "the bot's own USDC principal; nothing was moved or funded")
        if not re.search(r"^executor:\\s*\\S", manifest_text, re.M):
            die("a holding bot needs an executor: the asset is kept in the executor and comes back through "
                "its exitAll(); nothing was moved or funded")
        abi = getattr(self, "_executor_abi", None)
        if not any(isinstance(e, dict) and e.get("type") == "function" and e.get("name") == "exitAll"
                   and not e.get("inputs") for e in (abi if isinstance(abi, list) else [])):
            die("holding_usd is set, but the executor artifact's ABI has no exitAll() without arguments: "
                "`gate stop` calls it to bring the holdings back as USDC; nothing was moved or funded")
        max_h = self.cfg.get("max_holding_hours", 168)
        hours = manifest_value(manifest_text, "holding_max_hours")
        if hours is None or not 0 < hours <= max_h:
            die(f"a holding bot must set holding_max_hours (0 < hours <= {max_h:g}): how long it may hold before "
                "it sells back on its own; nothing was moved or funded")
        live = {b: v for b, v in self.live_holding_usd().items() if v}
        if sum(live.values()) + holding > total:
            die(f"holding_usd {holding:g} + {sum(live.values()):g} already live ({live}) would pass the frame of "
                f"{total:g} USD (max_holding_usd_total); nothing was moved or funded")
        return holding

    def exit_log(self, bot_id):
        \"\"\"From gate.log, for this bot since it was last archived: ({chain: executor address},
        {chain: exitAll() transactions that failed on chain since the last one that worked}).
        gate.log is the gate's own; state/executor.json is writable by the bot, so an entry there
        is used only when it is the contract this bot's key creates at the recorded nonce.\"\"\"
        executors, failed = {}, {}
        try:
            with open(LOG, encoding="utf-8") as f:
                for line in f:
                    try:
                        r = json.loads(line)
                    except ValueError:
                        continue
                    if not isinstance(r, dict) or r.get("bot") != bot_id:
                        continue
                    op, chain = r.get("op"), r.get("chain")
                    if op == "stop":
                        executors, failed = {}, {}
                    elif op == "deploy_executor" and r.get("address"):
                        executors[chain] = r["address"]
                    elif op == "exit":
                        failed.pop(chain, None)
                    elif op == "exit_failed" and r.get("txHash"):
                        failed[chain] = failed.get(chain, 0) + 1
        except OSError:
            pass
        try:
            with open(f"{LIVE}/{bot_id}/state/executor.json", encoding="utf-8") as f:
                st = json.load(f)
            frm = self.addr(f"bot:{bot_id}")
            import rlp as _rlp
            for chain, v in st.items():
                made = "0x" + farmkeys.keccak256(_rlp.encode([bytes.fromhex(frm[2:]), v["nonce"]]))[-20:].hex()
                if chain in CHAIN_IDS and v["address"].lower() == made:
                    executors.setdefault(chain, made)
        except (OSError, ValueError, KeyError, TypeError, AttributeError):
            pass
        return executors, failed

    def exit_holdings(self, bot_id, exit_again=False):
        \"\"\"stop, before the sweep (12d): a holding bot's executor holds another asset, which the
        sweep cannot see. Call exitAll() on every executor of the bot, from the bot's key; the
        executor sells everything and returns USDC (or native) to the bot wallet. Returns None when
        there is nothing to exit or every exit is done, else the reason (the stop is then unfinished
        and nothing is swept).\"\"\"
        try:
            with open(f"{LIVE}/{bot_id}/manifest.yaml", encoding="utf-8") as f:
                holding = manifest_holding(f.read())
        except ValueError:
            holding = -1.0                            # unreadable value: treat the bot as holding
        if holding == 0:
            return None
        executors, failed = self.exit_log(bot_id)
        if not executors:
            log(op="exit_skipped", bot=bot_id, why="no executor was deployed for this bot: nothing can be held")
            return None
        why = []
        for chain, ex in sorted(executors.items()):
            try:
                w = self.exit_one(bot_id, chain, ex, failed.get(chain, 0), exit_again)
            except (Exception, SystemExit) as exc:    # noqa: BLE001 - the other chains are still tried
                w = f"exitAll() aborted: {exc!r}"
                log(op="exit_failed", bot=bot_id, chain=chain, executor=ex, why=w)
            if w:
                why.append(f"{chain}: {w}")
        return "; ".join(why) or None

    def exit_one(self, bot_id, chain, ex, failed_before, exit_again):
        \"\"\"One exitAll() call. None when done, else why not. Every transaction sent with the bot's
        key is logged with its nonce before the receipt is awaited (the watchdog treats a bot nonce
        it finds in no log as a stolen key).\"\"\"
        def fail(why, **extra):
            log(op="exit_failed", bot=bot_id, chain=chain, executor=ex, why=why, **extra)
            return why
        if chain not in CHAIN_IDS:
            return fail("unknown chain")
        if failed_before >= EXIT_TRIES and not exit_again:
            return fail(f"{failed_before} exitAll() transactions already failed on chain; no further one is sent "
                        f"until a human runs `gate-ctl stop {bot_id} --exit-again`")
        label = f"bot:{bot_id}"
        priv = self.key(label)
        frm = farmkeys.address_of(priv)
        data = farmkeys.selector("exitAll()")
        try:
            est = int(self.rpc.call(chain, "eth_estimateGas", [{"from": frm, "to": ex, "data": data}]), 16)
        except (RuntimeError, ValueError, OSError) as exc:
            # nothing is sent, so nothing is spent: a call that would revert costs gas only when mined
            return fail(f"exitAll() does not estimate (it would revert, or {chain} is unreadable): {exc}")
        if est > max_tx_gas(chain):
            return fail(f"exitAll() needs {est:,} gas, above the {max_tx_gas(chain):,} the gate sends on {chain}")
        gas = min(int(est * 1.5), max_tx_gas(chain))  # headroom: a swap's gas moves with the pool's state
        fees = self.fees(chain)
        max_fee, tip = int(fees[0] * 1.2), fees[1]
        worst_usd = gas * max_fee / 1e18 * self.eth_usd(chain)
        if worst_usd > self.cfg["max_loss_per_tx_usd"]:
            return fail(f"exitAll() worst-case gas {worst_usd:.2f} USD is above L={self.cfg['max_loss_per_tx_usd']}")
        have = self.balance_wei(chain, frm)
        if have < gas * max_fee:
            # the bot ran its gas float down: top it up from the intermediate wallet, as the sweep does
            topup = gas * max_fee - have + transfer_gas_budget(chain) * max_fee
            th, _ = self.send_eth(chain, "intermediate", frm, topup, fees=(max_fee, tip))
            p = self.pnl()
            if bot_id in p["baseline"] and chain in p["baseline"][bot_id]:
                p["baseline"][bot_id][chain] += topup      # funded capital, so the PnL math sees it
                self.save_pnl(p)
            log(op="exit_gas_topup", bot=bot_id, chain=chain, wei=topup, txHash=th)
            tr = self.poll_receipt(chain, th)
            if not tr or tr.get("status") != "0x1":
                return fail(f"gas top-up {'pending' if not tr else 'reverted'}", topup_txHash=th)
        before = self.usdc_raw(chain, frm)
        n = None
        try:
            n = self.nonce(chain, frm)
            tx = {"chainId": CHAIN_IDS[chain], "nonce": n, "to": ex, "value": 0, "data": data,
                  "gas": gas, "maxFeePerGas": max_fee, "maxPriorityFeePerGas": tip}
            h = self.rpc.call(chain, "eth_sendRawTransaction", ["0x" + farmkeys.sign_eip1559(priv, tx).hex()])
        except Exception as exc:                      # noqa: BLE001 - socket errors and timeouts too
            # with the nonce: the call may be out all the same
            return fail(f"send failed: {exc!r}", nonce=n)
        log(op="exit_sent", bot=bot_id, chain=chain, executor=ex, txHash=h, nonce=n)
        r = self.poll_receipt(chain, h, timeout_s=180)
        if not r:
            return fail("exitAll() not mined in time", txHash=h, nonce=n)
        if r.get("status") != "0x1":
            return fail("exitAll() reverted", txHash=h, nonce=n)
        left = self.usdc_raw(chain, ex)
        left_native_usd = self.balance_wei(chain, ex) / 1e18 * self.eth_usd(chain)
        if left > 0 or left_native_usd > 1:
            return fail(f"exitAll() was mined, but the executor still holds {left / usdc_scale(chain):.2f} USDC and "
                        f"{left_native_usd:.2f} USD of {native(chain)}", txHash=h, nonce=n)
        log(op="exit", bot=bot_id, chain=chain, executor=ex, txHash=h, nonce=n,
            usdc_back=self.usdc_raw(chain, frm) - before)
        return None

    def fund(self, bot_id, usd, usdc=False):
        if bot_id not in self.live_bots():
            die(f"{bot_id} is not live")
"""),
    # --- stop: exitAll() before the sweep -----------------------------------------------------
    ("""    def stop(self, bot_id):
        if bot_id not in self.live_bots():
            die(f"{bot_id} is not live")
""",
     """    def stop(self, bot_id, exit_again=False):
        if bot_id not in self.live_bots():
            die(f"{bot_id} is not live")
"""),
    ("""        # limits approves to allowed contracts and finite amounts. Revocation of
        # ERC-20 approvals comes with the USDC step.
        try:
            swept_all, why = self.sweep(bot_id), "see the sweep_failed records in gate.log"
""",
     """        # limits approves to allowed contracts and finite amounts. Revocation of
        # ERC-20 approvals comes with the USDC step.
        # 12d: a holding bot's other asset sits in its executor, where the sweep cannot see it.
        # exitAll() brings it back to the wallet first. If that fails, sweeping what is in the
        # wallet would book the missing part as a realized loss and leave the retry without gas:
        # nothing is swept, and a human decides.
        try:
            exit_why = self.exit_holdings(bot_id, exit_again)
        except (Exception, SystemExit) as exc:        # noqa: BLE001
            exit_why = f"exitAll() aborted: {exc!r}"
            log(op="exit_failed", bot=bot_id, why=exit_why)
        if exit_why:
            log(op="stop_incomplete", bot=bot_id, why=exit_why)
            die(f"{bot_id}: the service is stopped, but its holdings are NOT back ({exit_why}). Nothing was "
                "swept. The bot stays listed as live - its wallet still counts toward X and is still watched. "
                f"This needs a human: see the exit_failed records in gate.log, then run `gate stop {bot_id}` again "
                "or recover the executor's assets by hand", 3)
        try:
            swept_all, why = self.sweep(bot_id), "see the sweep_failed records in gate.log"
"""),
    # --- main ------------------------------------------------------------------------------
    ("""    elif cmd == "stop" and bid:
        g.stop(bid)
""",
     """    elif cmd == "stop" and bid:
        g.stop(bid, exit_again="--exit-again" in rest[1:])
"""),
    ("""        die("usage: gate status [id] | intermediate | promote <id> | deploy <id> | fund <id> <usd> [--usdc] | sweep <id> | stop <id> | stop --all | restart <id>")
""",
     """        die("usage: gate status [id] | intermediate | promote <id> | deploy <id> | fund <id> <usd> [--usdc] | sweep <id> | stop <id> [--exit-again] | stop --all | restart <id>")
"""),
]

WATCHDOG = [
    ("""  - loss since promotion (pnl.json baselines minus wallet value) > max_live_loss_usd (30)
                                                                  -> stop that bot, wake (10c)
""",
     """  - loss since promotion (pnl.json baselines minus wallet value) > max_live_loss_usd (30)
                                                                  -> stop that bot, wake (10c)
    A bot whose manifest sets holding_usd (12d) may keep that much in another asset inside its
    executor: its lines are L + holding_usd and max_live_loss_usd + holding_usd.
"""),
    ("""UNREADABLE = set()   # live bots whose manifest names no known chain (reported once)
""",
     """def manifest_holding(text, cap):
    \"\"\"`holding_usd` of a live manifest (12d): USD the bot may keep in another asset, inside its
    executor. Never above `cap` (gate.json max_holding_usd_per_bot; 0 when that key is absent, so
    without the frame every bot keeps the plain lines). Absent or unreadable = 0.\"\"\"
    for raw in text.splitlines():
        if raw.startswith("holding_usd:"):
            try:
                v = float(raw.split(":", 1)[1].split("#", 1)[0].strip().strip("'\\""))
                cap = float(cap)
            except (ValueError, TypeError):
                return 0.0
            return min(v, cap) if v > 0 and cap > 0 else 0.0
    return 0.0


UNREADABLE = set()   # live bots whose manifest names no known chain (reported once)
"""),
    ("""                if r.get("bot") == bot and r.get("op") in ("sweep", "sweep_usdc", "sweep_usdc_sent", "cancel", "deploy_executor_sent", "deploy_executor", "sweep_failed", "cancel_failed") and r.get("nonce") is not None:
""",
     """                # exit_sent / exit / exit_failed: the gate's exitAll() call for a holding bot (12d)
                if r.get("bot") == bot and r.get("op") in ("sweep", "sweep_usdc", "sweep_usdc_sent", "cancel", "deploy_executor_sent", "deploy_executor", "sweep_failed", "cancel_failed", "exit_sent", "exit", "exit_failed") and r.get("nonce") is not None:
"""),
    ("""                    with open(f"{LIVE}/{bot}/manifest.yaml", encoding="utf-8") as f:
                        chains = manifest_chains(f.read())   # every YAML list style, like the gate (9i)
""",
     """                    with open(f"{LIVE}/{bot}/manifest.yaml", encoding="utf-8") as f:
                        mtext = f.read()
                    chains = manifest_chains(mtext)          # every YAML list style, like the gate (9i)
                    # 12d: up to holding_usd of this bot's USDC may sit in its executor as another
                    # asset. Both lines below move up by that much; the asset's price is not watched.
                    holding = manifest_holding(mtext, cfg.get("max_holding_usd_per_bot", 0))
"""),
    ("""                        if drop_usd > cfg["max_loss_per_tx_usd"] and not halted:
                            subprocess.run(["/opt/farm/bin/gate-ctl", "stop", bot], check=False)
                            wake("bot lost more than L between two balance reads, stopped it",
                                 f"bot: {bot}\\nchain: {chain}\\ndrop: {drop_usd:.2f} USD (native + USDC) since the last "
                                 f"balance read (every {bal_every * interval}s, and whenever the nonce moves)")
""",
     """                        if drop_usd > cfg["max_loss_per_tx_usd"] + holding and not halted:
                            subprocess.run(["/opt/farm/bin/gate-ctl", "stop", bot], check=False)
                            wake("bot lost more than L between two balance reads, stopped it",
                                 f"bot: {bot}\\nchain: {chain}\\ndrop: {drop_usd:.2f} USD (native + USDC) since the last "
                                 f"balance read (every {bal_every * interval}s, and whenever the nonce moves)"
                                 + (f"\\nline: L + holding_usd {holding:g}" if holding else ""))
"""),
    ("""                    elif loss > max_live_loss:
""",
     """                    elif loss > max_live_loss + holding:
"""),
    ("""                                 f"bot: {bot}\\nloss since promotion: {loss:.2f} USD (limit {max_live_loss:.0f} USD; "
""",
     """                                 f"bot: {bot}\\nloss since promotion: {loss:.2f} USD (limit {max_live_loss + holding:.0f} USD"
                                 + (f" = {max_live_loss:.0f} + holding_usd {holding:g}" if holding else "") + "; "
"""),
]


def patched(path, pairs, check_only=False):
    text = open(path, encoding="utf-8").read()
    for i, (old, new) in enumerate(pairs, 1):
        n = text.count(old)
        if n != 1:
            sys.exit(f"{path}: patch {i} matches {n} times (expected 1); nothing was changed")
        if not check_only:
            text = text.replace(old, new)
    return text


def main():
    if len(sys.argv) < 4 or sys.argv[1] not in ("check", "apply"):
        sys.exit(__doc__)
    gate, wd = sys.argv[2], sys.argv[3]
    if sys.argv[1] == "check":
        patched(gate, GATE, True)
        patched(wd, WATCHDOG, True)
        print(f"  gate-ctl: {len(GATE)} patches match, farm-watchdog: {len(WATCHDOG)} patches match")
        return
    out = sys.argv[4]
    for path, pairs, name in ((gate, GATE, "gate-ctl"), (wd, WATCHDOG, "farm-watchdog")):
        with open(f"{out}/{name}", "w", encoding="utf-8") as f:
            f.write(patched(path, pairs))
    print(f"  patched copies written to {out}")


if __name__ == "__main__":
    main()
