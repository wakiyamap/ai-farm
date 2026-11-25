#!/usr/bin/env python3
"""Offline prototype: score wiki-search ranking variants on tools/wiki-eval/questions.jsonl.

Variant 'cur' replicates /opt/farm/bin/wiki cmd_search exactly (matched terms, then
5*in_head + min(count,5)). Other variants change only the ordering, not the output format,
so tok/query is unchanged for the same limit. Read-only; no wiki writes.
"""
import json, math, os, re, sys

WIKI = "/srv/farm/ws/wiki"
Q = "/srv/farm/ws/tools/wiki-eval/questions.jsonl"
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
            return line.lower()
    return ""


docs = []
for root, dirs, files in os.walk(WIKI):
    dirs[:] = [d for d in dirs if not d.startswith(".")]
    for n in files:
        if n.endswith(".md") and not n.startswith("."):
            full = os.path.join(root, n)
            rel = os.path.relpath(full, WIKI)
            text = open(full, encoding="utf-8", errors="replace").read(MAX_READ)
            meta, body = parse(text)
            docs.append(dict(rel=rel, meta=meta,
                             head=(rel + " " + " ".join(meta.values())).lower(),
                             low=body.lower(), title=first_line(body), n=len(body)))
N = len(docs)
avglen = sum(d["n"] for d in docs) / N


def redirect(d):
    return d["meta"].get("to") if d["meta"].get("type") == "redirect" else None


def terms_of(q):
    return [t for t in re.findall(r"0x[0-9a-fA-F]+|[\w.-]+", q.lower()) if len(t) > 1]


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
                idf = math.log(1 + (N - df(t) + 0.5) / (df(t) + 0.5))
                k1, b = 1.2, 0.75
                tf = c * (k1 + 1) / (c + k1 * (1 - b + b * d["n"] / avglen)) if c else 0.0
                h = (2.0 if in_head else 0.0) + (1.0 if t in d["title"] else 0.0)
                score += idf * (tf + h)
        if matched >= need:
            if variant in ("cur", "bm25_matched"):
                key = (-matched, -score, d["rel"])
            else:  # bm25: score only, matched-term floor still applies
                key = (-score, d["rel"])
            hits.append((key, d))
    hits.sort(key=lambda h: h[0])
    return [redirect(d) or d["rel"] for _, d in hits[:limit]]


qs = [json.loads(l) for l in open(Q, encoding="utf-8") if l.strip()]
for v in sys.argv[1:] or ["cur", "bm25_matched", "bm25"]:
    h1 = h3 = h5 = 0
    rr = 0.0
    miss = []
    for it in qs:
        got = rank(it["q"], v)
        r = next((i + 1 for i, p in enumerate(got) if p == it["page"]), 0)
        h1 += r == 1; h3 += 0 < r <= 3; h5 += r > 0; rr += 1 / r if r else 0
        if r != 1:
            miss.append((r, it["q"]))
    n = len(qs)
    print(f"{v}: n={n} hit@1={h1/n:.3f} hit@3={h3/n:.3f} hit@5={h5/n:.3f} mrr={rr/n:.3f} misses={len(miss)}")
    if "-v" in os.environ.get("PROTO_FLAGS", ""):
        for r, q in miss:
            print(f"   rank={r} {q}")
