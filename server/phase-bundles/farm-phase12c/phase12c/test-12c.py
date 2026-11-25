#!/usr/bin/env python3
"""Offline tests for the 12c `wiki search` ranking (a temp wiki; nothing else is read).

  test-12c.py <wiki> [--old] [--variants PATH]
--old        the unpatched file: failures expected, report only
--variants   meta's rank-variants.py; if given, the order must equal its `bm25` variant
"""
import contextlib
import io
import os
import sys
import tempfile

args = [a for a in sys.argv[1:] if not a.startswith("--")]
OLD = "--old" in sys.argv
VAR = sys.argv[sys.argv.index("--variants") + 1] if "--variants" in sys.argv else None
if VAR:
    args.remove(VAR)
TMP = tempfile.mkdtemp(prefix="t12c-")
PAGES = {
    "infra/crash-hub.md": "---\ntype: infra\n---\n# Crash hub\n" + ("reaction time fork reset lease liquidation census taker oracle window gas executor limit. " * 400),
    "infra/reaction-time.md": "---\ntype: infra\n---\n# Reaction time of the farm per chain\nMeasured reaction time: 3.9 s on ethereum.\n",
    "pitfalls/fork-reset.md": "---\ntype: pitfall\n---\n# Fork reset by another session\nA fork reset drops your deployment.\n",
    "pitfalls/deploy-gas.md": "---\ntype: pitfall\n---\n# Executor deploy gas limit\nThe gate refuses an executor above the limit.\n",
    "methods/old.md": "---\ntype: redirect\nto: infra/reaction-time.md\n---\n",
    "methods/unrelated.md": "---\ntype: method\n---\n# Something else\nNothing to see.\n",
}
for rel, text in PAGES.items():
    os.makedirs(os.path.dirname(os.path.join(TMP, rel)), exist_ok=True)
    open(os.path.join(TMP, rel), "w", encoding="utf-8").write(text)

ns = {"__name__": "wiki12c"}
exec(compile(open(args[0], encoding="utf-8").read(), args[0], "exec"), ns)   # noqa: S102
ns["WIKI_DIR"] = TMP


def search(q, limit=5):
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        ns["cmd_search"](q, limit)
    return [line.split("\t")[0] for line in buf.getvalue().splitlines()]


results = []


def case(name, fn):
    try:
        fn()
        results.append((name, None))
    except Exception as exc:                      # noqa: BLE001
        results.append((name, f"{type(exc).__name__}: {exc}"))


def t_short_page_beats_hub():
    got = search("reaction time")
    assert got[0] == "infra/reaction-time.md", got
    got = search("fork reset")
    assert got[0] == "pitfalls/fork-reset.md", got
    got = search("executor limit")              # terms only in the title and body, not in the path
    assert got[0] == "pitfalls/deploy-gas.md", got


def t_floor_and_no_match():
    assert search("zzzz qqqq") == ["no matches"]
    assert "methods/unrelated.md" not in search("reaction time fork")


def t_output_shape():
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        ns["cmd_search"]("reaction time", 1)
    lines = buf.getvalue().splitlines()
    assert lines[0].split("\t")[1] == "infra" and lines[0].count("\t") == 3, lines
    assert lines[1].startswith("... ") and "more matches" in lines[1], lines


def t_same_order_as_meta_variant():
    if not VAR:
        return
    v = {"__name__": "variants", "__file__": VAR}
    exec(compile(open(VAR, encoding="utf-8").read(), VAR, "exec"), v)   # noqa: S102
    v["WIKI"] = TMP
    rank = v["make_ranker"](v["load"]())
    for q in ("reaction time", "fork reset", "liquidation census taker", "crash hub gas", "ethereum 3.9", "executor limit"):
        mine = [p for p in search(q) if not p.startswith("...") and p != "no matches"]
        theirs = rank(q, "bm25")
        # the tool prints a redirect's own path, the variant its target: compare page identity
        mine = ["infra/reaction-time.md" if p == "methods/old.md" else p for p in mine]
        assert mine == theirs, (q, mine, theirs)


for f in (t_short_page_beats_hub, t_floor_and_no_match, t_output_shape, t_same_order_as_meta_variant):
    case(f.__name__[2:], f)
bad = [r for r in results if r[1]]
for name, err in results:
    print(f"  {'FAIL' if err else 'ok  '} wiki: {name}" + (f"  ({err})" if err else ""))
print(f"{len(results) - len(bad)} of {len(results)} passed" + (" (old file: failures expected)" if OLD else ""))
sys.exit(0 if OLD or not bad else 1)
