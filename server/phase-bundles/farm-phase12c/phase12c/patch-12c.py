#!/usr/bin/env python3
"""Phase 12c text patch for /opt/farm/bin/wiki: rank `wiki search` by BM25 with a bonus for a
term in the path/frontmatter or the title line (meta's proposal of 2026-11-15, the `bm25`
variant of tools/wiki-eval/rank-variants.py). Output lines, the limit and the "at least half
of the terms" floor are unchanged; only the order differs.

  patch-12c.py check <wiki>           the old text occurs exactly once
  patch-12c.py apply <wiki> <out>     write the patched copy to <out>
"""
import sys

OLD = '''    need = max(1, (len(terms) + 1) // 2)
    hits = []
    for rel, full in pages():
        try:
            with open(full, encoding="utf-8", errors="replace") as f:
                text = f.read(MAX_READ)
        except OSError:
            continue
        meta, body = parse(text)
        head = (rel + " " + " ".join(meta.values())).lower()
        low = body.lower()
        matched, score = 0, 0
        for term in terms:
            in_head, count = term in head, low.count(term)
            if in_head or count:
                matched += 1
                score += (5 if in_head else 0) + min(count, 5)
        if matched >= need:
            hits.append((matched, score, rel, meta, body))
    hits.sort(key=lambda h: (-h[0], -h[1], h[2]))
'''

NEW = '''    need = max(1, (len(terms) + 1) // 2)
    docs = []
    for rel, full in pages():
        try:
            with open(full, encoding="utf-8", errors="replace") as f:
                text = f.read(MAX_READ)
        except OSError:
            continue
        meta, body = parse(text)
        docs.append((rel, meta, body, (rel + " " + " ".join(meta.values())).lower(), body.lower(),
                     first_line(body).lower()))
    # BM25 with a bonus for a term in the path/frontmatter (2) or the title line (1): a long hub
    # page that mentions every term once no longer outranks the short page about the question
    # (12c; before, the order was matched terms, then capped term counts).
    import math
    n_docs = len(docs)
    avglen = (sum(len(d[2]) for d in docs) / n_docs) if n_docs else 1.0
    df = {t: sum(1 for d in docs if t in d[3] or t in d[4]) for t in set(terms)}
    k1, b = 1.2, 0.75
    hits = []
    for rel, meta, body, head, low, title in docs:
        matched, score = 0, 0.0
        for term in terms:
            in_head, count = term in head, low.count(term)
            if not (in_head or count):
                continue
            matched += 1
            idf = math.log(1 + (n_docs - df[term] + 0.5) / (df[term] + 0.5))
            tf = count * (k1 + 1) / (count + k1 * (1 - b + b * len(body) / (avglen or 1.0))) if count else 0.0
            score += idf * (tf + (2.0 if in_head else 0.0) + (1.0 if term in title else 0.0))
        if matched >= need:
            hits.append((matched, score, rel, meta, body))
    hits.sort(key=lambda h: (-h[1], h[2]))
'''


def main():
    if len(sys.argv) < 3 or sys.argv[1] not in ("check", "apply"):
        sys.exit(__doc__)
    text = open(sys.argv[2], encoding="utf-8").read()
    n = text.count(OLD)
    if n != 1:
        sys.exit(f"{sys.argv[2]}: the search block matches {n} times (expected 1); nothing was changed")
    if sys.argv[1] == "check":
        print("  wiki: 1 patch matches")
        return
    with open(sys.argv[3], "w", encoding="utf-8") as f:
        f.write(text.replace(OLD, NEW))


if __name__ == "__main__":
    main()
