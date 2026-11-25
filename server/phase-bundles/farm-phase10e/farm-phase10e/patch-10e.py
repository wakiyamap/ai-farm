#!/usr/bin/env python3
"""Phase 10e: exact-text patches - gate-ctl, farm-signer, farm-watchdog (audit of 2026-11-11).

  patch-10e.py check <gate-ctl> <farm-signer> <farm-watchdog>
  patch-10e.py apply <gate-ctl> <farm-signer> <farm-watchdog> <outdir>

Every old text must occur exactly once, or nothing is written. Safe to re-run (markers).
"""
import os
import sys

GATE = [
("reads_executor_addr(): does the bot's code read the executor address the gate hands it",
r'''def die(msg, code=2):
    print(f"gate: {msg}", file=sys.stderr)
    sys.exit(code)
''',
r'''def die(msg, code=2):
    print(f"gate: {msg}", file=sys.stderr)
    sys.exit(code)


CODE_SKIP_DIRS = {"node_modules", "logs", "state", ".git"}
CODE_SKIP_EXT = (".md", ".yaml", ".yml", ".json", ".sol", ".log", ".txt", ".lock", ".toml")


def reads_executor_addr(bot_dir):
    """True when some code file of the bot mentions EXECUTOR_ADDR or executor.json - the two
    places a live bot is given the address of the executor the gate deploys for it (10e)."""
    for root, dirs, files in os.walk(bot_dir):
        dirs[:] = [d for d in dirs if d not in CODE_SKIP_DIRS]
        for name in files:
            path = os.path.join(root, name)
            if name.endswith(CODE_SKIP_EXT) or os.path.islink(path):
                continue
            try:
                if os.path.getsize(path) > 2_000_000:
                    continue
                with open(path, encoding="utf-8", errors="ignore") as f:
                    code = f.read()
            except OSError:
                continue
            if "EXECUTOR_ADDR" in code or "executor.json" in code:
                return True
    return False
''',
"def reads_executor_addr(bot_dir):"),

("promote: an executor bot whose code never reads EXECUTOR_ADDR / state/executor.json is refused before funding",
r'''            die("manifest.yaml must list allowed_contracts (the contracts the bot wallet sends to) "
                "or name an executor")
''',
r'''            die("manifest.yaml must list allowed_contracts (the contracts the bot wallet sends to) "
                "or name an executor")
        if re.search(r"^executor:\s*\S", text, re.M) and not reads_executor_addr(src):
            # 2026-11-10: a bot read EXEC_ADDRESS, restart-looped right after promotion and the
            # executor deployment gas (5 USD) was lost. Paper mode never needs the address, so
            # neither the paper run nor the review shows this (10e).
            die("this bot names an executor, but none of its code reads EXECUTOR_ADDR or state/executor.json - "
                "the only places a live bot is given the address of the executor the gate deploys. "
                "Read the EXECUTOR_ADDR environment variable (else state/executor.json) and resubmit; "
                "nothing was funded")
''',
"and not reads_executor_addr(src):"),

("promote: pnl.json is saved after every funding transfer (native)",
r'''                p["baseline"][bot_id][chain] = wei
''',
r'''                p["baseline"][bot_id][chain] = wei
                self.save_pnl(p)                    # at once: a later failure must not lose this baseline (10e)
''',
"a later failure must not lose this baseline (10e)"),

("promote: pnl.json is saved after every funding transfer (USDC)",
r'''                p["baseline_usdc"][bot_id][chain] = per_chain_usdc[chain]
''',
r'''                p["baseline_usdc"][bot_id][chain] = per_chain_usdc[chain]
                self.save_pnl(p)                    # at once, as for the native baseline (10e)
''',
"at once, as for the native baseline (10e)"),

("fund: the per-bot cap also holds for top-ups",
r'''        chains = self.manifest_chains(f"{LIVE}/{bot_id}/manifest.yaml")
        per = usd / len(chains)
        bot_addr = self.addr(f"bot:{bot_id}")
        p = self.pnl()
        if usdc:
''',
r'''        chains = self.manifest_chains(f"{LIVE}/{bot_id}/manifest.yaml")
        per = usd / len(chains)
        bot_addr = self.addr(f"bot:{bot_id}")
        # max_capital_per_bot_usd was only checked at promotion and per single top-up, so repeated
        # top-ups could carry one bot past it (10e): wallet now + this top-up must stay within it
        have = sum(self.balance_wei(c, bot_addr) / 1e18 * self.eth_usd(c) + self.usdc_raw(c, bot_addr) / usdc_scale(c)
                   for c in chains)
        if have + usd > self.cfg["max_capital_per_bot_usd"]:
            die(f"{bot_id} holds {have:.2f} USD; {usd:.2f} more would pass the per-bot cap "
                f"({self.cfg['max_capital_per_bot_usd']} USD)")
        p = self.pnl()
        if usdc:
''',
"more would pass the per-bot cap"),

("fund --usdc: pnl.json is saved after every transfer",
r'''                b[chain] = b.get(chain, 0) + raw[chain]
''',
r'''                b[chain] = b.get(chain, 0) + raw[chain]
                self.save_pnl(p)                    # at once (10e)
''',
"b[chain] = b.get(chain, 0) + raw[chain]\n                self.save_pnl(p)"),

("fund: pnl.json is saved after every transfer",
r'''            p["baseline"].setdefault(bot_id, {})[chain] = p["baseline"].get(bot_id, {}).get(chain, 0) + wei
''',
r'''            p["baseline"].setdefault(bot_id, {})[chain] = p["baseline"].get(bot_id, {}).get(chain, 0) + wei
            self.save_pnl(p)                        # at once (10e)
''',
".get(chain, 0) + wei\n            self.save_pnl(p)"),

("pnl(): sweep_unsure survives the day change",
r'''                 "usdc_in_flight": p.get("usdc_in_flight", {})}
''',
r'''                 "usdc_in_flight": p.get("usdc_in_flight", {}), "sweep_unsure": p.get("sweep_unsure", {})}
''',
'"sweep_unsure": p.get("sweep_unsure", {})}'),

("poll_receipt: an RPC error while polling is not the end of the wait",
r'''        while time.monotonic() - t0 < timeout_s:
            r = self.rpc.call(chain, "eth_getTransactionReceipt", [txhash])
            if r:
''',
r'''        while time.monotonic() - t0 < timeout_s:
            try:
                r = self.rpc.call(chain, "eth_getTransactionReceipt", [txhash])
            except Exception:                         # noqa: BLE001 - keep polling: the transfer is already out (10e)
                r = None
            if r:
''',
"keep polling: the transfer is already out (10e)"),

("sweep: bookings survive a failure on a later chain; sweep() returns whether everything is back",
r'''    def sweep(self, bot_id, record_pnl=True):
        chains = self.manifest_chains(f"{LIVE}/{bot_id}/manifest.yaml") if os.path.exists(f"{LIVE}/{bot_id}/manifest.yaml") else list(CHAIN_IDS)
        label = f"bot:{bot_id}"
        bot_addr = self.addr(label)
        inter = self.intermediate()
        p = self.pnl()
        swept, all_ok = {}, True
''',
r'''    def sweep(self, bot_id, record_pnl=True):
        """True when every chain is done. Whatever was booked before a failure is saved (10e): an
        RPC error on a later chain used to drop the bookings of the earlier ones, and the next
        sweep then read the emptied wallet as "principal gone" (a phantom loss)."""
        p = self.pnl()
        try:
            return self._sweep(bot_id, record_pnl, p)
        finally:
            self.save_pnl(p)

    def _sweep(self, bot_id, record_pnl, p):
        chains = self.manifest_chains(f"{LIVE}/{bot_id}/manifest.yaml") if os.path.exists(f"{LIVE}/{bot_id}/manifest.yaml") else list(CHAIN_IDS)
        label = f"bot:{bot_id}"
        bot_addr = self.addr(label)
        inter = self.intermediate()
        swept, all_ok = {}, True
''',
"def _sweep(self, bot_id, record_pnl, p):"),

("sweep: per-bot record of transfers whose send call failed (they may have been broadcast)",
r'''            fees = (int(fees[0] * 1.2), fees[1])        # margin for base fee moving between calls
''',
r'''            fees = (int(fees[0] * 1.2), fees[1])        # margin for base fee moving between calls
            # sweep transfers whose send call failed: {chain | chain:usdc -> {nonce, amount}}. If the
            # nonce has moved on by the next sweep, the transfer was mined after all (10e)
            unsure = p.setdefault("sweep_unsure", {}).setdefault(bot_id, {})
''',
'unsure = p.setdefault("sweep_unsure", {}).setdefault(bot_id, {})'),

("sweep: a failed USDC send is logged with its nonce and remembered; every error type is caught",
r'''                try:
                    un = self.nonce(chain, bot_addr)    # send_usdc signs with this same pending nonce
                    uh, _ = self.send_usdc(chain, label, inter, uraw, fees=fees)
                except RuntimeError as exc:
                    log(op="sweep_failed", bot=bot_id, chain=chain, why=f"usdc: {exc}")
''',
r'''                un = None
                try:
                    un = self.nonce(chain, bot_addr)    # send_usdc signs with this same pending nonce
                    uh, _ = self.send_usdc(chain, label, inter, uraw, fees=fees)
                except Exception as exc:                # noqa: BLE001 - socket errors and timeouts too (10e)
                    # with the nonce: the transfer may be out all the same, and the watchdog must
                    # not take that nonce for a foreign transaction
                    log(op="sweep_failed", bot=bot_id, chain=chain, why=f"usdc: {exc!r}", nonce=un)
                    if un is not None:
                        unsure[chain + ":usdc"] = {"nonce": un, "usdc": uraw}
''',
'unsure[chain + ":usdc"] = {"nonce": un, "usdc": uraw}'),

("sweep: a USDC transfer that went through clears the unsure record",
r'''                swept[chain + ":usdc"] = uraw
''',
r'''                unsure.pop(chain + ":usdc", None)
                swept[chain + ":usdc"] = uraw
''',
'unsure.pop(chain + ":usdc", None)\n                swept[chain + ":usdc"] = uraw'),

("sweep: 'principal gone' is not booked when the earlier transfer was in fact mined",
r'''                # principal was funded but the wallet holds none now: that is a realized loss
                ubase = p["baseline_usdc"][bot_id].pop(chain)
                if record_pnl:
                    p["realized_usd"][bot_id] = p["realized_usd"].get(bot_id, 0.0) - ubase / usdc_scale(chain)
                log(op="sweep_usdc", bot=bot_id, chain=chain, usdc=0, usd=-ubase / usdc_scale(chain), note="principal gone")
''',
r'''                # principal was funded but the wallet holds none now: that is a realized loss -
                # unless an earlier sweep transfer whose send call failed was mined after all (10e)
                rec = unsure.get(chain + ":usdc")
                back = rec["usdc"] if rec and self.nonce(chain, bot_addr, "latest") > rec["nonce"] else 0
                unsure.pop(chain + ":usdc", None)
                ubase = p["baseline_usdc"][bot_id].pop(chain)
                uusd = round((back - ubase) / usdc_scale(chain), 4)
                if record_pnl:
                    p["realized_usd"][bot_id] = p["realized_usd"].get(bot_id, 0.0) + uusd
                log(op="sweep_usdc", bot=bot_id, chain=chain, usdc=0, usd=uusd,
                    note="earlier sweep transfer had been mined" if back else "principal gone")
''',
'back = rec["usdc"] if rec and self.nonce(chain, bot_addr, "latest") > rec["nonce"] else 0'),

("sweep: an emptied gas wallet is booked; a failed native send is logged with its nonce and remembered",
r'''            if bal <= cost * 2:
                swept[chain] = 0
                continue
            try:
                n = self.nonce(chain, bot_addr)
                h, _ = self.send_eth(chain, label, inter, bal - cost, nonce=n, fees=fees)
            except RuntimeError as exc:
                log(op="sweep_failed", bot=bot_id, chain=chain, why=str(exc))
                swept[chain] = f"failed: {exc}"
                all_ok = False
                continue
            swept[chain] = bal - cost
''',
r'''            if bal <= cost * 2:
                swept[chain] = 0
                base = p["baseline"].get(bot_id, {}).get(chain)
                rec = unsure.get(chain)
                if record_pnl and base is not None:
                    # Nothing left worth sending, but the gate did fund this wallet: book it (10e).
                    # Until now a bot that had burned its whole gas float left no PnL record at
                    # all. If an earlier sweep transfer's send call failed yet the transfer was
                    # mined (the nonce moved on), what came back is what the wallet held then.
                    landed = bool(rec) and self.nonce(chain, bot_addr, "latest") > rec["nonce"]
                    back = rec["wei"] if landed else bal
                    usd = round((back - base) / 1e18 * self.eth_usd(chain), 4)
                    p["realized_usd"][bot_id] = p["realized_usd"].get(bot_id, 0.0) + usd
                    p["baseline"][bot_id].pop(chain, None)
                    log(op="sweep", bot=bot_id, chain=chain, wei=0, usd=usd,
                        note="earlier sweep transfer had been mined" if landed else "wallet empty: the funded gas is spent")
                unsure.pop(chain, None)
                continue
            n = None
            try:
                n = self.nonce(chain, bot_addr)
                h, _ = self.send_eth(chain, label, inter, bal - cost, nonce=n, fees=fees)
            except Exception as exc:                  # noqa: BLE001 - socket errors and timeouts too (10e)
                # with the nonce, for the watchdog (see the USDC transfer above)
                log(op="sweep_failed", bot=bot_id, chain=chain, why=repr(exc), nonce=n)
                if n is not None:
                    unsure[chain] = {"nonce": n, "wei": bal}
                swept[chain] = f"failed: {exc}"
                all_ok = False
                continue
            unsure.pop(chain, None)
            swept[chain] = bal - cost
''',
'unsure[chain] = {"nonce": n, "wei": bal}'),

("sweep: says so when it is incomplete, and returns the result",
r'''        self.save_pnl(p)
        print(f"ok swept {bot_id}: {swept}")
''',
r'''        if not p.get("sweep_unsure", {}).get(bot_id):
            p.get("sweep_unsure", {}).pop(bot_id, None)
        print(f"{'ok swept' if all_ok else 'sweep INCOMPLETE:'} {bot_id}: {swept}")
        return all_ok                                 # pnl.json is saved by sweep() (10e)
''',
"return all_ok                                 # pnl.json is saved by sweep() (10e)"),

("cancel_pending: a chain that cannot be read does not abort the stop before the sweep",
r'''            latest, pending = self.nonce(chain, a, "latest"), self.nonce(chain, a, "pending")
            for n in range(latest, pending):
                try:
                    h, _ = self.send_eth(chain, label, a, 0, nonce=n, bump=1.3)
                    log(op="cancel", bot=bot_id, chain=chain, nonce=n, txHash=h)
                except RuntimeError as exc:
''',
r'''            try:
                latest, pending = self.nonce(chain, a, "latest"), self.nonce(chain, a, "pending")
            except Exception as exc:                  # noqa: BLE001 - the other chains are still swept (10e)
                log(op="cancel_failed", bot=bot_id, chain=chain, why=f"nonce unreadable: {exc!r}")
                continue
            for n in range(latest, pending):
                try:
                    h, _ = self.send_eth(chain, label, a, 0, nonce=n, bump=1.3)
                    log(op="cancel", bot=bot_id, chain=chain, nonce=n, txHash=h)
                except Exception as exc:              # noqa: BLE001 - socket errors and timeouts too (10e)
''',
'why=f"nonce unreadable: {exc!r}")'),

("stop: a bot whose sweep is incomplete is not archived (its funds would drop out of X and of the watchdog's view)",
r'''        self.sweep(bot_id)
        with open(f"{STATE}/stop-{bot_id}.md", "w", encoding="utf-8") as f:
''',
r'''        try:
            swept_all, why = self.sweep(bot_id), "see the sweep_failed records in gate.log"
        except Exception as exc:                      # noqa: BLE001 - e.g. the relay is unreachable
            swept_all, why = False, repr(exc)
            log(op="sweep_failed", bot=bot_id, why=f"sweep aborted: {exc!r}")
        if not swept_all:
            # Until 10e the bot was archived all the same: what was left in its wallet no longer
            # counted toward X, nothing watched it and nothing retried the sweep.
            log(op="stop_incomplete", bot=bot_id, why=why)
            die(f"{bot_id}: the service is stopped, but the sweep is incomplete ({why}). The bot stays listed "
                f"as live - its wallet still counts toward X and is still watched - until `gate stop {bot_id}` "
                "is run again and finishes", 3)
        with open(f"{STATE}/stop-{bot_id}.md", "w", encoding="utf-8") as f:
''',
'log(op="stop_incomplete", bot=bot_id, why=why)'),

("gate sweep <id>: exit code 3 when incomplete",
r'''    elif cmd == "sweep" and bid:
        g.sweep(bid)
''',
r'''    elif cmd == "sweep" and bid:
        if not g.sweep(bid):
            sys.exit(3)                               # incomplete (10e)
''',
"sys.exit(3)                               # incomplete (10e)"),
]

SIGNER = [
("increaseAllowance selector",
r'''SEL_TRANSFER_FROM = farmkeys.selector("transferFrom(address,address,uint256)")
''',
r'''SEL_TRANSFER_FROM = farmkeys.selector("transferFrom(address,address,uint256)")
SEL_INCREASE_ALLOWANCE = farmkeys.selector("increaseAllowance(address,uint256)")
''',
"SEL_INCREASE_ALLOWANCE = farmkeys.selector"),

("check: increaseAllowance is held to the approve rule (allowed spender, finite amount)",
r'''        if data.startswith(SEL_APPROVE):
''',
r'''        # increaseAllowance(spender, amount) grants an allowance exactly like approve; USDC has it,
        # and until 10e it passed unchecked, to any spender and for any amount
        if data.startswith(SEL_APPROVE) or data.startswith(SEL_INCREASE_ALLOWANCE):
''',
"if data.startswith(SEL_APPROVE) or data.startswith(SEL_INCREASE_ALLOWANCE):"),

("send: every broadcast failure leaves a record with the nonce",
r'''            except RuntimeError as exc:
                log(bot=bot_id, op="send", decision="broadcast_failed", why=str(exc), chain=chain, nonce=nonce)
''',
r'''            except Exception as exc:                  # noqa: BLE001 - socket errors and timeouts too (10e):
                # the transaction may be out all the same, and the watchdog halts everything on a
                # bot nonce it finds in no log
                log(bot=bot_id, op="send", decision="broadcast_failed", why=str(exc) or repr(exc), chain=chain, nonce=nonce)
''',
'why=str(exc) or repr(exc), chain=chain, nonce=nonce)'),
]

WATCHDOG = [
("LOSS_RETRY: an unfinished live-loss stop is tried again",
r'''NO_BASELINE = set()   # live bots without a pnl.json baseline: live-loss stop impossible (reported once)
''',
r'''NO_BASELINE = set()   # live bots without a pnl.json baseline: live-loss stop impossible (reported once)
LOSS_RETRY = {}       # bot -> (tries, monotonic time of the next try) while a live-loss stop is unfinished (10e)
LOSS_RETRY_S = 600
''',
"LOSS_RETRY_S = 600"),

("sent_nonces: a broadcast the signer attempted is the signer's, even when the relay reported a failure",
r'''                if r.get("bot") == bot and r.get("decision") == "sent":
''',
r'''                # broadcast_failed: the relay answered with an error or not at all, but the
                # transaction may have reached the chain; it is still ours, not a stolen key (10e)
                if r.get("bot") == bot and r.get("decision") in ("sent", "broadcast_failed"):
''',
'r.get("decision") in ("sent", "broadcast_failed")'),

("sent_nonces: gate transfers whose send call failed (logged with their nonce since 10e)",
r'''("sweep", "sweep_usdc", "sweep_usdc_sent", "cancel", "deploy_executor_sent", "deploy_executor")''',
r'''("sweep", "sweep_usdc", "sweep_usdc_sent", "cancel", "deploy_executor_sent", "deploy_executor", "sweep_failed", "cancel_failed")''',
'"deploy_executor", "sweep_failed", "cancel_failed")'),

("a bot id that left bots/live is forgotten by the live-loss stop (the same id may be promoted again)",
r'''            try:                                   # baselines for the live-loss stop (10c)
''',
r'''            # LOSS_STOPPED used to keep an id for the life of the process, so a bot promoted again
            # under the same id was never judged by the live-loss stop (10e)
            LOSS_STOPPED.intersection_update(bots)
            for gone in [b for b in LOSS_RETRY if b not in bots]:
                LOSS_RETRY.pop(gone, None)
            try:                                   # baselines for the live-loss stop (10c)
''',
"LOSS_STOPPED.intersection_update(bots)"),

("one unreadable directory in bots/live no longer ends the round for every bot after it",
r'''                with open(f"{LIVE}/{bot}/manifest.yaml", encoding="utf-8") as f:
                    chains = manifest_chains(f.read())   # every YAML list style, like the gate (9i)
''',
r'''                try:
                    with open(f"{LIVE}/{bot}/manifest.yaml", encoding="utf-8") as f:
                        chains = manifest_chains(f.read())   # every YAML list style, like the gate (9i)
                except OSError as exc:
                    # this used to raise out of the loop: every bot sorted after this directory, and
                    # the daily-loss check, were skipped on every round (10e)
                    if bot not in UNREADABLE:
                        UNREADABLE.add(bot)
                        print(f"watchdog: {bot}: manifest.yaml unreadable ({exc!r}); this directory is NOT monitored",
                              file=sys.stderr)
                    continue
''',
"this directory is NOT monitored"),

("an unfinished live-loss stop becomes due again after LOSS_RETRY_S",
r'''                seen_vals, all_read = {}, True      # for the live-loss stop (10c)
''',
r'''                seen_vals, all_read = {}, True      # for the live-loss stop (10c)
                if bot in LOSS_RETRY and LOSS_RETRY[bot][1] <= time.monotonic():
                    LOSS_STOPPED.discard(bot)               # the stop did not finish: due again (10e)
''',
"the stop did not finish: due again (10e)"),

("live-loss stop: check that the stop finished; retry and say so when it did not",
r'''                        LOSS_STOPPED.add(bot)
                        subprocess.run(["/opt/farm/bin/gate-ctl", "stop", bot], check=False)
                        wake("bot's loss since promotion passed the live-loss stop, stopped it",
                             f"bot: {bot}\nloss since promotion: {loss:.2f} USD (limit {max_live_loss:.0f} USD; "
                             f"funded native + USDC minus wallet now, current prices)\nchains: {', '.join(chains)}")
''',
r'''                        LOSS_STOPPED.add(bot)
                        subprocess.run(["/opt/farm/bin/gate-ctl", "stop", bot], check=False)
                        # gate stop archives the bot only once its funds are back; while the directory
                        # is still here the stop is unfinished (service stopped, sweep incomplete) and
                        # is tried again every LOSS_RETRY_S. It used to be tried exactly once (10e).
                        done = not os.path.isdir(f"{LIVE}/{bot}")
                        tries = LOSS_RETRY.get(bot, (0, 0))[0] + 1
                        if done:
                            LOSS_RETRY.pop(bot, None)
                        else:
                            LOSS_RETRY[bot] = (tries, time.monotonic() + LOSS_RETRY_S)
                        if done or tries == 1 or tries % 6 == 0:
                            wake("bot's loss since promotion passed the live-loss stop, "
                                 + ("stopped it" if done else "its service is stopped but the sweep is NOT finished"),
                                 f"bot: {bot}\nloss since promotion: {loss:.2f} USD (limit {max_live_loss:.0f} USD; "
                                 f"funded native + USDC minus wallet now, current prices)\nchains: {', '.join(chains)}"
                                 + ("" if done else f"\n\n`gate stop {bot}` did not finish (try {tries}); the watchdog repeats it "
                                    f"every {LOSS_RETRY_S // 60} min. See the sweep_failed / stop_incomplete records in gate.log."))
''',
"done = not os.path.isdir(f\"{LIVE}/{bot}\")"),
]

FILES = [("gate-ctl", GATE), ("farm-signer", SIGNER), ("farm-watchdog", WATCHDOG)]


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
    if len(argv) == 4 and argv[0] == "check":
        out = None
    elif len(argv) == 5 and argv[0] == "apply":
        out = argv[4]
    else:
        sys.exit(__doc__)
    results = []
    for path, (name, hunks) in zip(argv[1:4], FILES):
        with open(path, encoding="utf-8") as f:
            results.append((name, patch(f.read(), hunks, name)))
    if out:
        for name, text in results:
            with open(os.path.join(out, name), "w", encoding="utf-8") as f:
                f.write(text)


if __name__ == "__main__":
    main(sys.argv[1:])
