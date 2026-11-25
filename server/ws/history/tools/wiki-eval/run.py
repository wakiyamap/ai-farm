#!/usr/bin/env python3
"""Wiki retrieval eval: run `wiki search` for each question, score the expected page.

Usage: python3 /srv/farm/ws/tools/wiki-eval/run.py [--limit 5] [--json out.json]

Metrics (printed as one summary line, plus misses):
  hit@1, hit@3, hit@limit : expected page (or a redirect pointing to it) at that rank
  mrr                     : mean reciprocal rank (0 when absent)
  empty                   : questions with zero results
  tok/query               : mean characters of search output / 4 (proxy for tokens returned)
Keep a retrieval change only if hit rates rise without tok/query rising.
"""
import argparse
import json
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
WIKI_DIR = "/srv/farm/ws/wiki"


def redirect_target(path):
    try:
        with open(os.path.join(WIKI_DIR, path), encoding="utf-8") as f:
            head = f.read(600)
    except OSError:
        return None
    if re.search(r"^type:\s*redirect\s*$", head, re.M):
        m = re.search(r"^to:\s*(\S+)\s*$", head, re.M)
        return m.group(1) if m else None
    return None


def search(q, limit):
    r = subprocess.run(["wiki", "search", q, "--limit", str(limit)],
                       capture_output=True, text=True, timeout=60)
    out = r.stdout
    paths = []
    for line in out.splitlines():
        cell = line.split("\t", 1)[0].strip()
        if cell.endswith(".md"):
            paths.append(cell)
    return paths, out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=5)
    ap.add_argument("--questions", default=os.path.join(HERE, "questions.jsonl"))
    ap.add_argument("--json", help="write per-question results here")
    a = ap.parse_args()

    qs = [json.loads(l) for l in open(a.questions, encoding="utf-8") if l.strip()]
    rows, h1, h3, hk, rr, empty, chars = [], 0, 0, 0, 0.0, 0, 0
    for item in qs:
        paths, out = search(item["q"], a.limit)
        chars += len(out)
        resolved = [redirect_target(p) or p for p in paths]
        rank = next((i + 1 for i, p in enumerate(resolved) if p == item["page"]), 0)
        empty += not paths
        h1 += rank == 1
        h3 += 0 < rank <= 3
        hk += rank > 0
        rr += 1.0 / rank if rank else 0.0
        rows.append({"q": item["q"], "page": item["page"], "rank": rank, "got": paths})
    n = len(qs)
    print(f"n={n} hit@1={h1/n:.3f} hit@3={h3/n:.3f} hit@{a.limit}={hk/n:.3f} "
          f"mrr={rr/n:.3f} empty={empty} tok/query={chars/4/n:.0f}")
    for r in rows:
        if r["rank"] != 1:
            print(f"  rank={r['rank']} q={r['q']!r} want={r['page']} got={r['got'][:3]}")
    if a.json:
        with open(a.json, "w", encoding="utf-8") as f:
            json.dump(rows, f, indent=1)
    return 0


if __name__ == "__main__":
    sys.exit(main())
