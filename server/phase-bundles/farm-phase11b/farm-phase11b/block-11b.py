# --- 11b: what phases 7 to 11a added and this page did not show yet -----------------------------
FEED = "http://127.0.0.1:8546"
GATE_CONF = "/etc/farm/gate.json"
RUNNERS = "/srv/farm/runners"
ALCHEMY_MONTHLY_CU = 95_200_000     # monthly allowance of the Alchemy plan
ALCHEMY_CYCLE_DAY = 1               # UTC day of the month the allowance restarts; set it to the billing day if that differs
USD_PER_M_CU = 0.53                 # 50 USD / 95.2M CU (decision 2026-11-12)
PROMPT_WARN, PROMPT_MAX = 56000, 60000      # assemble-prompt: memo to meta above 56,000, refuses above 60,000
SERVICES = ("rpc-relay", "farm-feed", "farm-signer", "farm-watchdog", "farm-search", "qwen-server")
QUIET_OPS = {"deploy_executor_sent", "sweep_usdc_sent"}     # each is followed by its own result record
LOSS_WARN = 2 / 3                   # warn when a live bot has used this share of max_live_loss_usd

_price_cache = {}


def _safe(default, fn, *a):
    try:
        return fn(*a)
    except Exception:                 # noqa: BLE001 - one broken source must not blank the page
        return default


def _farmchains():
    try:
        import farmchains
        return farmchains
    except Exception:                 # noqa: BLE001
        return None


def usdc_units(chain, raw):
    try:
        return raw / _farmchains().usdc_scale(chain)
    except Exception:                 # noqa: BLE001 - no farmchains: Binance-Peg USDC has 18 decimals, the rest 6
        return raw / (1e18 if chain == "bsc" else 1e6)


def native_price(chain, max_age=300):
    """Native/USD from the chain's Chainlink feed, through the relay's research lane (public nodes
    first, so normally no Alchemy CU). None when it cannot be read or is implausible."""
    import time as _t
    hit = _price_cache.get(chain)
    if hit and _t.monotonic() - hit[0] < max_age:
        return hit[1]
    fc = _farmchains()
    try:
        body = json.dumps({"jsonrpc": "2.0", "id": 1, "method": "eth_call",
                           "params": [{"to": fc.ETH_USD_FEED[chain], "data": "0x50d25bcd"}, "latest"]}).encode()   # latestAnswer()
        req = urllib.request.Request(f"{RELAY}/{fc.feed_chain(chain)}?lane=research", data=body,
                                     headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=10) as r:
            price = int(json.loads(r.read())["result"], 16) / 1e8
        if not fc.price_ok(chain, price):
            return None
    except Exception:                 # noqa: BLE001
        return None
    _price_cache[chain] = (_t.monotonic(), price)
    return price


def feed_health():
    try:
        with urllib.request.urlopen(f"{FEED}/health", timeout=5) as r:
            return json.loads(r.read())
    except (OSError, ValueError) as exc:
        return {"error": str(exc)}


def cycle_bounds(now):
    day = max(1, min(int(ALCHEMY_CYCLE_DAY), 28))
    y, m = now.year, now.month
    if now.day < day:
        y, m = (y, m - 1) if m > 1 else (y - 1, 12)
    ny, nm = (y, m + 1) if m < 12 else (y + 1, 1)
    return dt.datetime(y, m, day, tzinfo=dt.timezone.utc), dt.datetime(ny, nm, day, tzinfo=dt.timezone.utc)


def alchemy_month(now=None):
    """Alchemy CU since the cycle began, as the relay counted them (ops.db rpc_stats). farm-feed's
    subscriptions are not in rpc_stats; today's feed CU is shown next to it."""
    now = now or dt.datetime.now(dt.timezone.utc)
    start, end = cycle_bounds(now)
    rows = q(OPS, "SELECT lane, sum(cu) cu, min(day) first FROM rpc_stats WHERE provider='alchemy' AND day>=? GROUP BY 1",
             (start.strftime("%Y-%m-%d"),))
    if rows and "error" in rows[0]:
        return {"error": rows[0]["error"]}
    lanes = {r["lane"]: int(r["cu"] or 0) for r in rows}
    total = sum(lanes.values())
    since = start
    firsts = [r["first"] for r in rows if r.get("first")]
    if firsts:
        try:
            since = max(start, dt.datetime.strptime(min(firsts), "%Y-%m-%d").replace(tzinfo=dt.timezone.utc))
        except ValueError:
            pass
    days = (now - since).total_seconds() / 86400
    projected = round(total + total / days * (end - now).total_seconds() / 86400) if total and days >= 0.5 else None
    return {"since": since.strftime("%Y-%m-%d"), "ends": end.strftime("%Y-%m-%d"), "cu": total, "lanes": lanes,
            "allowance": ALCHEMY_MONTHLY_CU, "projected_cu": projected, "usd": round(total / 1e6 * USD_PER_M_CU, 2)}


def rpc_by_chain():
    return q(OPS, "SELECT chain, sum(CASE WHEN lane='live' THEN cu ELSE 0 END) live, "
                  "sum(CASE WHEN lane='paper' THEN cu ELSE 0 END) paper, "
                  "sum(CASE WHEN lane='research' THEN cu ELSE 0 END) research, sum(ok) ok, sum(failed) failed, "
                  "CASE WHEN sum(ok)+sum(failed)>0 THEN sum(latency_ms)/(sum(ok)+sum(failed)) END avg_ms "
                  "FROM rpc_stats WHERE day=date('now') AND provider='alchemy' GROUP BY 1 ORDER BY sum(cu) DESC")


def services():
    names = [f"{s}.service" for s in SERVICES]
    out = subprocess.run(["systemctl", "show", *names, "-p", "Id,LoadState,ActiveState,SubState"],
                         capture_output=True, text=True, check=False).stdout
    res = []
    for block in out.strip().split("\n\n"):
        kv = dict(line.split("=", 1) for line in block.splitlines() if "=" in line)
        if kv.get("LoadState") in (None, "not-found"):
            continue                                 # e.g. the local model server under another unit name
        res.append({"unit": kv.get("Id", "?").replace(".service", ""), "active": kv.get("ActiveState", "?"),
                    "sub": kv.get("SubState", "?")})
    for u in units("fork@*.service"):
        res.append({"unit": u["unit"].replace(".service", ""), "active": u["active"], "sub": u["sub"]})
    return res


def gate_log_tail(n=12):
    """The newest gate.log records, newest first: promote, fund, sweep (with its PnL), stop, failures."""
    try:
        with open(f"{STATE}/gate.log", "rb") as f:
            f.seek(0, 2)
            size = f.tell()
            f.seek(max(0, size - 65536))
            lines = f.read().decode("utf-8", "replace").splitlines()
    except OSError:
        return []
    if size > 65536:
        lines = lines[1:]                            # the first line is cut somewhere in the middle
    rows = []
    for line in lines:
        try:
            r = json.loads(line)
        except ValueError:
            continue
        if not isinstance(r, dict) or r.get("op") in QUIET_OPS:
            continue
        chain, bits = r.get("chain", ""), []
        if isinstance(r.get("usd"), (int, float)):
            bits.append(f"PnL {r['usd']:+.4f} USD")
        if isinstance(r.get("wei"), int):
            bits.append(f"{r['wei'] / 1e18:.6f} native")
        if isinstance(r.get("usdc"), int):
            bits.append(f"{usdc_units(chain, r['usdc']):.2f} USDC")
        if r.get("capital_usd") is not None:
            bits.append(f"capital {r['capital_usd']} USD")
        if r.get("nonce") is not None:
            bits.append(f"nonce {r['nonce']}")
        for k in ("why", "note", "archived", "label"):
            if r.get(k):
                bits.append(str(r[k])[:140])
        rows.append({"at": jst(r.get("at")), "op": r.get("op"), "bot": r.get("bot", ""), "chain": chain,
                     "detail": " · ".join(bits), "by": f"{r.get('by', '?')}/{r.get('role', '?')}"})
    return rows[-n:][::-1]


def pnl_state():
    try:
        with open(f"{STATE}/pnl.json", encoding="utf-8") as f:
            p = json.load(f)
    except (OSError, ValueError):
        return {}
    if not isinstance(p, dict):
        return {}
    if p.get("day") != dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d"):
        p["realized_usd"] = {}                       # the gate resets it on its first call of the UTC day
    return p


def max_live_loss():
    try:
        with open(GATE_CONF, encoding="utf-8") as f:
            return float(json.load(f).get("max_live_loss_usd", 30))
    except (OSError, ValueError, TypeError):
        return 30.0


def live_loss(g, pnl):
    """Per live bot: what the gate funded (pnl.json baseline, at the current price) minus what the
    wallet holds now - the number the watchdog stops a bot on. Approximate: balances are up to
    5 minutes old."""
    out = {}
    for bot, v in (g.get("live") or {}).items():
        base, ubase = (pnl.get("baseline") or {}).get(bot), (pnl.get("baseline_usdc") or {}).get(bot)
        if not base and not ubase:
            out[bot] = {"note": "no baseline"}
            continue
        funded, priced = 0.0, True
        for chain, wei in (base or {}).items():
            p = native_price(chain) if wei else 0.0
            if p is None:
                priced = False
                break
            funded += wei / 1e18 * p
        if not priced:
            out[bot] = {"note": "price unavailable"}
            continue
        for chain, raw in (ubase or {}).items():
            funded += usdc_units(chain, raw)
        value = sum(x for x in (v.get("balances_usd") or {}).values() if isinstance(x, (int, float)))
        out[bot] = {"funded_usd": round(funded, 2), "value_usd": round(value, 2), "loss_usd": round(funded - value, 2)}
    return out


def prompt_sizes():
    import time as _t
    rows = []
    for p in sorted(glob.glob(f"{RUNNERS}/*/prompt.md")):
        try:
            st = os.stat(p)
        except OSError:
            continue
        if _t.time() - st.st_mtime > 7 * 86400:
            continue                                 # leftovers of renamed instances
        rows.append({"instance": os.path.basename(os.path.dirname(p)), "bytes": st.st_size,
                     "state": "OVER 60,000: cannot start" if st.st_size > PROMPT_MAX
                     else "over 56,000" if st.st_size > PROMPT_WARN else "ok", "built": jst(st.st_mtime)})
    return rows


def decisions(n=6):
    files = sorted((f for f in glob.glob(f"{WS}/decisions/human/*") if os.path.isfile(f)), key=os.path.getmtime, reverse=True)[:n]
    return [{"mtime": jst(os.path.getmtime(p)), "file": os.path.basename(p)} for p in files]


def extras(gate_max_age=300):
    g = gate_status(gate_max_age)                    # cached: collect() has just asked for it
    g = g if isinstance(g, dict) and "error" not in g else {}
    pnl = _safe({}, pnl_state)
    return {
        "feed": _safe({"error": "feed health unreadable"}, feed_health),
        "alchemy_month": _safe({"error": "rpc_stats unreadable"}, alchemy_month),
        "rpc_chains": _safe([], rpc_by_chain),
        "services": _safe([], services),
        "gate_log": _safe([], gate_log_tail),
        "realized_today": pnl.get("realized_usd") or {},
        "sweep_pending": {k: pnl.get(k) for k in ("usdc_in_flight", "sweep_unsure") if pnl.get(k)},
        "live_loss": _safe({}, live_loss, g, pnl),
        "max_live_loss_usd": max_live_loss(),
        "prompts": _safe([], prompt_sizes),
        "decisions": _safe([], decisions),
        "lead_counts": _safe([], q, KB, "SELECT status, count(*) n FROM leads GROUP BY 1 ORDER BY 2 DESC"),
    }


def mcu(n):
    return f"{n / 1e6:.2f}M" if isinstance(n, (int, float)) else "?"


def warnings(d):
    """Things that want a look, as short lines (page badges and the top of the brief)."""
    w = []
    g = d["gate"] if "error" not in d["gate"] else {}
    for s in d.get("services", []):
        if s["active"] != "active":
            w.append(f"{s['unit']} is {s['active']}/{s['sub']}")
    for bot, v in (g.get("live") or {}).items():
        if "ActiveState=active" not in v.get("service", ""):
            w.append(f"live bot {bot} is not running ({v.get('service', '?')}): a stopped promote or an unfinished stop")
    cap = d.get("max_live_loss_usd", 30)
    for bot, x in d.get("live_loss", {}).items():
        if x.get("note") == "no baseline":
            w.append(f"{bot}: no baseline in pnl.json, the live-loss stop cannot judge it")
        elif x.get("loss_usd", 0) >= cap * LOSS_WARN:
            w.append(f"{bot}: {x['loss_usd']} USD lost since promotion (the watchdog stops it at {cap:g})")
    for k, v in d.get("sweep_pending", {}).items():
        w.append(f"pnl.json {k}: {', '.join(v)} - a sweep transfer is unresolved; run `gate stop <id>` again")
    f = d.get("feed", {})
    if "error" in f:
        w.append(f"farm-feed /health: {f['error']}")
    elif f.get("exhausted"):
        w.append("farm-feed used up its daily CU budget: every subscription is off until 00:00 UTC")
    elif f.get("blocked_filters_today"):
        w.append(f"farm-feed dropped {f['blocked_filters_today']} log filter(s) today (per-filter CU cap)")
    for c, v in (f.get("chains") or {}).items():
        if v.get("status") in ("down", "reconnecting"):
            w.append(f"farm-feed {c}: {v['status']} {v.get('error', '')}".rstrip())
    m = d.get("alchemy_month", {})
    if m.get("projected_cu") and m["projected_cu"] > m.get("allowance", 0):
        w.append(f"Alchemy is on course for {mcu(m['projected_cu'])} CU by {m['ends']}, above the {mcu(m['allowance'])} allowance "
                 "(when it runs out, sends stop too)")
    for p in d.get("prompts", []):
        if p["state"] != "ok":
            w.append(f"prompt of {p['instance']} is {p['bytes']:,} bytes ({p['state']})")
    return w


def extra_tiles(d):
    m, f, sv = d.get("alchemy_month", {}), d.get("feed", {}), d.get("services", [])
    down = [s["unit"] for s in sv if s["active"] != "active"]
    tiles = []
    if "error" in m:
        tiles.append(("Alchemy CU this cycle", "?", m["error"][:60], False))
    else:
        proj = m.get("projected_cu")
        tiles.append(("Alchemy CU this cycle", mcu(m.get("cu")),
                      f"of {mcu(m.get('allowance'))} · on course for {mcu(proj) if proj else '?'} · about ${m.get('usd')}",
                      not proj or proj <= m.get("allowance", 0)))
    if "error" in f:
        tiles.append(("Feed CU today", "?", "farm-feed not answering", False))
    else:
        nsub = sum(len(c.get("subscriptions", [])) for c in (f.get("chains") or {}).values())
        tiles.append(("Feed CU today", str(f.get("cu_today", "?")),
                      ("EXHAUSTED · " if f.get("exhausted") else "") + f"budget {f.get('daily_cu_budget', '?')} · {nsub} subscription(s)",
                      not f.get("exhausted")))
    tiles.append(("Services", f"{len(sv) - len(down)}/{len(sv)}", ", ".join(down) if down else "all active", bool(sv) and not down))
    return tiles


def render_warnings(d):
    w = warnings(d)
    return "<p>" + " ".join(badge(False, x) for x in w) + "</p>" if w else ""


def live_cols(d, live_rows):
    """The live table plus: loss since promotion against the watchdog's stop, realized today, nonces."""
    live = (d["gate"].get("live") or {}) if "error" not in d["gate"] else {}
    cap = d.get("max_live_loss_usd", 30)
    out = []
    for r in live_rows:
        x = d.get("live_loss", {}).get(r["bot"], {})
        loss = x.get("note") or f"{x.get('loss_usd', '?')} of {cap:g} (funded {x.get('funded_usd', '?')})"
        today = d.get("realized_today", {}).get(r["bot"])
        out.append(dict(r, loss_since_promote_usd=loss, realized_today_usd="" if today is None else round(today, 4),
                        nonces=json.dumps(live.get(r["bot"], {}).get("nonces", {}))))
    return out


def intermediate_rows(d):
    bal = (d["gate"].get("intermediate_balances_usd") or {}) if "error" not in d["gate"] else {}
    chains = []
    for k in bal:
        c = k.split(":", 1)[0]
        if c not in chains:
            chains.append(c)
    return [{"chain": c, "native_usd": bal.get(c, 0), "usdc": bal.get(f"{c}:usdc", 0)} for c in chains]


def render_money(d):
    g = d["gate"] if "error" not in d["gate"] else {}
    inter = intermediate_rows(d)
    total = round(sum(r["native_usd"] + r["usdc"] for r in inter), 2)
    return f"""<div class="grid">
<section><h2>Intermediate wallet (${e(total)})</h2>{table(inter)}
<p class="muted" style="font-size:12px">{e(g.get('intermediate', ''))} · a promote on a chain with 0 is refused until it is funded</p></section>
<section><h2>Gate log (latest {len(d.get('gate_log', []))})</h2>{table(d.get('gate_log', []))}</section>
</div>"""


def feed_rows(f):
    chains, subs = [], []
    for c, v in (f.get("chains") or {}).items():
        if v.get("status") != "idle" or v.get("cu_today") or v.get("subscriptions"):
            chains.append({"chain": c, "status": v.get("status"), "connects": v.get("connects"), "cu_today": v.get("cu_today"),
                           "subscriptions": len(v.get("subscriptions", [])), "error": v.get("error", "")})
        for s in v.get("subscriptions", []):
            flt = s.get("filter") or {}
            topics = flt.get("topics") or [""]
            subs.append({"chain": c, "kind": s.get("kind"), "state": s.get("state"), "waiters": s.get("waiters"),
                         "idle_s": s.get("idle_s"), "cu_today": s.get("cu_today"),
                         "filter": (f"{len(flt.get('address', []))} address(es), topic0 {str(topics[0])[:18]}…" if flt
                                    else f"head {s.get('head')}"), "error": s.get("error", "")})
    return chains, subs


def render_infra(d):
    f, m = d.get("feed", {}), d.get("alchemy_month", {})
    if "error" in f:
        feed_html = f"<p class='badge bad'>▲ {e(f['error'])}</p>"
    else:
        chains, subs = feed_rows(f)
        feed_html = (f"<p>{e(f.get('cu_today'))} of {e(f.get('daily_cu_budget'))} CU today · /head on "
                     f"{e(', '.join(f.get('heads_offered_on') or []) or 'no chain')} · up {e(round(f.get('uptime_s', 0) / 3600, 1))} h</p>"
                     + (table(chains) + table(subs) if chains or subs
                        else "<p class='muted'>no subscriptions: no bot is waiting on the feed</p>"))
    month = ("" if "error" in m else
             f"<p class='muted' style='font-size:12px'>cycle {e(m.get('since'))} → {e(m.get('ends'))}: {e(mcu(m.get('cu')))} of "
             f"{e(mcu(m.get('allowance')))} · {e(' · '.join(f'{k} {mcu(v)}' for k, v in sorted(m.get('lanes', {}).items())))} · "
             "the relay's count, without farm-feed</p>")
    return f"""<div class="grid">
<section><h2>Alchemy today, by chain</h2>{table(d.get('rpc_chains', []))}{month}</section>
<section><h2>Feed (8546)</h2>{feed_html}</section>
</div>
<div class="grid">
<section><h2>Services</h2>{table([dict(unit=s['unit'], state=f"{s['active']}/{s['sub']}") for s in d.get('services', [])])}</section>
<section><h2>Prompt sizes (memo above 56,000, refused above 60,000)</h2>{table(d.get('prompts', []))}
<h2>decisions/human (latest)</h2>{table(d.get('decisions', []))}
<h2>KB leads by status</h2>{table(d.get('lead_counts', []))}</section>
</div>"""


def brief_top(d):
    g = d["gate"] if "error" not in d["gate"] else {}
    L = []
    cap = d.get("max_live_loss_usd", 30)
    for bot, x in d.get("live_loss", {}).items():
        nonces = json.dumps((g.get("live") or {}).get(bot, {}).get("nonces", {}))
        L.append(f"  live {bot}: " + (x.get("note") or f"loss since promotion {x.get('loss_usd')} of {cap:g} USD "
                                                          f"(funded {x.get('funded_usd')}, wallet {x.get('value_usd')})") + f" · nonces {nonces}")
    if d.get("realized_today"):
        L.append("realized today (UTC) " + json.dumps(d["realized_today"]))
    inter = intermediate_rows(d)
    if inter:
        L.append("intermediate wallet: " + " · ".join(
            f"{r['chain']} {r['native_usd']}" + (f" + USDC {r['usdc']}" if r["usdc"] else "") for r in inter if r["native_usd"] or r["usdc"])
            + " · zero on: " + (", ".join(r["chain"] for r in inter if not r["native_usd"] and not r["usdc"]) or "none"))
    m = d.get("alchemy_month", {})
    if "error" in m:
        L.append(f"alchemy this cycle: ERROR {m['error']}")
    else:
        L.append(f"alchemy this cycle ({m.get('since')} to {m.get('ends')}, relay count, without feed): {mcu(m.get('cu'))} of "
                 f"{mcu(m.get('allowance'))} CU, on course for {mcu(m['projected_cu']) if m.get('projected_cu') else '?'}, "
                 f"about ${m.get('usd')} · by lane {json.dumps(m.get('lanes'))}")
    f = d.get("feed", {})
    if "error" in f:
        L.append(f"feed: ERROR {f['error']}")
    else:
        chains, subs = feed_rows(f)
        L.append(f"feed: {f.get('cu_today')} of {f.get('daily_cu_budget')} CU today, exhausted={f.get('exhausted')}, "
                 f"/head on {f.get('heads_offered_on')}, {len(subs)} subscription(s)")
        for s in subs:
            L.append(f"  feed {s['chain']} {s['kind']} {s['state']}: {s['filter']} cu {s['cu_today']} waiters {s['waiters']} {s['error']}".rstrip())
        for c in chains:
            if c["status"] in ("down", "reconnecting"):
                L.append(f"  feed {c['chain']}: {c['status']} {c['error']}".rstrip())
    sv = d.get("services", [])
    down = [f"{s['unit']} {s['active']}/{s['sub']}" for s in sv if s["active"] != "active"]
    L.append(f"services: {len(sv) - len(down)}/{len(sv)} active" + (" · NOT active: " + ", ".join(down) if down else ""))
    w = warnings(d)
    if w:
        L += ["", "## Needs a look"] + [f"- {x}" for x in w]
    L += ["", "## Gate log (newest first, JST)"]
    for x in d.get("gate_log", []):
        L.append(f"- {x['at']} {x['op']} {x['bot']} {x['chain']} {x['detail']} [{x['by']}]".replace("  ", " "))
    L += ["", "## Alchemy today by chain (CU)"]
    for x in d.get("rpc_chains", []):
        if "error" in x:
            L.append(f"- ERROR {x['error']}")
        else:
            L.append(f"- {x['chain']}: live {x['live']} paper {x['paper']} research {x['research']} · ok {x['ok']} failed {x['failed']} · {x['avg_ms']} ms")
    L += ["", "## Prompt sizes (bytes)", "- " + (" · ".join(f"{p['instance']} {p['bytes']}" + ("" if p["state"] == "ok" else f" ({p['state']})")
                                                           for p in d.get("prompts", [])) or "(none readable)")]
    L += ["", "## decisions/human (latest)"] + [f"- {x['mtime']} {x['file']}" for x in d.get("decisions", [])]
    L += ["", "## KB leads by status", "- " + " · ".join(f"{x.get('status')} {x.get('n')}" for x in d.get("lead_counts", []) if "error" not in x)]
    return L


