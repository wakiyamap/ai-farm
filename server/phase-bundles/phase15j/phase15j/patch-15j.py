#!/usr/bin/env python3
"""Phase 15j text patches of farm-dash: show the live bots' profit, not only sweeps.

  patch-15j.py check <farm-dash>
  patch-15j.py apply <farm-dash> <outdir>

"realized today" is pnl.json realized_usd, which the gate writes only when it sweeps a stopped bot.
A live bot's earnings stay in its wallet, so peapods-arb-arbitrum's +1.64 USD showed nowhere. The
gate's realized_usd (the daily-loss guard) is not touched; the dashboard adds:

1. live PnL since promotion per bot = -(loss since promotion): wallet value now minus what the gate
   funded, native valued at the current price on both sides (price moves cancel; gains and gas stay).
   Totals: all, gains, losses.
2. live PnL today (UTC) per bot = live PnL now minus a snapshot taken at 00:00 UTC by a thread in
   farm-dash (one gate status a day, ~900 CU) - or at the first request of the day if farm-dash was
   down then ("since" says when). A bot promoted after the snapshot starts at 0. The day's final total
   is kept per UTC day (14 days) in /var/lib/farmgate/dash-pnl-day.json (farmgate's own directory).
3. swept PnL all time = the sum of the gate.log sweep records (bots already stopped).
The old "realized today" stays, renamed "swept today" on the page and in the brief.
"""
import os
import sys

PAIRS = [
("imports: threading, time",
'''import sys
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
''',
'''import sys
import threading
import time
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
'''),
("live PnL helpers after live_loss()",
'''def prompt_sizes():
''',
'''DAY_FILE = "/var/lib/farmgate/dash-pnl-day.json"    # 15j: farm-dash's own live-PnL snapshot per UTC day
_day_lock = threading.Lock()


def live_pnl(ll):
    """15j: per live bot, PnL since promotion = -(loss since promotion), rounded to cents."""
    return {b: round(-x["loss_usd"], 2) for b, x in (ll or {}).items() if isinstance(x.get("loss_usd"), (int, float))}


def pnl_today(cur, now=None, path=None):
    """15j: live PnL since the UTC day's snapshot. The first call of a UTC day (the 00:00 thread, or
    the first request) closes the previous day into history and snapshots `cur`. A bot not in the
    snapshot was promoted after it and starts at 0."""
    path = path or DAY_FILE
    now = now or dt.datetime.now(dt.timezone.utc)
    day = now.strftime("%Y-%m-%d")
    with _day_lock:
        try:
            with open(path, encoding="utf-8") as f:
                s = json.load(f)
            if not isinstance(s, dict):
                s = {}
        except (OSError, ValueError):
            s = {}
        hist = s.get("history") if isinstance(s.get("history"), dict) else {}
        changed = False
        if s.get("day") != day:
            if s.get("day") and isinstance(s.get("last_total"), (int, float)):
                hist[s["day"]] = s["last_total"]
            hist = {k: hist[k] for k in sorted(hist)[-14:]}
            s = {"day": day, "since": now.strftime("%H:%M UTC"), "start": dict(cur), "history": hist}
            changed = True
        start = s.setdefault("start", {})
        for b in cur:
            if b not in start:
                start[b] = 0.0                       # promoted after the snapshot: PnL 0 at promotion
                changed = True
        by_bot = {b: round(v - start[b], 2) for b, v in cur.items()}
        total = round(sum(by_bot.values()), 2)
        if s.get("last_total") != total:
            s["last_total"] = total
            changed = True
        if changed:
            tmp = f"{path}.tmp"
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(s, f)
            os.replace(tmp, path)
    return {"since": s["since"], "by_bot": by_bot, "total": total, "history": s.get("history", {})}


def swept_total():
    """15j: PnL of every sweep in gate.log (bots already stopped), all time."""
    total = 0.0
    with open(f"{STATE}/gate.log", encoding="utf-8") as f:
        for line in f:
            try:
                r = json.loads(line)
            except ValueError:
                continue
            if isinstance(r, dict) and r.get("op") == "sweep" and isinstance(r.get("usd"), (int, float)):
                total += r["usd"]
    return round(total, 4)


def pnl_summary(d):
    """15j: one line for the brief and the tile: live PnL since promotion and today, sweeps."""
    lp = d.get("live_pnl") or {}
    t = d.get("live_pnl_today") or {}
    gains = round(sum(v for v in lp.values() if v > 0), 2)
    losses = round(sum(v for v in lp.values() if v < 0), 2)
    swept_today = round(sum((d.get("realized_today") or {}).values()), 4)
    return {"total": round(gains + losses, 2), "gains": gains, "losses": losses, "today": t.get("total", 0.0),
            "since": t.get("since", "?"), "swept_today": swept_today, "swept_total": d.get("swept_total")}


def day_snapshot_loop():
    """15j: at 00:00:20 UTC take the day's live-PnL snapshot (one fresh gate status)."""
    while True:
        now = dt.datetime.now(dt.timezone.utc)
        nxt = (now + dt.timedelta(days=1)).replace(hour=0, minute=0, second=20, microsecond=0)
        time.sleep(max(30.0, (nxt - now).total_seconds()))
        try:
            g = gate_status(60)
            g = g if isinstance(g, dict) and "error" not in g else {}
            if g:
                pnl_today(live_pnl(live_loss(g, pnl_state())))
        except Exception as exc:                     # noqa: BLE001 - the page keeps working; the first request snapshots
            print(f"farm-dash: day snapshot failed: {exc!r}", file=sys.stderr)


def prompt_sizes():
'''),
("extras: live PnL, today, swept total",
'''        "realized_today": pnl.get("realized_usd") or {},
        "sweep_pending": {k: pnl.get(k) for k in ("usdc_in_flight", "sweep_unsure") if pnl.get(k)},
        "live_loss": _safe({}, live_loss, g, pnl),
''',
'''        "realized_today": pnl.get("realized_usd") or {},
        "sweep_pending": {k: pnl.get(k) for k in ("usdc_in_flight", "sweep_unsure") if pnl.get(k)},
        "live_loss": (ll := _safe({}, live_loss, g, pnl)),
        "live_pnl": (lp := live_pnl(ll)),                                                       # 15j
        "live_pnl_today": _safe({"since": "?", "by_bot": {}, "total": 0.0, "history": {}}, pnl_today, lp) if g else
                          {"since": "?", "by_bot": {}, "total": 0.0, "history": {}},
        "swept_total": _safe(None, swept_total),
'''),
("live table: PnL since promotion and today; realized today -> swept today",
'''        today = d.get("realized_today", {}).get(r["bot"])
        out.append(dict(r, loss_since_promote_usd=loss, realized_today_usd="" if today is None else round(today, 4),
''',
'''        swept = d.get("realized_today", {}).get(r["bot"])
        pnl = d.get("live_pnl", {}).get(r["bot"])
        today = (d.get("live_pnl_today") or {}).get("by_bot", {}).get(r["bot"])
        out.append(dict(r, pnl_since_promote_usd="" if pnl is None else f"{pnl:+.2f}",           # 15j
                        pnl_today_usd="" if today is None else f"{today:+.2f}",
                        loss_since_promote_usd=loss, swept_today_usd="" if swept is None else round(swept, 4),
'''),
("brief: per-bot PnL today, summary line, swept today",
'''                                                          f"(funded {x.get('funded_usd')}, wallet {x.get('value_usd')})") + f" · nonces {nonces}")
    if d.get("realized_today"):
        L.append("realized today (UTC) " + json.dumps(d["realized_today"]))
''',
'''                                                          f"(funded {x.get('funded_usd')}, wallet {x.get('value_usd')})") + f" · nonces {nonces}"
                 + (f" · pnl today {t:+.2f}" if (t := (d.get("live_pnl_today") or {}).get("by_bot", {}).get(bot)) else ""))
    s = pnl_summary(d)                                                                          # 15j
    L.append(f"live PnL since promotion {s['total']:+.2f} USD (gains {s['gains']:+.2f}, losses {s['losses']:+.2f}) · "
             f"today (UTC, since {s['since']}) {s['today']:+.2f} · swept today {s['swept_today']:+.4f} · "
             f"swept all time {'?' if s['swept_total'] is None else format(s['swept_total'], '+.4f')}")
    winners = sorted(((v, b) for b, v in (d.get("live_pnl") or {}).items() if v > 0), reverse=True)
    if winners:
        L.append("  in profit: " + ", ".join(f"{b} {v:+.2f}" for v, b in winners))
    if d.get("realized_today"):
        L.append("swept today (UTC, gate realized_usd) " + json.dumps(d["realized_today"]))
'''),
("tile: live PnL next to today's loss",
'''        ("Today's loss", f"${g.get('daily_loss_usd', '?')}", f"limit ${g.get('max_daily_loss_usd', '?')}", gate_ok and not frozen),
''',
'''        ("Today's loss", f"${g.get('daily_loss_usd', '?')}", f"limit ${g.get('max_daily_loss_usd', '?')}", gate_ok and not frozen),
        (lambda s: ("Live PnL", f"{s['total']:+.2f}", f"today {s['today']:+.2f} · gains {s['gains']:+.2f} / losses {s['losses']:+.2f}",
                    s["total"] >= 0))(pnl_summary(d)),                                          # 15j
'''),
("sparkline title: swept PnL; live PnL by UTC day under it",
'''<section><h2>Realized PnL, 14 days (total ${e(pnl_total)})</h2>{sparkline(d['pnl'])}
<p class="muted" style="font-size:12px">{e(d['pnl'][0][0])} → {e(d['pnl'][-1][0])}; today {e(d['pnl'][-1][1])}</p></section>
''',
'''<section><h2>Swept PnL of stopped bots, 14 days (total ${e(pnl_total)})</h2>{sparkline(d['pnl'])}
<p class="muted" style="font-size:12px">{e(d['pnl'][0][0])} → {e(d['pnl'][-1][0])}; today {e(d['pnl'][-1][1])}</p>
<p class="muted" style="font-size:12px">Live PnL by UTC day (15j): {e(' · '.join(f"{k[5:]} {v:+.2f}" for k, v in sorted(((d.get('live_pnl_today') or {}).get('history') or {}).items())) or 'from 15j on')}
· today {e(format((d.get('live_pnl_today') or {}).get('total', 0.0), '+.2f'))} (since {e((d.get('live_pnl_today') or {}).get('since', '?'))})</p></section>
'''),
("start the 00:00 UTC snapshot thread",
'''    print(f"farm-dash: http://{BIND[0]}:{BIND[1]}/", file=sys.stderr)
''',
'''    print(f"farm-dash: http://{BIND[0]}:{BIND[1]}/", file=sys.stderr)
    threading.Thread(target=day_snapshot_loop, name="day-snapshot", daemon=True).start()     # 15j
'''),
]

MARKER = "# 15j: farm-dash's own live-PnL snapshot"


def patched(path):
    text = open(path, encoding="utf-8").read()
    if MARKER in text:
        print("  farm-dash: already the 15j version")
        return text
    for title, old, new in PAIRS:
        n = text.count(old)
        if n != 1:
            raise SystemExit(f"farm-dash: cannot apply '{title}': old text found {n} times (expected 1); nothing was changed")
        text = text.replace(old, new)
        print(f"  farm-dash: {title}")
    return text


def main(a):
    if len(a) < 2 or a[0] not in ("check", "apply") or (a[0] == "apply" and len(a) < 3):
        raise SystemExit(__doc__)
    text = patched(a[1])
    if a[0] == "apply":
        os.makedirs(a[2], exist_ok=True)
        with open(os.path.join(a[2], "farm-dash"), "w", encoding="utf-8") as f:
            f.write(text)
    print(f"patch-15j: {a[0]} ok")


if __name__ == "__main__":
    main(sys.argv[1:])
