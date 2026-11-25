#!/usr/bin/env python3
"""Phase 10h: exact-text patch for ledger-ingest - one eth_getLogs per (source, chain) instead of
one per emitter, and no events lost when the CU budget runs out inside a block range.

  patch-10h.py check <ledger-ingest>
  patch-10h.py apply <ledger-ingest> <outdir>

The old text (the whole ingest_source function) must occur exactly once, or nothing is written.
Safe to re-run (marker).
"""
import os
import sys

LEDGER = [
("ingest_source: emitters of a (source, chain) share one eth_getLogs; the cursor stops where the budget ran out",
r'''def ingest_source(con, rpc, cfg, s, heads, budget, stats):
    """Advance this source on every chain while budget allows. Returns events inserted."""
    inserted = 0
    for chain, addrs in s["chains"].items():
        if chain not in heads:
            continue                                  # head unreadable this run (runs.note says why)
        head = heads[chain] - cfg["confirmations"]
        step = cfg["blocks_per_call"][chain]
        backfill_from = head - int(cfg["backfill_days"] * 86400 / cfg["block_time_s"][chain])
        for addr in addrs:
            addr = addr.lower()
            row = con.execute("SELECT next_block, verified FROM cursors WHERE source_id=? AND chain=? AND contract=?",
                              (s["id"], chain, addr)).fetchone()
            if row is None:
                if rpc.cu > budget:
                    return inserted
                ok = verify_contract(rpc, chain, addr)
                con.execute("INSERT INTO cursors VALUES (?,?,?,?,?)", (s["id"], chain, addr, max(backfill_from, 0), int(ok)))
                con.commit()
                if not ok:
                    stats["unverified"].append(f"{s['id']}@{chain}:{addr}")
                    continue
                next_block = max(backfill_from, 0)
            else:
                next_block, verified = row
                if not verified:
                    continue
            while next_block <= head and rpc.cu <= budget:
                to_block = min(next_block + step - 1, head)
                try:
                    logs = rpc.call(chain, "eth_getLogs", [{"fromBlock": hex(next_block), "toBlock": hex(to_block),
                                                            "address": addr, "topics": [s["topic0"]]}])
                except RuntimeError as exc:
                    msg = str(exc).lower()
                    if "range" in msg or "limit" in msg or "too many" in msg or "10000" in msg:
                        step = max(step // 4, 50)
                        continue
                    stats["errors"].append(str(exc))
                    break
                block_ts = {}
                for log in logs:
                    tx = log["transactionHash"]
                    fields = decode(s, log)
                    # actor: a named event field, or the tx sender (costs one receipt call)
                    tx_from = None
                    actor = fields.get(s["actor_field"]) if s["actor_field"] != "tx_from" else None
                    if actor is None:
                        if rpc.cu > budget:
                            break
                        rcpt = rpc.call(chain, "eth_getTransactionReceipt", [tx])
                        tx_from = rcpt["from"].lower() if rcpt else None
                        actor = tx_from
                    blk = int(log["blockNumber"], 16)
                    cur = con.execute("INSERT OR IGNORE INTO events VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                                      (chain, blk, tx, int(log["logIndex"], 16), block_ts.get(blk), s["id"], s["protocol"],
                                       s["kind"], addr, actor, tx_from, json.dumps(fields, separators=(",", ":"))))
                    inserted += cur.rowcount
                next_block = to_block + 1
                con.execute("UPDATE cursors SET next_block=? WHERE source_id=? AND chain=? AND contract=?",
                            (next_block, s["id"], chain, addr))
                con.commit()
    return inserted


''',
r'''def ingest_source(con, rpc, cfg, s, heads, budget, stats):
    """Advance this source on every chain while budget allows. Returns events inserted.

    One eth_getLogs covers every emitter of a (source, chain) that stands at the same block (10h).
    Until 10h each emitter was queried on its own, so a source with N emitters paid N * 60 CU a
    run only to stay at the head: with the 600 CU fair share, the 12th emitter of a source (and
    every later chain) was never initialized. Emitters that lag (a new one still backfilling) are
    advanced first, alone, until they reach the block of the others and join their call."""
    inserted = 0
    for chain, addrs in s["chains"].items():
        if chain not in heads:
            continue                                  # head unreadable this run (runs.note says why)
        head = heads[chain] - cfg["confirmations"]
        step = cfg["blocks_per_call"][chain]
        backfill_from = max(head - int(cfg["backfill_days"] * 86400 / cfg["block_time_s"][chain]), 0)
        addrs = list(dict.fromkeys(a.lower() for a in addrs))
        rows = {r[0]: (r[1], r[2]) for r in con.execute(
            "SELECT contract, next_block, verified FROM cursors WHERE source_id=? AND chain=?", (s["id"], chain))}
        at = {}                                       # verified emitter -> next block to read
        for addr in addrs:
            if addr in rows:
                if rows[addr][1]:
                    at[addr] = rows[addr][0]
                continue
            if rpc.cu > budget:
                break                                 # the rest is initialized on a later run
            ok = verify_contract(rpc, chain, addr)
            con.execute("INSERT INTO cursors VALUES (?,?,?,?,?)", (s["id"], chain, addr, backfill_from, int(ok)))
            con.commit()
            if ok:
                at[addr] = backfill_from
            else:
                stats["unverified"].append(f"{s['id']}@{chain}:{addr}")
        failed = set()                                # emitters whose call failed this run
        while rpc.cu <= budget:
            behind = {a: n for a, n in at.items() if n <= head and a not in failed}
            if not behind:
                break
            lo = min(behind.values())
            group = sorted(a for a, n in behind.items() if n == lo)
            ahead = [n for n in behind.values() if n > lo]
            to_block = min(lo + step - 1, head, min(ahead) - 1 if ahead else head)
            try:
                logs = rpc.call(chain, "eth_getLogs", [{"fromBlock": hex(lo), "toBlock": hex(to_block),
                                                        "address": group if len(group) > 1 else group[0],
                                                        "topics": [s["topic0"]]}])
            except RuntimeError as exc:
                msg = str(exc).lower()
                if "range" in msg or "limit" in msg or "too many" in msg or "10000" in msg:
                    step = max(step // 4, 50)
                    continue
                stats["errors"].append(str(exc))
                failed.update(group)                  # the other emitters of this chain still advance
                continue
            logs = sorted(logs, key=lambda l: (int(l["blockNumber"], 16), int(l["logIndex"], 16)))
            stop_at = None                            # first block NOT stored, when the budget ran out
            for log in logs:
                tx = log["transactionHash"]
                blk = int(log["blockNumber"], 16)
                contract = (log.get("address") or group[0]).lower()
                fields = decode(s, log)
                # actor: a named event field, or the tx sender (costs one receipt call)
                tx_from = None
                actor = fields.get(s["actor_field"]) if s["actor_field"] != "tx_from" else None
                if actor is None:
                    if rpc.cu > budget and blk > lo:
                        # Out of budget inside the range: the cursor stops at this block and the
                        # next run reads on from here. Until 10h the cursor moved past the whole
                        # range and the remaining events were lost. (The first block of a range is
                        # always finished, so every run makes progress.)
                        stop_at = blk
                        break
                    rcpt = rpc.call(chain, "eth_getTransactionReceipt", [tx])
                    tx_from = rcpt["from"].lower() if rcpt else None
                    actor = tx_from
                cur = con.execute("INSERT OR IGNORE INTO events VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                                  (chain, blk, tx, int(log["logIndex"], 16), None, s["id"], s["protocol"],
                                   s["kind"], contract, actor, tx_from, json.dumps(fields, separators=(",", ":"))))
                inserted += cur.rowcount
            next_block = stop_at if stop_at is not None else to_block + 1
            for a in group:
                at[a] = next_block
                con.execute("UPDATE cursors SET next_block=? WHERE source_id=? AND chain=? AND contract=?",
                            (next_block, s["id"], chain, a))
            con.commit()
            if stop_at is not None:
                break
    return inserted


''',
"One eth_getLogs covers every emitter"),
]


def plan(text, hunks):
    """Returns (new_text, report lines). Raises ValueError when an old text is not found exactly once."""
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
        out, lines = plan(text, LEDGER)
    except ValueError as exc:
        sys.exit(f"patch-10h: {os.path.basename(path)}: {exc}")
    print(f"{os.path.basename(path)}:")
    print("\n".join(lines))
    if argv[0] == "apply":
        with open(os.path.join(argv[2], os.path.basename(path)), "w", encoding="utf-8") as f:
            f.write(out)


if __name__ == "__main__":
    main(sys.argv[1:])
