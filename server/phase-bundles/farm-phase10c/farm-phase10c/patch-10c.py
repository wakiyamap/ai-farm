#!/usr/bin/env python3
"""Phase 10c: exact-text patches - the watchdog enforces the 30 USD live-loss stop, common.md says so.

  patch-10c.py check <farm-watchdog> <common.md>
  patch-10c.py apply <farm-watchdog> <common.md> <outdir>

Every old text must occur exactly once, or nothing is written. Safe to re-run (markers).
"""
import os
import sys

WATCHDOG = [
("docstring: the live-loss stop",
'''  - native + USDC balance dropped by more than L since last check -> stop that bot, wake
''',
'''  - native + USDC balance dropped by more than L since last check -> stop that bot, wake
  - loss since promotion (pnl.json baselines minus wallet value) > max_live_loss_usd (30)
                                                                  -> stop that bot, wake (10c)
''',
"-> stop that bot, wake (10c)"),
("LOSS_STOPPED / NO_BASELINE sets",
'''READ_FAILED = set()  # (bot, chain) whose reads failed; reported once until they read again (10b)
''',
'''READ_FAILED = set()  # (bot, chain) whose reads failed; reported once until they read again (10b)
LOSS_STOPPED = set()  # bots the live-loss stop has stopped (10c)
NO_BASELINE = set()   # live bots without a pnl.json baseline: live-loss stop impossible (reported once)


def live_loss_usd(pnl, bot, vals):
    """Loss since promotion in USD (10c): what the gate funded - pnl.json `baseline` (native wei)
    and `baseline_usdc` (raw units) per chain, which include later `gate fund` and sweep gas
    top-ups - minus what the bot wallet holds now, valued at the current native/USD price.
    `vals` = {chain: (native_wei, usdc_raw, price)}. None when the bot has no baseline. Value the
    bot keeps outside its wallet (an executor, a vault) counts as lost: conservative on purpose."""
    base = (pnl.get("baseline") or {}).get(bot)
    if base is None:
        return None
    ubase = (pnl.get("baseline_usdc") or {}).get(bot) or {}
    loss = 0.0
    for chain, (bal, usdc, price) in vals.items():
        loss += (base.get(chain, 0) - bal) / 1e18 * price
        loss += (ubase.get(chain, 0) - usdc) / usdc_scale(chain)
    return loss
''',
"def live_loss_usd(pnl, bot, vals):"),
("each loop reads pnl.json baselines and the limit",
'''            halted = os.path.exists(f"{STATE}/halt")
''',
'''            halted = os.path.exists(f"{STATE}/halt")
            try:                                   # baselines for the live-loss stop (10c)
                with open(f"{STATE}/pnl.json", encoding="utf-8") as f:
                    pnl_now = json.load(f)
            except (OSError, ValueError):
                pnl_now = None
            max_live_loss = float(cfg.get("max_live_loss_usd", 30))
''',
"baselines for the live-loss stop (10c)"),
("per bot: collect every chain's reading",
'''                for chain in chains:
                    try:
''',
'''                seen_vals, all_read = {}, True      # for the live-loss stop (10c)
                for chain in chains:
                    try:
''',
"seen_vals, all_read = {}, True"),
("a failed chain read skips the live-loss check for that bot this round",
'''                    except Exception as exc:              # noqa: BLE001 - keep watching the other chains (10b)
''',
'''                    except Exception as exc:              # noqa: BLE001 - keep watching the other chains (10b)
                        all_read = False
''',
"                        all_read = False\n"),
("live-loss stop after all chains of the bot are read",
'''                    last[(bot, chain)] = (bal, nonce, usdc)
''',
'''                    last[(bot, chain)] = (bal, nonce, usdc)
                    seen_vals[chain] = (bal, usdc, price)
                # live-loss stop (10c): the whole loss since promotion, not one interval's drop
                if chains and all_read and pnl_now is not None and not halted and bot not in LOSS_STOPPED \\
                        and os.path.isdir(f"{LIVE}/{bot}"):
                    loss = live_loss_usd(pnl_now, bot, seen_vals)
                    if loss is None:
                        if bot not in NO_BASELINE:
                            NO_BASELINE.add(bot)
                            print(f"watchdog: {bot}: no baseline in pnl.json; the live-loss stop cannot judge it",
                                  file=sys.stderr)
                    elif loss > max_live_loss:
                        LOSS_STOPPED.add(bot)
                        subprocess.run(["/opt/farm/bin/gate-ctl", "stop", bot], check=False)
                        wake("bot's loss since promotion passed the live-loss stop, stopped it",
                             f"bot: {bot}\\nloss since promotion: {loss:.2f} USD (limit {max_live_loss:.0f} USD; "
                             f"funded native + USDC minus wallet now, current prices)\\nchains: {', '.join(chains)}")
''',
"live-loss stop (10c): the whole loss since promotion"),
]

COMMON = [
("hard constraint: the watchdog's live-loss stop",
'''- **T / R / M**: ''',
'''- **Live-loss stop**: the watchdog stops a live bot (`gate stop`, which sweeps it back) once its loss since promotion passes 30 USD: what the gate funded (native and USDC, later top-ups included) minus what the bot's wallet holds now, at current prices. This is enforced in code, so a bot does not need crash-proof loss accounting of its own to be promoted; a simple self-stop is still welcome. Keep profit and principal in the bot's wallet, or have the executor return them there: value left in an executor or elsewhere counts as lost.
- **T / R / M**: ''',
"- **Live-loss stop**: the watchdog stops"),
]

FILES = [("farm-watchdog", WATCHDOG), ("common.md", COMMON)]


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
    if len(argv) == 3 and argv[0] == "check":
        out = None
    elif len(argv) == 4 and argv[0] == "apply":
        out = argv[3]
    else:
        sys.exit(__doc__)
    results = []
    for path, (name, hunks) in zip(argv[1:3], FILES):
        with open(path, encoding="utf-8") as f:
            results.append((name, patch(f.read(), hunks, name)))
    if out:
        for name, text in results:
            with open(os.path.join(out, name), "w", encoding="utf-8") as f:
                f.write(text)


if __name__ == "__main__":
    main(sys.argv[1:])
