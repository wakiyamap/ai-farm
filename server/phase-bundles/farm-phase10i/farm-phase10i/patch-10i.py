#!/usr/bin/env python3
"""Phase 10i: exact-text patches that cut the farm's own Alchemy use on the live lane.

  patch-10i.py check <farm-watchdog> <farm-dash>
  patch-10i.py apply <farm-watchdog> <farm-dash> <outdir>

Every old text must occur exactly once in its file, or nothing is written. Safe to re-run (markers).
"""
import os
import sys

WATCHDOG = [
("how often balances are read: gate.json watchdog_balance_interval_s (default: every round, as before)",
'''    url, interval = cfg["relay_url"], cfg["watchdog_interval_s"]
''',
'''    url, interval = cfg["relay_url"], cfg["watchdog_interval_s"]
    # 10i: the nonce is read every round; balance, USDC and price every bal_every rounds. With four
    # live bots the watchdog alone used about 2.1M Alchemy CU a day reading all four every 15 s.
    bal_every = max(1, round(float(cfg.get("watchdog_balance_interval_s", interval)) / interval))
    round_no = -1
''',
"bal_every = max(1, round("),

("a round counter and one price read per feed and round",
'''    while True:
        try:
            bots = sorted(d for d in os.listdir(LIVE)''',
'''    while True:
        round_no += 1
        prices = {}                                # (feed chain, feed) -> price, for this round (10i)
        try:
            bots = sorted(d for d in os.listdir(LIVE)''',
"prices = {}                                # (feed chain, feed)"),

("nonce every round; balance, USDC and price when due, when the nonce moved, the first time, or after a failed read",
'''                    try:
                        bal = int(rpc(url, chain, "eth_getBalance", [addr, "latest"]), 16)
                        nonce = int(rpc(url, chain, "eth_getTransactionCount", [addr, "latest"]), 16)
                        price = int(rpc(url, feed_chain(chain), "eth_call", [{"to": ETH_USD_FEED[chain], "data": farmkeys.selector("latestAnswer()")}, "latest"]), 16) / 1e8
                        if not price_ok(chain, price):
                            raise RuntimeError(f"implausible native/USD price {price}")
                        token = (cfg.get("usdc") or {}).get(chain)
                        usdc = 0
                        if token:
                            r = rpc(url, chain, "eth_call", [{"to": token, "data": farmkeys.encode_call("balanceOf(address)", addr)}, "latest"])
                            usdc = int(r, 16) if r and r != "0x" else 0
''',
'''                    try:
                        nonce = int(rpc(url, chain, "eth_getTransactionCount", [addr, "latest"]), 16)
                        prev = last.get((bot, chain))
                        # A wallet's native balance cannot fall without a transaction of its own, so a
                        # moved nonce triggers a full read at once; USDC can also be pulled by an
                        # approved spender, which the periodic read catches (10i).
                        full = (prev is None or round_no % bal_every == 0 or nonce > prev[1]
                                or (bot, chain) in READ_FAILED)
                        if full:
                            bal = int(rpc(url, chain, "eth_getBalance", [addr, "latest"]), 16)
                            fkey = (feed_chain(chain), ETH_USD_FEED[chain])
                            if fkey not in prices:
                                prices[fkey] = int(rpc(url, fkey[0], "eth_call", [{"to": fkey[1], "data": farmkeys.selector("latestAnswer()")}, "latest"]), 16) / 1e8
                            price = prices[fkey]
                            if not price_ok(chain, price):
                                raise RuntimeError(f"implausible native/USD price {price}")
                            token = (cfg.get("usdc") or {}).get(chain)
                            usdc = 0
                            if token:
                                r = rpc(url, chain, "eth_call", [{"to": token, "data": farmkeys.encode_call("balanceOf(address)", addr)}, "latest"])
                                usdc = int(r, 16) if r and r != "0x" else 0
                        else:
                            bal, usdc, price = prev[0], prev[2], None
''',
"full = (prev is None or round_no % bal_every == 0"),

("prev is read before the RPC calls now",
'''                    prev = last.get((bot, chain))
                    if prev:
                        pbal, pnonce, pusdc = prev
''',
'''                    # prev was read above, before the RPC calls (10i)
                    if prev:
                        pbal, pnonce, pusdc = prev
''',
"prev was read above, before the RPC calls"),

("the drop check runs on the rounds that read the balance",
'''                        drop_usd = (pbal - bal) / 1e18 * price + (pusdc - usdc) / usdc_scale(chain)
                        if drop_usd > cfg["max_loss_per_tx_usd"] and not halted:
                            subprocess.run(["/opt/farm/bin/gate-ctl", "stop", bot], check=False)
                            wake("bot lost more than L in one interval, stopped it",
                                 f"bot: {bot}\\nchain: {chain}\\ndrop: {drop_usd:.2f} USD (native + USDC) in {interval}s")
                    last[(bot, chain)] = (bal, nonce, usdc)
                    seen_vals[chain] = (bal, usdc, price)
''',
'''                        drop_usd = ((pbal - bal) / 1e18 * price + (pusdc - usdc) / usdc_scale(chain)) if full else 0.0
                        if drop_usd > cfg["max_loss_per_tx_usd"] and not halted:
                            subprocess.run(["/opt/farm/bin/gate-ctl", "stop", bot], check=False)
                            wake("bot lost more than L between two balance reads, stopped it",
                                 f"bot: {bot}\\nchain: {chain}\\ndrop: {drop_usd:.2f} USD (native + USDC) since the last "
                                 f"balance read (every {bal_every * interval}s, and whenever the nonce moves)")
                    last[(bot, chain)] = (bal, nonce, usdc)
                    if full:
                        seen_vals[chain] = (bal, usdc, price)
''',
"between two balance reads, stopped it"),

("the live-loss stop judges a bot on the rounds that read every chain's balance",
'''                if chains and all_read and pnl_now is not None and not halted and bot not in LOSS_STOPPED \\
''',
'''                if chains and all_read and len(seen_vals) == len(chains) and pnl_now is not None and not halted and bot not in LOSS_STOPPED \\
''',
"all_read and len(seen_vals) == len(chains)"),
]

DASH = [
("gate status is cached for 5 minutes for the page (it reads every chain; an open tab refreshed it every minute)",
'''def gate_status():
    import time as _t
    if _gate_cache["v"] is not None and _t.monotonic() - _gate_cache["t"] < 60:
        return _gate_cache["v"]
''',
'''def gate_status(max_age=300):
    # 10i: `gate-ctl status` reads balances, USDC and prices on every chain (about 900 Alchemy CU).
    # With the page open and refreshing, a 60 s cache meant about 1.3M CU a day.
    import time as _t
    if _gate_cache["v"] is not None and _t.monotonic() - _gate_cache["t"] < max_age:
        return _gate_cache["v"]
''',
"def gate_status(max_age=300):"),

("collect() takes the allowed age of the gate data",
'''def collect():
    return {''',
'''def collect(gate_max_age=300):
    return {''',
"def collect(gate_max_age=300):"),

("collect() passes it on",
'''        "gate": gate_status(),
''',
'''        "gate": gate_status(gate_max_age),
''',
"gate_status(gate_max_age),"),

("brief.txt (Copy for Claude) still gets gate data at most 60 s old",
'''            d = collect()
            if self.path.startswith("/data.json"):''',
'''            d = collect(60 if self.path.startswith("/brief.txt") else 300)
            if self.path.startswith("/data.json"):''',
'collect(60 if self.path.startswith("/brief.txt") else 300)'),

("the page says how old the balances can be",
'''· refreshes every 30 s</span>''',
'''· refreshes every 30 s, balances every 5 min (fresh in brief.txt)</span>''',
"balances every 5 min (fresh in brief.txt)"),
]


def plan(text, hunks):
    lines = []
    for title, old, new, marker in hunks:
        if marker in text:
            lines.append(f"  already applied: {title}")
            continue
        n = text.count(old)
        if n != 1:
            raise ValueError(f"{title}: the expected text occurs {n} times (must be exactly 1); nothing was changed")
        text = text.replace(old, new)
        lines.append(f"  ok: {title}")
    return text, lines


def main(argv):
    if len(argv) < 3 or argv[0] not in ("check", "apply") or (argv[0] == "apply" and len(argv) != 4):
        sys.exit(__doc__)
    outs = []
    for path, hunks in ((argv[1], WATCHDOG), (argv[2], DASH)):
        with open(path, encoding="utf-8") as f:
            text = f.read()
        try:
            out, lines = plan(text, hunks)
        except ValueError as exc:
            sys.exit(f"patch-10i: {os.path.basename(path)}: {exc}")
        print(f"{os.path.basename(path)}:")
        print("\n".join(lines))
        outs.append((os.path.basename(path), out))
    if argv[0] == "apply":
        for name, out in outs:
            with open(os.path.join(argv[3], name), "w", encoding="utf-8") as f:
                f.write(out)


if __name__ == "__main__":
    main(sys.argv[1:])
