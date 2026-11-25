#!/usr/bin/env python3
"""Offline tests of phase 16c (farm-dash: grad bots, graduation candidates).

  test-16c.py <farm-dash>            tests in a temporary directory (no network, no gate, no systemd)
  test-16c.py <farm-dash> --old      same, report only (the installed farm-dash fails them before 16c)
  test-16c.py <farm-dash> --probe    read-only look at the real bots/live and gate.log, as the
                                     calling user: promote time, won / sends and where they came from
"""
import datetime as dt
import importlib.machinery
import importlib.util
import json
import os
import sys
import tempfile
import time
import types

PATH = sys.argv[1] if len(sys.argv) > 1 else "farm-dash"
MODE = sys.argv[2] if len(sys.argv) > 2 else ""


def load():
    loader = importlib.machinery.SourceFileLoader("farmdash16c", PATH)
    spec = importlib.util.spec_from_loader("farmdash16c", loader)
    m = importlib.util.module_from_spec(spec)
    loader.exec_module(m)
    return m


def iso(t):
    return dt.datetime.fromtimestamp(t, dt.timezone.utc).isoformat()


def probe():
    m = load()
    pt = m.promote_times()
    bots = sorted(n for n in os.listdir(f"{m.WS}/bots/live") if os.path.isdir(f"{m.WS}/bots/live/{n}"))
    ops = {}
    try:
        with open(f"{m.STATE}/gate.log", encoding="utf-8") as f:
            for line in f:
                try:
                    r = json.loads(line)
                except ValueError:
                    continue
                if isinstance(r, dict) and "promote" in str(r.get("op", "")):
                    ops[r["op"]] = ops.get(r["op"], 0) + 1
    except OSError as exc:
        print(f"  gate.log unreadable: {exc}")
    print(f"  gate.log ops containing 'promote': {ops}")
    now = time.time()
    for b in bots:
        t = pt.get(b)
        s = m.send_counts(b, t)
        print(f"  {b}: promoted {m.jst(t) if t else '? (no promote record)'}"
              f" ({'?' if t is None else round((now - t) / 3600, 1)} h) · won {s['won']} of {s['sends']} {s['results']} · {s['source']}")


def main():
    if MODE == "--probe":
        probe()
        return
    results = []

    def check(name, cond):
        results.append((name, bool(cond)))
        print(("  ok   " if cond else "  FAIL ") + name)

    try:
        m = load()
    except Exception as exc:                     # noqa: BLE001
        print(f"  FAIL load: {exc!r}")
        sys.exit(0 if MODE == "--old" else 1)
    need = ("promote_times", "send_counts", "graduation", "render_grad", "grad_brief")
    if not all(hasattr(m, n) for n in need):
        print(f"  {sum(hasattr(m, n) for n in need)} of {len(need)} 16c functions present")
        print("result: 0 of 9 passed")
        sys.exit(0 if MODE == "--old" else 1)

    tmp = tempfile.mkdtemp(prefix="t16c-")
    m.WS, m.STATE = f"{tmp}/ws", f"{tmp}/state"
    os.makedirs(m.STATE)
    now = time.time()
    t_a, t_b, t_new = now - 100 * 3600, now - 90 * 3600, now - 10 * 3600
    live_ids = ["trial-a-base", "trial-b-base", "trial-c-ethereum", "trial-d-arbitrum", "oneshot-x-base", "grad-a-base"]
    for b in live_ids + ["trial-gone-base"]:
        if b != "trial-gone-base":
            os.makedirs(f"{m.WS}/bots/live/{b}/logs")
    os.makedirs(f"{m.WS}/bots/paper/grad-d-arbitrum")
    with open(f"{m.STATE}/gate.log", "w") as f:
        rec = [{"op": "promote", "bot": "trial-a-base", "at": iso(now - 300 * 3600)},           # earlier promote
               {"op": "promote", "bot": "trial-a-base", "at": iso(t_a)},
               {"op": "promote", "bot": "trial-b-base", "at": int(t_b)},
               {"op": "promote", "bot": "trial-c-ethereum", "at": iso(t_a)},
               {"op": "promote", "bot": "trial-d-arbitrum", "at": iso(t_a)},
               {"op": "promote", "bot": "grad-a-base", "at": iso(t_new)},
               {"op": "promote", "bot": "trial-b-base", "at": iso(now), "ok": False, "why": "refused"},
               {"op": "fund", "bot": "trial-a-base", "at": iso(now)}]
        f.write("\n".join(json.dumps(r) for r in rec) + "\nnot json\n")

    # 1. promote_times: newest successful promote, refused one ignored, epoch and ISO both read
    pt = m.promote_times()
    check("promote_times: newest promote, refused skipped, epoch + ISO",
          abs(pt.get("trial-a-base", 0) - t_a) < 2 and abs(pt.get("trial-b-base", 0) - int(t_b)) < 2 and "oneshot-x-base" not in pt)

    # 2. send_counts: lines before promotion skipped, JSON / text / timeless lines, incremental appends
    lg = f"{m.WS}/bots/live/trial-a-base/logs/run.jsonl"
    with open(lg, "w") as f:
        f.write(json.dumps({"ts": iso(t_a - 3600), "send_result": "won"}) + "\n")     # paper era: not counted
        for i in range(2):
            f.write(json.dumps({"ts": now - 50 * 3600 + i, "send_result": "won", "tx": "0x1"}) + "\n")
        f.write(json.dumps({"time": iso(now - 40 * 3600), "send_result": "lost"}) + "\n")
        f.write(f"{iso(now - 30 * 3600)[:19].replace('T', ' ')} INFO send_result=won tx=0x2\n")
        f.write("send_result: reverted (no time on this line)\n")
        f.write("heartbeat\n")
    s = m.send_counts("trial-a-base", pt["trial-a-base"])
    check("send_counts: 3 won of 5 since promotion (paper-era line skipped)", s["won"] == 3 and s["sends"] == 5)
    with open(lg, "a") as f:
        f.write(json.dumps({"ts": now - 5, "send_result": "won"}) + "\n" + '{"ts": %d, "send_result": "won"' % now)
    s2 = m.send_counts("trial-a-base", pt["trial-a-base"])
    with open(lg, "a") as f:
        f.write("}\n")
    s3 = m.send_counts("trial-a-base", pt["trial-a-base"])
    check("send_counts: appends read once, an unfinished line waits", s2["won"] == 4 and s3["won"] == 5 and s3["sends"] == 7)

    for b, won in (("trial-b-base", 3), ("trial-c-ethereum", 5), ("trial-d-arbitrum", 4), ("grad-a-base", 1)):
        with open(f"{m.WS}/bots/live/{b}/logs/bot.log", "w") as f:
            for i in range(won):
                f.write(json.dumps({"ts": now - 3600 - i, "send_result": "won"}) + "\n")

    # 3. journal fallback when the files hold no send_result line
    real_run = m.subprocess.run
    m.subprocess.run = lambda cmd, **kw: types.SimpleNamespace(
        stdout="x\nsend_result: won\nsend_result: lost\n" if cmd[0] == "journalctl" else "", stderr="", returncode=0)
    try:
        sj = m.send_counts("oneshot-x-base", None)
    finally:
        m.subprocess.run = real_run
    check("send_counts: journal fallback", sj["won"] == 1 and sj["sends"] == 2 and sj["source"] == "journal")
    m._journal_cache["oneshot-x-base"] = (time.monotonic(), None, {}, "no entries")

    # 4. graduation: candidates, one short, ethereum / one-shot / grad excluded, grad status
    g = {"live": {b: {"service": "ActiveState=active SubState=running", "address": "0xabc", "balances_usd": {"base": 20}}
                  for b in live_ids + ["trial-gone-base"]}}
    lp = {"trial-a-base": 2.5, "trial-b-base": 0.4, "trial-c-ethereum": 9.0, "trial-d-arbitrum": 1.2, "grad-a-base": 3.0}
    gr = m.graduation(g, lp, now=now)
    cands = [c["bot"] for c in gr["candidates"]]
    near = {c["bot"]: c["short_of"] for c in gr["near"]}
    check("graduation: candidates = trial-a-base, trial-d-arbitrum (ethereum, one-shot, grad excluded)",
          cands == ["trial-a-base", "trial-d-arbitrum"] and "trial-gone-base" not in gr["stats"])
    check("graduation: trial-b-base one short on pnl; grad status live / in paper",
          list(near) == ["trial-b-base"] and "pnl" in near["trial-b-base"]
          and {c["bot"]: c["grad"] for c in gr["candidates"]} == {"trial-a-base": "live", "trial-d-arbitrum": "in paper"}
          and gr["grad_live"] == ["grad-a-base"] and gr["grad_paper"] == ["grad-d-arbitrum"])

    # 5. page and brief
    d = {"now": "test", "gate": dict(g, frozen=False, halted=False, capital_usd=100, max_capital_usd=2000),
         "relay": {"alchemy_cu_today": {}}, "agents": [], "paper": [{"id": "grad-d-arbitrum", "service": "running", "review": "wait"}],
         "timers": [], "runs": [], "rpc": [], "ledger": [], "ledger_runs": [], "kb": {}, "leads": [], "sessions": [],
         "inbox_human": [], "inbox_meta": [], "inbox_live": [], "pnl": [("2026-11-23", 0.0)],
         "feed": {"error": "test"}, "alchemy_month": {"error": "test"}, "rpc_chains": [], "services": [], "gate_log": [],
         "realized_today": {}, "sweep_pending": {}, "live_loss": {}, "live_pnl": lp,
         "live_pnl_today": {"since": "00:00 UTC", "by_bot": {"grad-a-base": 0.5}, "total": 0.5, "history": {}},
         "swept_total": 0.0, "max_live_loss_usd": 30, "prompts": [], "decisions": [], "lead_counts": [], "graduation": gr}
    page = m.render(d)
    i_grad, i_trial, i_cand = page.find("<h2>Grad bots (1 of 5)"), page.find("<h2>Live bots: trial and one-shot (6)"), page.find("<h2>Graduation candidates (2)")
    grad_tbl = page[i_grad:i_trial]
    check("render: grad table first, holds only grad-a-base; trial table; candidates; tile",
          0 < i_grad < i_trial < i_cand and "grad-a-base" in grad_tbl and "trial-a-base" not in grad_tbl
          and "grad-d-arbitrum (review wait)" in grad_tbl and ">Grad bots<" in page and "<h2>Live bots</h2>" not in page)
    b = m.brief(d)
    check("brief: grad line, candidates, one short",
          "grad bots live: 1 of 5 · in paper: grad-d-arbitrum" in b and "  grad grad-a-base: pnl since promotion +3.00 · today +0.50 · won 1 of 1 sends" in b
          and "  - trial-a-base: live 100.0 h · pnl +2.50 · won 5/7 sends · grad live" in b and "one condition short: trial-b-base (pnl +0.40 < +1)" in b)
    many = dict(gr, grad_live=[f"grad-{i}-base" for i in range(6)])
    check("warnings: more than 5 live grads", any("6 grad bots are live" in w for w in m.warnings(dict(d, graduation=many))))

    n = sum(ok for _, ok in results)
    print(f"result: {n} of {len(results)} passed")
    sys.exit(0 if MODE == "--old" or n == len(results) else 1)


if __name__ == "__main__":
    main()
