#!/usr/bin/env python3
"""Phase 9i: exact-text patches for the installed gate-ctl and farm-watchdog.

  patch-9i.py check <gate-ctl> <farm-watchdog>          every hunk applies (or is already applied)
  patch-9i.py apply <gate-ctl> <farm-watchdog> <outdir> write patched copies to <outdir>

Each hunk is applied only when its old text occurs exactly once; a hunk whose marker is already
present counts as applied (re-running is safe). Anything else stops before writing a byte.
"""
import os
import sys

GATE = []
WATCHDOG = []

# --- gate-ctl ---------------------------------------------------------------------------------

GATE.append(("poll_receipt: the first wait_receipt was shadowed by the second (sweep TypeError)",
"""    def wait_receipt(self, chain, txhash, timeout_s=120):
        import time
        t0 = time.monotonic()
""",
"""    def poll_receipt(self, chain, txhash, timeout_s=120):
        \"\"\"Receipt or None after timeout_s; never exits, the caller checks the status.
        (Until 9i this was a second `wait_receipt`, shadowed by the promote one below, so the
        USDC sweep raised TypeError right after broadcasting the transfer.)\"\"\"
        import time
        t0 = time.monotonic()
""",
"def poll_receipt(self, chain, txhash, timeout_s=120):"))

GATE.append(("pnl(): keep usdc_in_flight across the UTC day change",
"""            p = {"day": day, "realized_usd": {}, "baseline": p.get("baseline", {}), "baseline_usdc": p.get("baseline_usdc", {})}
""",
"""            p = {"day": day, "realized_usd": {}, "baseline": p.get("baseline", {}), "baseline_usdc": p.get("baseline_usdc", {}),
                 "usdc_in_flight": p.get("usdc_in_flight", {})}
""",
'"usdc_in_flight": p.get("usdc_in_flight", {})}'))

GATE.append(("promote: the pre-check asks for what will be sent (gas_wallet_cap_usd), not the uncapped share",
"""        for chain in chains:
            wei = int(per_chain / self.eth_usd(chain) * 1e18)
            if self.balance_wei(chain, inter) < wei + 10**15:
                die(f"intermediate wallet on {chain} has less than {per_chain:.2f} USD + gas; deposit first")
""",
"""        for chain in chains:
            # check what will actually be sent: on a capped chain (gas_wallet_cap_usd) the funding
            # below never exceeds the cap, so the intermediate wallet need not hold the full share
            wanted = int(per_chain / self.eth_usd(chain) * 1e18)
            wei = self.capped_wei(chain, bot_addr, wanted)
            if self.balance_wei(chain, inter) < wei + 10**15:
                note = (f" (capital share {per_chain:.2f} USD, capped by the {self.gas_cap_usd(chain)} USD gas wallet cap)"
                        if wei < wanted else "")
                die(f"intermediate wallet on {chain} has less than {wei / 1e18 * self.eth_usd(chain):.2f} USD{note} + gas; deposit first")
""",
"wei = self.capped_wei(chain, bot_addr, wanted)"))

GATE.append(("sweep: settle an earlier USDC transfer whose receipt did not come back before touching the chain",
"""            fees = (int(fees[0] * 1.2), fees[1])        # margin for base fee moving between calls
            # 1. USDC back to the intermediate wallet (before the native sweep: the transfer needs gas)
            uraw = self.usdc_raw(chain, bot_addr)
""",
"""            fees = (int(fees[0] * 1.2), fees[1])        # margin for base fee moving between calls
            if self.settle_usdc_in_flight(p, bot_id, chain, record_pnl) == "pending":
                log(op="sweep_failed", bot=bot_id, chain=chain, why="an earlier USDC sweep transfer is still unresolved")
                swept[chain + ":usdc"] = "failed: earlier transfer still pending"
                all_ok = False
                continue
            # 1. USDC back to the intermediate wallet (before the native sweep: the transfer needs gas)
            uraw = self.usdc_raw(chain, bot_addr)
""",
'if self.settle_usdc_in_flight(p, bot_id, chain, record_pnl) == "pending":'))

GATE.append(("sweep: gas top-up uses poll_receipt and checks the status",
"""                    if not self.wait_receipt(chain, th):
                        log(op="sweep_failed", bot=bot_id, chain=chain, why="gas top-up not mined in time")
                        swept[chain + ":usdc"] = "failed: gas top-up pending"
""",
"""                    tr = self.poll_receipt(chain, th)
                    if not tr or tr.get("status") != "0x1":
                        state = "pending" if not tr else "reverted"
                        log(op="sweep_failed", bot=bot_id, chain=chain, why=f"gas top-up {state}", txHash=th)
                        swept[chain + ":usdc"] = f"failed: gas top-up {state}"
""",
"tr = self.poll_receipt(chain, th)"))

GATE.append(("sweep: USDC transfer is logged with its nonce before waiting; pending -> in flight, reverted -> failed",
"""                try:
                    uh, _ = self.send_usdc(chain, label, inter, uraw, fees=fees)
                except RuntimeError as exc:
                    log(op="sweep_failed", bot=bot_id, chain=chain, why=f"usdc: {exc}")
                    swept[chain + ":usdc"] = f"failed: {exc}"
                    all_ok = False
                    continue
                if not self.wait_receipt(chain, uh):
                    log(op="sweep_failed", bot=bot_id, chain=chain, why="usdc transfer not mined in time")
                    swept[chain + ":usdc"] = "failed: pending"
                    all_ok = False
                    continue
""",
"""                try:
                    un = self.nonce(chain, bot_addr)    # send_usdc signs with this same pending nonce
                    uh, _ = self.send_usdc(chain, label, inter, uraw, fees=fees)
                except RuntimeError as exc:
                    log(op="sweep_failed", bot=bot_id, chain=chain, why=f"usdc: {exc}")
                    swept[chain + ":usdc"] = f"failed: {exc}"
                    all_ok = False
                    continue
                # recorded before waiting: the watchdog must know this bot-key nonce even when the
                # receipt does not come back while we wait
                log(op="sweep_usdc_sent", bot=bot_id, chain=chain, usdc=uraw, txHash=uh, nonce=un)
                ur = self.poll_receipt(chain, uh, timeout_s=180)
                if not ur:
                    # not booked either way: the next sweep settles it from the receipt instead of
                    # reading the then-empty wallet as "principal gone" (a phantom loss)
                    p.setdefault("usdc_in_flight", {}).setdefault(bot_id, {})[chain] = {"txHash": uh, "usdc": uraw, "nonce": un}
                    log(op="sweep_failed", bot=bot_id, chain=chain, why="usdc transfer not mined in time; next sweep settles it",
                        txHash=uh, nonce=un)
                    swept[chain + ":usdc"] = "failed: pending (in flight)"
                    all_ok = False
                    continue
                if ur.get("status") != "0x1":
                    log(op="sweep_failed", bot=bot_id, chain=chain, why="usdc transfer reverted", txHash=uh, nonce=un)
                    swept[chain + ":usdc"] = "failed: reverted"
                    all_ok = False
                    continue
""",
'log(op="sweep_usdc_sent", bot=bot_id, chain=chain, usdc=uraw, txHash=uh, nonce=un)'))

GATE.append(("sweep: sweep_usdc record carries the nonce we signed with",
"""                log(op="sweep_usdc", bot=bot_id, chain=chain, usdc=uraw, usd=uusd, txHash=uh, nonce=self.tx_nonce(chain, uh))
""",
"""                log(op="sweep_usdc", bot=bot_id, chain=chain, usdc=uraw, usd=uusd, txHash=uh, nonce=un)
""",
"usdc=uraw, usd=uusd, txHash=uh, nonce=un)"))

GATE.append(("sweep: native transfer signs with a nonce read first (no lookup by hash afterwards)",
"""            try:
                h, _ = self.send_eth(chain, label, inter, bal - cost, fees=fees)
            except RuntimeError as exc:
""",
"""            try:
                n = self.nonce(chain, bot_addr)
                h, _ = self.send_eth(chain, label, inter, bal - cost, nonce=n, fees=fees)
            except RuntimeError as exc:
""",
"h, _ = self.send_eth(chain, label, inter, bal - cost, nonce=n, fees=fees)"))

GATE.append(("sweep: native sweep record carries that nonce",
"""            log(op="sweep", bot=bot_id, chain=chain, wei=bal - cost, usd=usd, txHash=h, nonce=self.tx_nonce(chain, h))
""",
"""            log(op="sweep", bot=bot_id, chain=chain, wei=bal - cost, usd=usd, txHash=h, nonce=n)
""",
"wei=bal - cost, usd=usd, txHash=h, nonce=n)"))

GATE.append(("settle_usdc_in_flight(): new helper",
"""    def cancel_pending(self, bot_id):
""",
"""    def settle_usdc_in_flight(self, p, bot_id, chain, record_pnl=True):
        \"\"\"A USDC sweep transfer whose receipt had not come back (9i). Returns 'none' (nothing in
        flight), 'pending' (still unresolved: touch nothing on this chain) or 'done' (settled from
        the receipt: mined -> PnL booked against baseline_usdc; reverted -> the USDC is still in
        the bot wallet and the normal sweep moves it).\"\"\"
        fl = p.get("usdc_in_flight", {}).get(bot_id, {}).get(chain)
        if not fl:
            return "none"
        r = self.poll_receipt(chain, fl["txHash"], timeout_s=10)
        if not r:
            return "pending"
        p["usdc_in_flight"][bot_id].pop(chain, None)
        if not p["usdc_in_flight"][bot_id]:
            p["usdc_in_flight"].pop(bot_id, None)
        if r.get("status") != "0x1":
            log(op="sweep_usdc_inflight", bot=bot_id, chain=chain, txHash=fl["txHash"], nonce=fl.get("nonce"),
                note="reverted; the USDC is still in the bot wallet")
            return "done"
        ubase = p.get("baseline_usdc", {}).get(bot_id, {}).get(chain)
        uusd = None
        if record_pnl and ubase is not None:
            uusd = round((fl["usdc"] - ubase) / 1e6, 4)
            p["realized_usd"][bot_id] = p["realized_usd"].get(bot_id, 0.0) + uusd
            p["baseline_usdc"][bot_id].pop(chain, None)
        log(op="sweep_usdc_inflight", bot=bot_id, chain=chain, usdc=fl["usdc"], usd=uusd, txHash=fl["txHash"],
            nonce=fl.get("nonce"), note="mined")
        return "done"

    def cancel_pending(self, bot_id):
""",
"def settle_usdc_in_flight(self, p, bot_id, chain, record_pnl=True):"))

GATE.append(("stop --all: one bot's exception no longer leaves the rest running",
"""            try:
                self.stop(bot)
            except SystemExit:
                pass
""",
"""            try:
                self.stop(bot)
            except SystemExit:
                pass
            except Exception as exc:                  # one bot's failure must not leave the others running
                log(op="stop_failed", bot=bot, why=repr(exc))
                print(f"gate: stop {bot} failed: {exc!r}", file=sys.stderr)
""",
'log(op="stop_failed", bot=bot, why=repr(exc))'))

# --- farm-watchdog ----------------------------------------------------------------------------

WATCHDOG.append(("manifest parsing helpers (same rules as gate-ctl / farm-signer since 9e)",
"""def rpc(url, chain, method, params):
""",
"""def manifest_block(text, key):
    \"\"\"Lines of a top-level manifest key (same rules as gate-ctl since 9e): inline lists, block
    lists and lists of mappings; comments stripped.\"\"\"
    out, inside = [], False
    for raw in text.splitlines():
        line = raw.split(" #", 1)[0].rstrip() if not raw.lstrip().startswith("#") else ""
        if not line.strip():
            continue
        if not line[0].isspace() and not line.startswith("-"):
            inside = line.split(":", 1)[0].strip() == key
            if inside:
                out.append(line.split(":", 1)[1] if ":" in line else "")
            continue
        if inside:
            out.append(line)
    return out


def manifest_chains(text):
    vals = []
    for line in manifest_block(text, "chains"):
        s = line.strip()
        if s.startswith("["):
            vals += [v.strip().strip("'\\"") for v in s.strip("[]").split(",") if v.strip()]
        elif s.startswith("- "):
            vals.append(s[2:].strip().strip("'\\""))
        elif s and not vals and "," not in s:
            vals.append(s.strip("'\\""))
    return [c for c in vals if c in CHAIN_IDS]


UNREADABLE = set()   # live bots whose manifest names no known chain (reported once)


def rpc(url, chain, method, params):
""",
"def manifest_chains(text):"))

WATCHDOG.append(("known gate nonces include sweep_usdc_sent",
"""r.get("op") in ("sweep", "sweep_usdc", "cancel", "deploy_executor_sent", "deploy_executor")""",
"""r.get("op") in ("sweep", "sweep_usdc", "sweep_usdc_sent", "cancel", "deploy_executor_sent", "deploy_executor")""",
'"sweep_usdc_sent", "cancel"'))

WATCHDOG.append(("chains read with every YAML list style (block lists were silently unmonitored)",
"""                chains = []
                with open(f"{LIVE}/{bot}/manifest.yaml", encoding="utf-8") as f:
                    for line in f:
                        if line.startswith("chains:"):
                            chains = [c.strip().strip('"') for c in line.split(":", 1)[1].strip().strip("[]").split(",") if c.strip() in CHAIN_IDS]
""",
"""                with open(f"{LIVE}/{bot}/manifest.yaml", encoding="utf-8") as f:
                    chains = manifest_chains(f.read())   # every YAML list style, like the gate (9i)
                if not chains and bot not in UNREADABLE:
                    UNREADABLE.add(bot)
                    print(f"watchdog: {bot}: manifest.yaml names no known chain; this bot is NOT monitored", file=sys.stderr)
""",
"chains = manifest_chains(f.read())   # every YAML list style, like the gate (9i)"))


def patch(text, hunks, name):
    for title, old, new, marker in hunks:
        if marker in text:
            print(f"  {name}: already applied: {title}")
            continue
        n = text.count(old)
        if n != 1:
            raise SystemExit(f"{name}: cannot apply '{title}': old text found {n} times (expected 1). "
                             "The installed file differs from phase 9g; nothing was changed.")
        text = text.replace(old, new)
        if marker not in text:
            raise SystemExit(f"{name}: internal error: marker missing after '{title}'")
        print(f"  {name}: applied: {title}")
    return text


def main(argv):
    if len(argv) < 3 or argv[0] not in ("check", "apply"):
        raise SystemExit(__doc__)
    mode, gate, wd = argv[0], argv[1], argv[2]
    out_gate = patch(open(gate, encoding="utf-8").read(), GATE, "gate-ctl")
    out_wd = patch(open(wd, encoding="utf-8").read(), WATCHDOG, "farm-watchdog")
    if mode == "apply":
        outdir = argv[3]
        os.makedirs(outdir, exist_ok=True)
        for content, base in ((out_gate, "gate-ctl"), (out_wd, "farm-watchdog")):
            with open(os.path.join(outdir, base), "w", encoding="utf-8") as f:
                f.write(content)
    print(f"patch-9i: {mode} ok")


if __name__ == "__main__":
    main(sys.argv[1:])
