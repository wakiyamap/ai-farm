#!/usr/bin/env python3
"""Phase 15b text patches.

  patch-15b.py check <gate-ctl> <run-role>
  patch-15b.py apply <gate-ctl> <run-role> <outdir>     write patched copies into <outdir>

gate-ctl
  The executor deployment is sent through send_deploy(): it waits until the bot wallet reads at
  least the deployment's worst-case gas, and resends the same signed bytes while the node answers
  "insufficient funds" (nothing was accepted, so the nonce is still free). After one minute it gives
  up without having sent anything from the bot key (log op deploy_executor_not_sent, exit 2).
  2026-11-17 20:21Z: trial-aave-optimism's funding receipt was visible (9f waits for it), but the
  node that took the deployment still read the old balance: "insufficient funds ... have 0".
run-role
  paper-reviewer-claude may run `paper stop <id>` (to park an approved trial that only waits for a
  live trial slot; decision 2026-11-18-park-approved-trials). The codex reviewer ignores this list.
"""
import sys

GATE = [
    ("""            raw = farmkeys.sign_eip1559(priv, tx)
            h = self.rpc.call(chain, "eth_sendRawTransaction", ["0x" + raw.hex()])
            # logged before waiting for the receipt: the watchdog checks bot nonces every 15 s and
""",
     """            raw = farmkeys.sign_eip1559(priv, tx)
            # 15b: the funding receipt can be visible while the node that takes this send still reads
            # the old balance ("insufficient funds ... have 0", optimism 2026-11-17 20:21Z)
            h = self.send_deploy(bot_id, chain, frm, raw, int(gas * 1.2) * max_fee)
            # logged before waiting for the receipt: the watchdog checks bot nonces every 15 s and
"""),
    ("""    def executor_state_ok(self, bot_id):
""",
     """    DEPLOY_SEND_TRIES = 20      # one try every 3 s: one minute (15b)

    def send_deploy(self, bot_id, chain, frm, raw, need_wei):
        \"\"\"Broadcast the signed executor deployment once the bot wallet can pay for it (15b).
        Waits while the wallet reads below need_wei, and resends the same signed bytes while the node
        answers "insufficient funds" (the tx was not accepted, so its nonce is still unused). Any
        other error is raised as before. Gives up after a minute having sent nothing from the bot key.\"\"\"
        import time as _t
        last = ""
        for _ in range(self.DEPLOY_SEND_TRIES):
            try:
                have = self.balance_wei(chain, frm)
            except (RuntimeError, ValueError, OSError) as exc:
                have, last = None, f"balance unreadable: {exc}"
            if have is not None and have < need_wei:
                last = f"the bot wallet reads {have} wei, the deployment needs up to {need_wei}"
            elif have is not None:
                try:
                    return self.rpc.call(chain, "eth_sendRawTransaction", ["0x" + raw.hex()])
                except RuntimeError as exc:
                    if "insufficient funds" not in str(exc).lower():
                        raise
                    last = f"node: {exc}"
            _t.sleep(3)
        log(op="deploy_executor_not_sent", bot=bot_id, chain=chain, why=last)
        die(f"executor deployment on {chain} was not sent after {self.DEPLOY_SEND_TRIES * 3} s ({last}). "
            f"Nothing was sent from the bot key: {bot_id} is live and funded but has no executor. "
            f"Check `gate status {bot_id}`, then run `gate-ctl deploy {bot_id}`")

    def executor_state_ok(self, bot_id):
"""),
]

RUN = [
    ("Bash(gate intermediate),Bash(paper archive *),Edit(",
     "Bash(gate intermediate),Bash(paper archive *),Bash(paper stop *),Edit("),
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
    a = sys.argv
    if len(a) < 4 or a[1] not in ("check", "apply"):
        sys.exit(__doc__)
    gate, run = a[2], a[3]
    if a[1] == "check":
        patched(gate, GATE, True)
        patched(run, RUN, True)
        print(f"  gate-ctl: {len(GATE)} patches match, run-role: {len(RUN)} patch matches")
        return
    for path, pairs, name in ((gate, GATE, "gate-ctl"), (run, RUN, "run-role")):
        with open(f"{a[4]}/{name}", "w", encoding="utf-8") as f:
            f.write(patched(path, pairs))
    print(f"  patched copies written to {a[4]}")


if __name__ == "__main__":
    main()
