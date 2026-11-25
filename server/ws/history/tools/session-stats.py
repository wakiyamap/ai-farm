#!/usr/bin/env python3
"""Session counts per day x role x model from logs/sessions/*.jsonl.

Harness lines for starts skipped by ExecCondition (empty scout queue etc.,
notes contain "exec-condition") are not sessions: they are counted in a
separate `skipped` column, never in `sessions` or `no_report`.

usage: session-stats.py [--days 3] [--role builder]
"""
import argparse, collections, datetime, glob, json, os

ap = argparse.ArgumentParser()
ap.add_argument("--days", type=int, default=3)
ap.add_argument("--role")
a = ap.parse_args()
today = datetime.datetime.now(datetime.timezone.utc).date()
days = {str(today - datetime.timedelta(d)) for d in range(a.days)}
c = collections.defaultdict(collections.Counter)
for f in sorted(glob.glob("/srv/farm/ws/logs/sessions/*.jsonl")):
    day = os.path.basename(f)[:10]
    if day not in days:
        continue
    for line in open(f):
        try:
            r = json.loads(line)
        except Exception:
            continue
        role = r.get("role")
        if a.role and role != a.role:
            continue
        k = (day, role, str(r.get("model")))
        if "exec-condition" in str(r.get("notes", "")):
            c[k]["skipped"] += 1
            continue
        c[k]["sessions"] += 1
        c[k][str(r.get("outcome"))] += 1
        c[k]["bot_ids"] += len(r.get("bot_ids") or [])
for k in sorted(c):
    v = c[k]
    rest = {x: y for x, y in v.items() if x not in ("sessions", "skipped", "bot_ids")}
    print(f"{k[0]}  {k[1]:<15} {k[2]:<22} sessions={v['sessions']:<4} skipped={v['skipped']:<5} bot_ids={v['bot_ids']:<3} {dict(sorted(rest.items()))}")
