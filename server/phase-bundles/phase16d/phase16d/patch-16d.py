#!/usr/bin/env python3
"""Phase 16d text patch of farm-dash: count sends in the format the live bots actually write.

  patch-16d.py check <farm-dash>
  patch-16d.py apply <farm-dash> <outdir>

16c looked for `send_result: won` / `"send_result": "won"`. The live bots write one JSON object per
line with the event name in "ev" and the outcome in "result":
  {"ts": 1795415348.8, "ev": "send_result", "result": "won", "hash": "0x…", "send_block": …}
so 16c counted 0 for every bot (11-23 15:38 survey of 67 bots: send_result/won 368, lost 550,
unknown 8). _count_lines() now reads a JSON line first: ev (or event) == "send_result" → its result
(or outcome; "unknown" when neither); a "send_result" key → its value. Other lines keep the 16c
regular expression. The time filter (lines before the promotion are not counted) is unchanged.
"""
import os
import sys

OLD = '''def _count_lines(lines, since, counts):
    for line in lines:
        if "send_result" not in line:
            continue
        m = SEND_RE.search(line)
        if not m:
            continue
        t = _line_epoch(line)
        if since is not None and t is not None and t < since:
            continue                                 # before this promotion (paper-era or an earlier promote)
        v = m.group(1).lower()
        counts[v] = counts.get(v, 0) + 1
'''

NEW = '''def _send_value(line):
    """16d: the outcome of a send recorded on this line, or None. The live bots write
    {"ev": "send_result", "result": "won", ...}; a "send_result" key or `send_result: won` text also count."""
    s = line.lstrip()
    if s.startswith("{"):
        try:
            r = json.loads(s)
        except ValueError:
            r = None
        if isinstance(r, dict):
            if "send_result" in (r.get("ev"), r.get("event")):
                return str(r.get("result") or r.get("outcome") or "unknown").lower()
            if isinstance(r.get("send_result"), str):
                return r["send_result"].lower()
            return None
    m = SEND_RE.search(line)
    return m.group(1).lower() if m else None


def _count_lines(lines, since, counts):
    for line in lines:
        if "send_result" not in line:
            continue
        v = _send_value(line)
        if v is None:
            continue
        t = _line_epoch(line)
        if since is not None and t is not None and t < since:
            continue                                 # before this promotion (paper-era or an earlier promote)
        counts[v] = counts.get(v, 0) + 1
'''

MARKER = "def _send_value(line):"


def main():
    if len(sys.argv) < 3 or sys.argv[1] not in ("check", "apply") or (sys.argv[1] == "apply" and len(sys.argv) != 4):
        sys.exit(__doc__)
    text = open(sys.argv[2], encoding="utf-8").read()
    if MARKER in text:
        print("  farm-dash: _count_lines reads ev/result: already applied")
    else:
        n = text.count(OLD)
        if n != 1:
            sys.exit(f"patch-16d: old _count_lines found {n} times (need 1; is 16c installed?); nothing written")
        text = text.replace(OLD, NEW)
        print("  farm-dash: _count_lines reads ev/result")
    if sys.argv[1] == "apply":
        out = os.path.join(sys.argv[3], "farm-dash")
        with open(out, "w", encoding="utf-8") as f:
            f.write(text)
        os.chmod(out, 0o755)
        print("patch-16d: apply ok")
    else:
        print("patch-16d: check ok")


if __name__ == "__main__":
    main()
