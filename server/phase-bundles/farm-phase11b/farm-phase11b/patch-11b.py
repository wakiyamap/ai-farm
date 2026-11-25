#!/usr/bin/env python3
"""Phase 11b: exact-text patches that add to farm-dash what phases 7 to 11a brought and the page
and brief.txt did not show.

  patch-11b.py check <farm-dash>
  patch-11b.py apply <farm-dash> <outdir>

The new functions are in block-11b.py (next to this file) and go in front of collect(). Every old
text must occur exactly once, or nothing is written. Safe to re-run (markers).
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
with open(os.path.join(HERE, "block-11b.py"), encoding="utf-8") as _f:
    BLOCK = _f.read()

DASH = [
("the new readers and renderers (block-11b.py), in front of collect()",
'''def collect(gate_max_age=300):
    return {''',
BLOCK + '''def collect(gate_max_age=300):
    return {''',
"def extras(gate_max_age=300):"),

("collect() adds them",
'''        "pnl": pnl_history(),
    }
''',
'''        "pnl": pnl_history(),
        **extras(gate_max_age),
    }
''',
"**extras(gate_max_age),"),

("tiles: Alchemy CU this cycle, Feed CU today, Services",
'''    tile_html = "".join(
''',
'''    tiles += extra_tiles(d)
    tile_html = "".join(
''',
"tiles += extra_tiles(d)"),

("badges under the tiles for whatever wants a look",
'''<div class="tiles">{tile_html}</div>
''',
'''<div class="tiles">{tile_html}</div>
{render_warnings(d)}
''',
"{render_warnings(d)}"),

("live table: loss since promotion, realized today, nonces; then the intermediate wallet and the gate log",
'''<h2>Live bots</h2>{table(live_rows)}
''',
'''<h2>Live bots</h2>{table(live_cols(d, live_rows))}
{render_money(d)}
''',
"{render_money(d)}"),

("Alchemy by chain, feed, services, prompt sizes, decisions, leads by status",
'''<p class="muted" style="font-size:12px;margin-top:24px">Read-only.''',
'''{render_infra(d)}
<p class="muted" style="font-size:12px;margin-top:24px">Read-only.''',
"{render_infra(d)}"),

("brief.txt carries the same, right under the capital line",
'''    L += ["", "## Paper bots"]
''',
'''    L += brief_top(d)
    L += ["", "## Paper bots"]
''',
"L += brief_top(d)"),
]


def plan(text, hunks):
    lines = []
    for title, old, new, marker in hunks:
        if marker in text:
            lines.append(f"  already applied: {title}")
            continue
        n = text.count(old)
        if n != 1:
            raise ValueError(f"{title}: the expected text occurs {n} times (must be exactly 1); nothing was changed")
        text = text.replace(old, new)
        lines.append(f"  ok: {title}")
    return text, lines


def main(argv):
    if len(argv) < 2 or argv[0] not in ("check", "apply") or (argv[0] == "apply" and len(argv) != 3):
        sys.exit(__doc__)
    path = argv[1]
    with open(path, encoding="utf-8") as f:
        text = f.read()
    try:
        out, lines = plan(text, DASH)
    except ValueError as exc:
        sys.exit(f"patch-11b: {os.path.basename(path)}: {exc}")
    print(f"{os.path.basename(path)}:")
    print("\n".join(lines))
    if argv[0] == "apply":
        with open(os.path.join(argv[2], os.path.basename(path)), "w", encoding="utf-8") as f:
            f.write(out)


if __name__ == "__main__":
    main(sys.argv[1:])
