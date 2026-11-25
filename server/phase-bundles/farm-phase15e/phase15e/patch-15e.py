#!/usr/bin/env python3
"""Phase 15e text patches.

  patch-15e.py check <rpc-relay> <farm-watchdog>
  patch-15e.py apply <rpc-relay> <farm-watchdog> <outdir>

The watchdog read every live bot's nonce every 15 s and its balance, USDC and price every 60 s on
the live lane (Alchemy first, no budget): about 180k CU a day per live bot. With 23 live bots that
is about 4M CU a day, and the Alchemy cycle was on course to run out before 12-01 (when it does,
every send stops). On 11-18 the live lane used 882k CU by 03:35 UTC.

rpc-relay
  - lane `watch`: public nodes first, Alchemy as fallback within relay.json alchemy_daily_cu.watch
    (like research). Any user may ask for it.
  - /health cycle: also projects from the recent pace (today so far, scaled, or yesterday,
    whichever is higher) - `pace_cu_per_day`, `projected_cu_recent` - and `projected_share` /
    `alert_85` use the higher of the two projections. The cycle average lagged a jump in use.
farm-watchdog
  - reads through lane `watch` instead of `live`. Its checks and intervals are unchanged.
"""
import sys

RELAY = [
    ('LANES = ("live", "paper", "research", "fork", "scout")     # fork, scout: 15c\n',
     'LANES = ("live", "paper", "research", "fork", "scout", "watch")     # fork, scout: 15c; watch: 15e\n'),
    ('''    proj = round(total + total / days * (end - now).total_seconds() / 86400) if total and days >= 0.5 else None
    share = round(proj / allowance, 3) if proj and allowance else None
    return {"since": since.strftime("%Y-%m-%d"), "ends": end.strftime("%Y-%m-%d"), "cu": total, "lanes": lanes,
            "allowance": allowance, "projected_cu": proj, "projected_share": share,
            "alert_85": bool(share and share > 0.85)}
''',
     '''    proj = round(total + total / days * (end - now).total_seconds() / 86400) if total and days >= 0.5 else None
    # 15e: the cycle average lags a jump in use; project from the recent pace too (today so far,
    # scaled to a day once 2 h have passed, or yesterday, whichever is higher)
    pace = None
    try:
        con = _sq.connect(f"file:{db}?mode=ro", uri=True, timeout=5)
        try:
            per_day = dict(con.execute("SELECT day, sum(cu) FROM rpc_stats WHERE provider='alchemy' AND day>=? GROUP BY 1",
                                       ((now - dt.timedelta(days=1)).strftime("%Y-%m-%d"),)).fetchall())
        finally:
            con.close()
        elapsed = (now - now.replace(hour=0, minute=0, second=0, microsecond=0)).total_seconds() / 86400
        rates = []
        if elapsed >= 2 / 24 and per_day.get(now.strftime("%Y-%m-%d")):
            rates.append(per_day[now.strftime("%Y-%m-%d")] / elapsed)
        if per_day.get((now - dt.timedelta(days=1)).strftime("%Y-%m-%d")):
            rates.append(per_day[(now - dt.timedelta(days=1)).strftime("%Y-%m-%d")])
        pace = max(rates) if rates else None
    except _sq.Error:
        pass
    proj_recent = round(total + pace * (end - now).total_seconds() / 86400) if pace else None
    worst = max([p for p in (proj, proj_recent) if p] or [0]) or None
    share = round(worst / allowance, 3) if worst and allowance else None
    return {"since": since.strftime("%Y-%m-%d"), "ends": end.strftime("%Y-%m-%d"), "cu": total, "lanes": lanes,
            "allowance": allowance, "projected_cu": proj, "pace_cu_per_day": round(pace) if pace else None,
            "projected_cu_recent": proj_recent, "projected_share": share,
            "alert_85": bool(share and share > 0.85)}
'''),
]

WATCHDOG = [
    ('f"{url}/{chain}?lane=live"', 'f"{url}/{chain}?lane=watch"'),
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
    if len(a) == 4 and a[1] == "check":
        patched(a[2], RELAY, True)
        patched(a[3], WATCHDOG, True)
        return print(f"  rpc-relay: {len(RELAY)} patches match, farm-watchdog: {len(WATCHDOG)} patch matches")
    if len(a) == 5 and a[1] == "apply":
        for path, pairs, name in ((a[2], RELAY, "rpc-relay"), (a[3], WATCHDOG, "farm-watchdog")):
            with open(f"{a[4]}/{name}", "w", encoding="utf-8") as f:
                f.write(patched(path, pairs))
        return print(f"  patched copies written to {a[4]}")
    sys.exit(__doc__)


if __name__ == "__main__":
    main()
