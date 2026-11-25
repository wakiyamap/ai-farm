#!/usr/bin/env python3
"""Phase 15l text patches of farm-dash: no false "no baseline" warning after a bot is stopped.

  patch-15l.py check <farm-dash>
  patch-15l.py apply <farm-dash> <outdir>

farm-dash keeps `gate-ctl status` for up to 5 minutes (it costs about 900 Alchemy CU), but reads
pnl.json fresh. `gate stop` sweeps the bot and removes its pnl.json baseline at once, so for up to
5 minutes the cached status still listed the stopped bot as live, without a baseline, and the page
and the brief warned "<bot>: no baseline in pnl.json, the live-loss stop cannot judge it".

1. gate_status(): the cache is dropped when gate.log has changed since it was taken (every promote,
   fund, sweep and stop writes a gate.log record; `gate-ctl status` writes none). A stopped or newly
   promoted bot shows on the next refresh. A few extra status calls a day, one per gate event.
2. live_loss(): a bot without a baseline whose bots/live directory is gone is skipped (stopped),
   instead of being reported as "no baseline". A live bot without a baseline is still reported.
"""
import os
import sys

PAIRS = [
("gate_status: drop the cache when gate.log changed",
'''_gate_cache = {"t": 0, "v": None}


def gate_status(max_age=300):
    # 10i: `gate-ctl status` reads balances, USDC and prices on every chain (about 900 Alchemy CU).
    # With the page open and refreshing, a 60 s cache meant about 1.3M CU a day.
    import time as _t
    if _gate_cache["v"] is not None and _t.monotonic() - _gate_cache["t"] < max_age:
        return _gate_cache["v"]
    v = _gate_status()
    _gate_cache.update(t=_t.monotonic(), v=v)
    return v
''',
'''_gate_cache = {"t": 0, "v": None, "log": None}


def _gate_log_stamp():
    """15l: (mtime_ns, size) of gate.log; every promote / fund / sweep / stop appends a record."""
    try:
        st = os.stat(f"{STATE}/gate.log")
        return (st.st_mtime_ns, st.st_size)
    except OSError:
        return None


def gate_status(max_age=300):
    # 10i: `gate-ctl status` reads balances, USDC and prices on every chain (about 900 Alchemy CU).
    # With the page open and refreshing, a 60 s cache meant about 1.3M CU a day.
    # 15l: the cache is also dropped when gate.log changed, so a stopped bot leaves the live list
    # at once (pnl.json, read fresh, no longer has its baseline).
    import time as _t
    stamp = _gate_log_stamp()
    if _gate_cache["v"] is not None and _t.monotonic() - _gate_cache["t"] < max_age \\
            and (stamp is None or stamp == _gate_cache["log"]):
        return _gate_cache["v"]
    v = _gate_status()
    _gate_cache.update(t=_t.monotonic(), v=v, log=stamp)
    return v
''',
"def _gate_log_stamp():"),
("live_loss: skip a bot stopped since the cached status",
'''        base, ubase = (pnl.get("baseline") or {}).get(bot), (pnl.get("baseline_usdc") or {}).get(bot)
        if not base and not ubase:
            out[bot] = {"note": "no baseline"}
            continue
''',
'''        base, ubase = (pnl.get("baseline") or {}).get(bot), (pnl.get("baseline_usdc") or {}).get(bot)
        if not base and not ubase:
            if not os.path.isdir(f"{WS}/bots/live/{bot}"):
                continue                 # 15l: stopped since the cached status (archived, swept)
            out[bot] = {"note": "no baseline"}
            continue
''',
"# 15l: stopped since the cached status"),
]


def main():
    if len(sys.argv) < 3 or sys.argv[1] not in ("check", "apply") or (sys.argv[1] == "apply" and len(sys.argv) != 4):
        sys.exit(__doc__)
    path = sys.argv[2]
    text = open(path, encoding="utf-8").read()
    for name, old, new, marker in PAIRS:
        if marker in text:
            print(f"  farm-dash: {name}: already applied")
            continue
        n = text.count(old)
        if n != 1:
            sys.exit(f"patch-15l: '{name}': old text found {n} times (need 1); nothing written")
        text = text.replace(old, new)
        print(f"  farm-dash: {name}")
    if sys.argv[1] == "apply":
        out = os.path.join(sys.argv[3], "farm-dash")
        with open(out, "w", encoding="utf-8") as f:
            f.write(text)
        os.chmod(out, 0o755)
        print("patch-15l: apply ok")
    else:
        print("patch-15l: check ok")


if __name__ == "__main__":
    main()
