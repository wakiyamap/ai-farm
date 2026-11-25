#!/usr/bin/env python3
"""Per-instance researcher lead funnel (decisions/human/2026-11-09-two-researchers.md).

For each author that added leads (default: researcher/*), counts:
  added        leads rows the author inserted (revisions op='add')
  non_liq      of those, the target does not name a liquidation (liquidat/absorb/clip/seize)
  earner_live  an earner later updated the lead and its status is not dead_end
  earner_dead  an earner later updated the lead and its status is dead_end
  paper        the lead id ("lead <id>" / "lead_id: <id>" / "leads:<id>") or its exact
               target appears in a bots/{paper,live,archive}/*/manifest.yaml
Read-only: opens kb/knowledge.db with mode=ro. Heuristic counts; read the rows
(`--rows`) before quoting a number in a report.
"""
import argparse
import glob
import re
import sqlite3

WS = "/srv/farm/ws"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--author-like", default="researcher/%")
    ap.add_argument("--since", default="2026-11-01", help="lead add date (UTC, inclusive)")
    ap.add_argument("--rows", action="store_true", help="print one line per lead")
    a = ap.parse_args()

    db = sqlite3.connect(f"file:{WS}/kb/knowledge.db?mode=ro", uri=True)
    leads = db.execute(
        """SELECT r.author, l.id, l.target, l.why, l.status, r.at FROM revisions r JOIN leads l ON l.id = r.row_id
           WHERE r.tbl='leads' AND r.op='add' AND r.author LIKE ? AND r.at >= ? ORDER BY r.at""",
        (a.author_like, a.since)).fetchall()
    earner_touched = {row[0] for row in db.execute(
        "SELECT DISTINCT row_id FROM revisions WHERE tbl='leads' AND op='update' AND author LIKE 'earner/%'")}

    manifests = {}
    for p in glob.glob(f"{WS}/bots/*/*/manifest.yaml"):
        try:
            manifests[p] = open(p, encoding="utf-8", errors="replace").read()
        except OSError:
            pass

    def in_paper(lid, target):
        pat = re.compile(rf"(lead[s]?[ _:#-]*(id)?[: ]*{lid}\b)", re.I)
        return any(pat.search(t) or (target and target in t) for t in manifests.values())

    stats = {}
    for author, lid, target, why, status, at in leads:
        s = stats.setdefault(author, dict(added=0, non_liq=0, earner_live=0, earner_dead=0, paper=0))
        s["added"] += 1
        # target only: "why" texts often say "beyond liquidations" / "not a liquidation"
        non_liq = not re.search(r"liquidat|absorb|clip|seize", target, re.I)
        s["non_liq"] += non_liq
        touched = lid in earner_touched
        s["earner_live"] += touched and status != "dead_end"
        s["earner_dead"] += touched and status == "dead_end"
        paper = in_paper(lid, target)
        s["paper"] += paper
        if a.rows:
            print(f"{author}\tlead {lid}\t{at[:10]}\t{status}\tnon_liq={int(non_liq)}\tearner={int(touched)}"
                  f"\tpaper={int(paper)}\t{target[:60]}")
    print("author\tadded\tnon_liq\tearner_live\tearner_dead\tpaper")
    for author, s in sorted(stats.items()):
        print(f"{author}\t{s['added']}\t{s['non_liq']}\t{s['earner_live']}\t{s['earner_dead']}\t{s['paper']}")


if __name__ == "__main__":
    main()
