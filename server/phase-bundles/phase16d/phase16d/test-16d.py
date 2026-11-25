#!/usr/bin/env python3
"""Offline tests of phase 16d: sends counted from {"ev": "send_result", "result": ...} lines.

  test-16d.py <farm-dash> [--old]
"""
import importlib.machinery
import importlib.util
import json
import os
import sys
import tempfile
import time

PATH = sys.argv[1]
OLD = "--old" in sys.argv[2:]


def main():
    loader = importlib.machinery.SourceFileLoader("farmdash16d", PATH)
    spec = importlib.util.spec_from_loader("farmdash16d", loader)
    m = importlib.util.module_from_spec(spec)
    loader.exec_module(m)
    tmp = tempfile.mkdtemp(prefix="t16d-")
    m.WS = f"{tmp}/ws"
    bot = "trial-ryeth-arb-arbitrum"
    os.makedirs(f"{m.WS}/bots/live/{bot}/logs")
    now = time.time()
    promoted = now - 80 * 3600
    rows = [{"ts": promoted - 600, "ev": "paper_sim", "result": "success"},
            {"ts": promoted - 300, "ev": "send_result", "result": "won", "hash": "0x" + "a" * 64}]   # before promote
    rows += [{"ts": now - 3600 * i, "ev": "check", "result": "no_gain", "best_wei": 0} for i in range(20)]
    rows += [{"ts": now - 7000 - i, "ev": "send_result", "result": "won", "hash": "0x" + "b" * 64, "send_block": 1, "winner_block": 1}
             for i in range(4)]
    rows += [{"ts": now - 9000, "ev": "send_result", "result": "lost", "winner_block": 2},
             {"ts": now - 9100, "ev": "send_result", "result": "unknown"},
             {"ts": now - 9200, "ev": "send_result"},
             {"ts": now - 9300, "ev": "send", "hash": "0x" + "c" * 64},
             {"ts": now - 9400, "ev": "opportunity", "note": "send_result pending"},
             {"ts": now - 9500, "send_result": "won"}]
    with open(f"{m.WS}/bots/live/{bot}/logs/bot.jsonl", "w") as f:
        f.write("\n".join(json.dumps(r) for r in rows) + "\n")
        f.write("2026-11-23 06:00:00 send_result: lost\n")
    m._journal_cache[bot] = (time.monotonic(), promoted, {}, "test")
    s = m.send_counts(bot, promoted)
    res = []

    def check(name, cond):
        res.append(cond)
        print(("  ok   " if cond else "  FAIL ") + name)

    check(f"won 5 (4 ev/result + 1 send_result key, paper-era one skipped): got {s['won']}", s["won"] == 5)
    check(f"sends 9 (won 5, lost 2, unknown 2; send / opportunity lines not counted): got {s['sends']} {s['results']}",
          s["sends"] == 9 and s["results"].get("lost") == 2 and s["results"].get("unknown") == 2)
    check("source is the log file, not the journal", s["source"].startswith("logs (1 file"))
    print(f"result: {sum(res)} of {len(res)} passed")
    sys.exit(0 if OLD or all(res) else 1)


if __name__ == "__main__":
    main()
