#!/usr/bin/env python3
"""Phase 16c text patches of farm-dash: grad bots in their own section, graduation candidates.

  patch-16c.py check <farm-dash>
  patch-16c.py apply <farm-dash> <outdir>

decisions/human/2026-11-24-graduate-and-builder-focus.md: a trial bot live for 72 h or more, +1 USD
or more since promotion and 3 or more `send_result: won` is a graduation candidate; it is rebuilt as
grad-<target>-<chain>; at most 5 grads live.

1. block-16c.py (next to this file) goes in before mcu(): promote time per bot from gate.log,
   won / sends per live bot from bots/live/<id>/logs/ (the bot@ journal when the files hold no
   send_result line), the candidates, and the page / brief pieces.
2. extras(): "graduation" (also in /data.json).
3. warnings(): more than 5 live grads.
4. extra_tiles(): a "Grad bots" tile (n/5, candidates).
5. brief_top(): grad and candidate lines after "in profit".
6. render(): "Live bots" becomes three tables: Grad bots, Live bots: trial and one-shot,
   Graduation candidates (and the trial bots one condition short).
Read-only as before: nothing here changes a bot, the gate or any file except farm-dash's own cache.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))


def pairs():
    block = open(os.path.join(HERE, "block-16c.py"), encoding="utf-8").read()
    return [
        ("grad / graduation functions before mcu()",
         "def mcu(n):\n",
         block + "def mcu(n):\n",
         "# --- 16c: grad bots and graduation candidates"),
        ("extras: graduation",
         '''        "swept_total": _safe(None, swept_total),
''',
         '''        "swept_total": _safe(None, swept_total),
        "graduation": _safe(dict(_GRAD_EMPTY), graduation, g, lp),                             # 16c
''',
         '"graduation": _safe(dict(_GRAD_EMPTY), graduation, g, lp)'),
        ("warnings: more than 5 live grads",
         '''            w.append(f"prompt of {p['instance']} is {p['bytes']:,} bytes ({p['state']})")
    return w
''',
         '''            w.append(f"prompt of {p['instance']} is {p['bytes']:,} bytes ({p['state']})")
    gr = d.get("graduation") or {}
    if len(gr.get("grad_live", [])) > gr.get("grad_max", GRAD_MAX_LIVE):                     # 16c
        w.append(f"{len(gr['grad_live'])} grad bots are live, the decision allows {gr['grad_max']}")
    return w
''',
         "the decision allows {gr['grad_max']}"),
        ("extra_tiles: grad tile",
         '''    return tiles
''',
         '''    gr = d.get("graduation") or {}                                                             # 16c
    tiles.append(("Grad bots", f"{len(gr.get('grad_live', []))}/{gr.get('grad_max', GRAD_MAX_LIVE)}",
                  f"{len(gr.get('candidates', []))} candidate(s) · {len(gr.get('near', []))} one short",
                  len(gr.get("grad_live", [])) <= gr.get("grad_max", GRAD_MAX_LIVE)))
    return tiles
''',
         'tiles.append(("Grad bots"'),
        ("brief_top: grad lines after 'in profit'",
         '''        L.append("  in profit: " + ", ".join(f"{b} {v:+.2f}" for v, b in winners))
''',
         '''        L.append("  in profit: " + ", ".join(f"{b} {v:+.2f}" for v, b in winners))
    L += grad_brief(d)                                                                          # 16c
''',
         "    L += grad_brief(d)"),
        ("render: grad / trial / candidate sections",
         '''<h2>Live bots</h2>{table(live_cols(d, live_rows))}
''',
         '''{render_grad(d, live_rows)}
''',
         "{render_grad(d, live_rows)}"),
    ]


def main():
    if len(sys.argv) < 3 or sys.argv[1] not in ("check", "apply") or (sys.argv[1] == "apply" and len(sys.argv) != 4):
        sys.exit(__doc__)
    path = sys.argv[2]
    text = open(path, encoding="utf-8").read()
    for name, old, new, marker in pairs():
        if marker in text:
            print(f"  farm-dash: {name}: already applied")
            continue
        n = text.count(old)
        if n != 1:
            sys.exit(f"patch-16c: '{name}': old text found {n} times (need 1); nothing written")
        text = text.replace(old, new)
        print(f"  farm-dash: {name}")
    if sys.argv[1] == "apply":
        out = os.path.join(sys.argv[3], "farm-dash")
        with open(out, "w", encoding="utf-8") as f:
            f.write(text)
        os.chmod(out, 0o755)
        print("patch-16c: apply ok")
    else:
        print("patch-16c: check ok")


if __name__ == "__main__":
    main()
