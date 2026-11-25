# --- 16c: grad bots and graduation candidates (decisions/human/2026-11-24-graduate-and-builder-focus.md) ---
import re as _re

GRAD_PREFIX, TRIAL_PREFIX = "grad-", "trial-"
GRAD_MAX_LIVE = 5                   # decision 2.: at most 5 live grads at a time
GRAD_MIN_HOURS = 72                 # decision 1.: live for 72 hours or more
GRAD_MIN_PNL = 1.0                  # decision 1.: +1 USD or more since promotion (gate status)
GRAD_MIN_WINS = 3                   # decision 1.: 3 or more `send_result: won` in the bot's log
SEND_RE = _re.compile(r"""send_result["']?\s*[:=]\s*["']?([A-Za-z_]+)""")
TS_RE = _re.compile(r"^\W{0,2}(\d{4}-\d\d-\d\d[T ]\d\d:\d\d:\d\d(?:\.\d+)?(?:Z|[+-]\d\d:?\d\d)?)")
LOG_READ_MAX = 256 * 1024 * 1024    # first read of one log file: at most its last 256 MiB
JOURNAL_MAX_AGE = 300               # the journal fallback is asked at most every 5 minutes per bot
_log_scan = {}                      # path -> {"key", "off", "counts"}: incremental, appends are read once
_journal_cache = {}                 # bot -> (monotonic, since, counts, error)
_journal_budget = [4]               # journalctl calls left in this graduation() call (keeps the page fast)


def _epoch(v):
    """gate.log / log-line time (epoch s or ms, or ISO 8601; naive = UTC) -> epoch seconds or None."""
    if isinstance(v, bool):
        return None
    if isinstance(v, (int, float)):
        return v / 1000 if v > 1e12 else float(v)
    if isinstance(v, str) and v:
        try:
            t = dt.datetime.fromisoformat(v.strip().replace("Z", "+00:00").replace(" ", "T", 1))
        except ValueError:
            return None
        return (t if t.tzinfo else t.replace(tzinfo=dt.timezone.utc)).timestamp()
    return None


def promote_times(path=None):
    """16c: bot -> epoch of its newest `promote` record in gate.log (a refused promote writes none
    with op 'promote', or carries ok=false / an error, and is skipped)."""
    out = {}
    try:
        with open(path or f"{STATE}/gate.log", encoding="utf-8") as f:
            for line in f:
                if '"promote"' not in line:
                    continue
                try:
                    r = json.loads(line)
                except ValueError:
                    continue
                if not isinstance(r, dict) or r.get("op") != "promote" or not r.get("bot"):
                    continue
                if r.get("ok") is False or r.get("error"):
                    continue
                t = _epoch(r.get("at"))
                if t is not None:
                    out[r["bot"]] = t
    except OSError:
        pass
    return out


def _line_epoch(line):
    """Time of one log line when it carries one: a JSON object with ts/time/at/timestamp, or a
    leading ISO time. None = unknown (the line is counted)."""
    s = line.lstrip()
    if s.startswith("{"):
        try:
            r = json.loads(s)
        except ValueError:
            r = None
        if isinstance(r, dict):
            for k in ("ts", "time", "at", "timestamp", "t"):
                if k in r:
                    t = _epoch(r[k])
                    if t is not None:
                        return t
            return None
    m = TS_RE.match(s)
    return _epoch(m.group(1)) if m else None


def _count_lines(lines, since, counts):
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


def _scan_file(path, since):
    """Counts of send_result values in one file since `since`; only bytes appended since the last
    call are read. A truncated or replaced file (other inode, smaller) is read again."""
    st = os.stat(path)
    key = (st.st_dev, st.st_ino, since)
    c = _log_scan.get(path)
    if not c or c["key"] != key or st.st_size < c["off"]:
        c = {"key": key, "off": max(0, st.st_size - LOG_READ_MAX), "counts": {}, "partial": b""}
    if st.st_size > c["off"]:
        with open(path, "rb") as f:
            f.seek(c["off"])
            data = c["partial"] + f.read(st.st_size - c["off"])
        c["off"] = st.st_size
        head, sep, tail = data.rpartition(b"\n")
        c["partial"] = tail                          # an unfinished last line waits for its newline
        if sep:
            _count_lines(head.decode("utf-8", "replace").splitlines(), since, c["counts"])
    _log_scan[path] = c
    return c["counts"]


def _journal_counts(bot, since):
    import time as _t
    hit = _journal_cache.get(bot)
    if hit and hit[1] == since and _t.monotonic() - hit[0] < JOURNAL_MAX_AGE:
        return hit[2], hit[3]
    if _journal_budget[0] <= 0:
        return (hit[2], hit[3]) if hit and hit[1] == since else ({}, "deferred to a later refresh")
    _journal_budget[0] -= 1
    counts, err = {}, ""
    cmd = ["journalctl", "-u", f"bot@{bot}.service", "-o", "cat", "--no-pager", "-q"]
    if since is not None:
        cmd += ["--since", f"@{int(since)}"]
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=20, check=False)
        _count_lines(r.stdout.splitlines(), since, counts)
        if not r.stdout.strip():
            err = (r.stderr.strip().splitlines() or ["empty"])[-1][:120]
    except (OSError, subprocess.TimeoutExpired) as exc:
        err = str(exc)[:120]
    _journal_cache[bot] = (_t.monotonic(), since, counts, err)
    return counts, err


def send_counts(bot, since):
    """16c: won / all send_result lines of a live bot since its promotion. Files under
    bots/live/<bot>/logs/ first; when they hold no send_result line, the bot@ unit's journal."""
    counts, files, unreadable = {}, 0, 0
    root = f"{WS}/bots/live/{bot}/logs"
    for dirpath, dirnames, filenames in os.walk(root):
        if dirpath[len(root):].count(os.sep) >= 2:
            dirnames[:] = []
        for n in filenames:
            p = os.path.join(dirpath, n)
            if os.path.islink(p) or not os.path.isfile(p):
                continue
            try:
                for k, v in _scan_file(p, since).items():
                    counts[k] = counts.get(k, 0) + v
                files += 1
            except OSError:
                unreadable += 1
    source = f"logs ({files} file(s)" + (f", {unreadable} unreadable)" if unreadable else ")")
    if not counts:
        jc, err = _journal_counts(bot, since)
        if jc:
            counts, source = jc, "journal"
        else:
            source += f"; journal: {err or 'no send_result'}"
    return {"won": counts.get("won", 0), "sends": sum(counts.values()), "results": counts, "source": source}


def graduation(g, lp, now=None):
    """16c: per live bot hours live / won / sends, the graduation candidates (decision 1.) and the
    trial bots one condition short of it."""
    import time as _t
    now = now or _t.time()
    live = g.get("live") or {}
    pt = promote_times()
    _journal_budget[0] = 4
    paper = {os.path.basename(p.rstrip("/")) for p in glob.glob(f"{WS}/bots/paper/*/")}
    stats = {}
    for bot in live:
        d = f"{WS}/bots/live/{bot}"
        if not os.path.isdir(d):
            continue                                 # stopped since the cached status
        t, src = pt.get(bot), "gate.log"
        if t is None:
            try:
                t, src = os.stat(d).st_mtime, "directory time (no promote record)"
            except OSError:
                t, src = None, "unknown"
        s = _safe({"won": 0, "sends": 0, "results": {}, "source": "error"}, send_counts, bot, t)
        stats[bot] = dict(s, hours_live=None if t is None else round((now - t) / 3600, 1),
                          promoted=jst(t) if t else "?", promote_source=src, pnl=lp.get(bot))
    cands, near = [], []
    for bot, r in sorted(stats.items()):
        if not bot.startswith(TRIAL_PREFIX) or bot.endswith("-ethereum"):
            continue                                 # one-shots, grads and ethereum are not graduated
        miss = []
        h = r["hours_live"]
        if h is None or h < GRAD_MIN_HOURS:
            miss.append(f"live {0 if h is None else h:.0f}/{GRAD_MIN_HOURS} h")
        if r["pnl"] is None or r["pnl"] < GRAD_MIN_PNL:
            miss.append("pnl " + ("?" if r["pnl"] is None else f"{r['pnl']:+.2f}") + f" < +{GRAD_MIN_PNL:g}")
        if r["won"] < GRAD_MIN_WINS:
            miss.append(f"won {r['won']}/{GRAD_MIN_WINS}")
        grad = GRAD_PREFIX + bot[len(TRIAL_PREFIX):]
        item = {"bot": bot, "hours_live": h, "pnl_since_promote_usd": "" if r["pnl"] is None else f"{r['pnl']:+.2f}",
                "won_of_sends": f"{r['won']}/{r['sends']}",
                "grad": "live" if grad in live else "in paper" if grad in paper else "—", "short_of": ", ".join(miss)}
        if not miss:
            cands.append(item)
        elif len(miss) == 1:
            near.append(item)
    return {"stats": stats, "candidates": cands, "near": near,
            "grad_live": sorted(b for b in stats if b.startswith(GRAD_PREFIX)),
            "grad_paper": sorted(b for b in paper if b.startswith(GRAD_PREFIX)), "grad_max": GRAD_MAX_LIVE}


_GRAD_EMPTY = {"stats": {}, "candidates": [], "near": [], "grad_live": [], "grad_paper": [], "grad_max": GRAD_MAX_LIVE}


def _with_sends(d, rows):
    st = (d.get("graduation") or {}).get("stats", {})
    return [dict(r, hours_live=st.get(r["bot"], {}).get("hours_live", ""),
                 won_of_sends=(f"{st[r['bot']]['won']}/{st[r['bot']]['sends']}" if r["bot"] in st else "")) for r in rows]


def render_grad(d, live_rows):
    """16c: grad bots, then the other live bots (trial, one-shot), then the graduation candidates."""
    gr = d.get("graduation") or _GRAD_EMPTY
    rows = live_cols(d, live_rows)
    grads = _with_sends(d, [r for r in rows if r["bot"].startswith(GRAD_PREFIX)])
    others = _with_sends(d, [r for r in rows if not r["bot"].startswith(GRAD_PREFIX)])
    paper = [b for b in d.get("paper", []) if b["id"].startswith(GRAD_PREFIX)]
    over = len(gr["grad_live"]) > gr["grad_max"]
    in_paper = ", ".join("%s (review %s)" % (b["id"], b["review"]) for b in paper)
    note = "<p class='muted' style='font-size:12px'>grad bots in paper: " + e(in_paper) + "</p>" if paper else ""
    warn = badge(False, "more than %d live grads" % gr["grad_max"]) if over else ""
    return f"""<h2>Grad bots ({len(grads)} of {gr['grad_max']})</h2>{warn}{table(grads)}{note}
<h2>Live bots: trial and one-shot ({len(others)})</h2>{table(others)}
<h2>Graduation candidates ({len(gr['candidates'])})</h2>{table(gr['candidates'])}
<p class="muted" style="font-size:12px">trial bots (not ethereum) live ≥ {GRAD_MIN_HOURS} h, PnL since promotion ≥ +{GRAD_MIN_PNL:g} USD and ≥ {GRAD_MIN_WINS} <code>send_result: won</code> since promotion · grad = <code>grad-&lt;target&gt;-&lt;chain&gt;</code></p>
<h2>One condition short ({len(gr['near'])})</h2>{table(gr['near'])}"""


def grad_brief(d):
    """16c: lines for brief.txt."""
    gr = d.get("graduation") or _GRAD_EMPTY
    lp, today = d.get("live_pnl") or {}, (d.get("live_pnl_today") or {}).get("by_bot", {})
    L = [f"grad bots live: {len(gr['grad_live'])} of {gr['grad_max']}"
         + (f" · in paper: {', '.join(gr['grad_paper'])}" if gr["grad_paper"] else "")]
    for b in gr["grad_live"]:
        s = gr["stats"].get(b, {})
        L.append(f"  grad {b}: pnl since promotion " + ("?" if lp.get(b) is None else f"{lp[b]:+.2f}")
                 + ("" if today.get(b) is None else f" · today {today[b]:+.2f}")
                 + f" · won {s.get('won', 0)} of {s.get('sends', 0)} sends · live {s.get('hours_live')} h")
    L.append(f"graduation candidates (trial, not ethereum, live >= {GRAD_MIN_HOURS} h, pnl >= +{GRAD_MIN_PNL:g}, "
             f"won >= {GRAD_MIN_WINS}): " + (str(len(gr["candidates"])) if gr["candidates"] else "none"))
    for c in gr["candidates"]:
        L.append(f"  - {c['bot']}: live {c['hours_live']} h · pnl {c['pnl_since_promote_usd']} · won {c['won_of_sends']} sends · grad {c['grad']}")
    if gr["near"]:
        L.append("  one condition short: " + "; ".join(f"{c['bot']} ({c['short_of']})" for c in gr["near"]))
    srcs = {s.get("source", "") for s in gr["stats"].values()}
    if gr["stats"] and all(not s.get("sends") for s in gr["stats"].values()):
        L.append("  note: no send_result line found for any live bot since its promotion ("
                 + "; ".join(sorted(srcs))[:300] + ")")
    return L


