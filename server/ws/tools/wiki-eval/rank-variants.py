#!/usr/bin/env python3
"""Offline comparison of `wiki search` ranking variants on the wiki-eval questions.

Usage: python3 /srv/farm/ws/tools/wiki-eval/rank-variants.py [variant ...] [-v]
  variants: cur (exact copy of /opt/farm/bin/wiki cmd_search ordering),
            bm25_matched (matched-term count first, then BM25 + head/title bonus),
            bm25 (BM25 + head/title bonus only; the same matched-term floor)
  -v        list the misses per variant

Only the ordering differs between variants; the result lines and the limit (5) are the
same, so tokens returned per query do not change. Read-only. Written by meta 85c0c080
to put numbers behind a proposal for the search tool, which lives outside the workspace.
`cur` must reproduce run.py's hit@1; if it does not, the copy is stale.
"""
import json
import math
import os
import re
import sys

WIKI = "/srv/farm/ws/wiki"
Q = os.path.join(os.path.dirname(os.path.abspath(__file__)), "questions.jsonl")
MAX_READ = 64 * 1024


def parse(text):
    meta, body = {}, text
    if text.startswith("---\n"):
        end = text.find("\n---\n", 4)
        if end > 0:
            for line in text[4:end].splitlines():
                k, _, v = line.partition(":")
                meta[k.strip()] = v.strip()
            body = text[end + 5:]
    return meta, body


def first_line(body):
    for line in body.splitlines():
        line = line.strip().lstrip("#").strip()
        if line:
            return line[:160].lower()
    return ""


def load():
    docs = []
    for root, dirs, files in os.walk(WIKI):
        dirs[:] = [d for d in dirs if not d.startswith(".")]
        for n in files:
            if n.endswith(".md") and not n.startswith("."):
                full = os.path.join(root, n)
                with open(full, encoding="utf-8", errors="replace") as f:
                    text = f.read(MAX_READ)
                meta, body = parse(text)
                docs.append(dict(rel=os.path.relpath(full, WIKI), meta=meta,
                                 head=(os.path.relpath(full, WIKI) + " " + " ".join(meta.values())).lower(),
                                 low=body.lower(), title=first_line(body), n=len(body)))
    return docs


def terms_of(q):
    return [t for t in re.findall(r"0x[0-9a-fA-F]+|[\w.-]+", q.lower()) if len(t) > 1]


def make_ranker(docs):
    n_docs = len(docs)
    avglen = sum(d["n"] for d in docs) / n_docs
    df_cache = {}

    def df(t):
        if t not in df_cache:
            df_cache[t] = sum(1 for d in docs if t in d["head"] or t in d["low"])
        return df_cache[t]

    def rank(q, variant, limit=5):
        terms = terms_of(q)
        need = max(1, (len(terms) + 1) // 2)
        hits = []
        for d in docs:
            matched, score = 0, 0.0
            for t in terms:
                in_head, c = t in d["head"], d["low"].count(t)
                if not (in_head or c):
                    continue
                matched += 1
                if variant == "cur":
                    score += (5 if in_head else 0) + min(c, 5)
                else:
                    idf = math.log(1 + (n_docs - df(t) + 0.5) / (df(t) + 0.5))
                    k1, b = 1.2, 0.75
                    tf = c * (k1 + 1) / (c + k1 * (1 - b + b * d["n"] / avglen)) if c else 0.0
                    bonus = (2.0 if in_head else 0.0) + (1.0 if t in d["title"] else 0.0)
                    score += idf * (tf + bonus)
            if matched >= need:
                if variant in ("cur", "bm25_matched"):
                    key = (-matched, -score, d["rel"])
                else:
                    key = (-score, d["rel"])
                hits.append((key, d))
        hits.sort(key=lambda h: h[0])
        out = []
        for _, d in hits[:limit]:
            out.append(d["meta"].get("to") if d["meta"].get("type") == "redirect" else d["rel"])
        return out

    return rank


def main(argv):
    verbose = "-v" in argv
    variants = [a for a in argv if a != "-v"] or ["cur", "bm25_matched", "bm25"]
    docs = load()
    rank = make_ranker(docs)
    with open(Q, encoding="utf-8") as f:
        qs = [json.loads(l) for l in f if l.strip()]
    for v in variants:
        h1 = h3 = h5 = 0
        rr = 0.0
        miss = []
        for it in qs:
            got = rank(it["q"], v)
            r = next((i + 1 for i, p in enumerate(got) if p == it["page"]), 0)
            h1 += r == 1
            h3 += 0 < r <= 3
            h5 += r > 0
            rr += 1 / r if r else 0
            if r != 1:
                miss.append((r, it["q"], it["page"], got[:3]))
        n = len(qs)
        print(f"{v}: n={n} pages={len(docs)} hit@1={h1/n:.3f} hit@3={h3/n:.3f} "
              f"hit@5={h5/n:.3f} mrr={rr/n:.3f}")
        if verbose:
            for r, q, want, got in miss:
                print(f"   rank={r} q={q!r} want={want} got={got}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
