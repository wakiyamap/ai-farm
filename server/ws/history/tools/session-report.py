#!/usr/bin/env python3
"""Append-only session report writer and coverage check.

Why: on 2026-11-04 only 2 of 18 runs that wrote KB attempts rows have a line in
logs/sessions/2026-11-04.jsonl (file born 08:20Z, so earlier lines were never
written or the file was replaced). Write/Edit-tool "appends" replace the file
(new inode), and a forgotten Read means lost lines. This tool appends with
O_APPEND and never rewrites existing content.

Usage (one command, no chaining):
  python3 tools/session-report.py append --file scratch/report-<run_id>.json
  python3 tools/session-report.py append --json '{"run_id": ...}'
  python3 tools/session-report.py coverage [--date YYYY-MM-DD]
"""
import argparse
import datetime as dt
import json
import os
import sqlite3
import sys

WS = os.environ.get("FARM_WS", "/srv/farm/ws")
LOG_DIR = os.path.join(WS, "logs", "sessions")
KB = os.path.join(WS, "kb", "knowledge.db")

OUTCOMES = {
    "earner": {"paper_placed", "fix_submitted", "lead_recorded", "dead_end_recorded", "blocked_infra", "no_target", "aborted"},
    "paper-reviewer": {"reviewed", "aborted"},
    "meta": {"reviewed", "changed", "reverted", "report_written"},
    "live-operator": {"stopped", "restarted", "sent_back", "confirmed_watchdog", "escalated", "no_action"},
    "researcher": {"proposal_written", "finding_recorded", "improvement_made", "followup_measured", "nothing_new"},
    # phase 14a/14b (human 2026-11-17): builder.md and scout.md "Session report outcomes"
    "builder": {"paper_placed", "fix_submitted", "lead_recorded", "dead_end_recorded", "blocked_infra", "no_target", "aborted"},
    "scout": {"scouted", "no_candidate", "aborted"},
}
LISTS = ("kb_rows", "wiki_pages", "bot_ids")
STRS = ("run_id", "role", "model", "target", "outcome", "notes")


def today():
    return dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d")


def validate(rep):
    errs = []
    if not isinstance(rep, dict):
        return ["report must be a JSON object"]
    for k in STRS:
        if not isinstance(rep.get(k), str) or not rep.get(k).strip():
            errs.append(f"{k}: required non-empty string")
    for k in LISTS:
        v = rep.get(k)
        if not isinstance(v, list) or not all(isinstance(x, str) for x in v):
            errs.append(f"{k}: required list of strings (may be empty)")
    if not isinstance(rep.get("injection_seen"), bool):
        errs.append("injection_seen: required true/false")
    role = rep.get("role")
    if role in OUTCOMES:
        if rep.get("outcome") not in OUTCOMES[role]:
            errs.append(f"outcome: '{rep.get('outcome')}' not valid for {role}; one of {sorted(OUTCOMES[role])}")
    elif isinstance(role, str):
        errs.append(f"role: unknown '{role}'; one of {sorted(OUTCOMES)}")
    return errs


def logged_run_ids(path):
    ids = set()
    if not os.path.exists(path):
        return ids
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            # a line may hold two glued objects (a `>>` append without "\n"): decode them all
            dec, pos = json.JSONDecoder(), 0
            while pos < len(line):
                try:
                    o, end = dec.raw_decode(line, pos)
                except ValueError:
                    break
                pos = end
                while pos < len(line) and line[pos].isspace():
                    pos += 1
                if isinstance(o, dict):
                    rid = o.get("run_id") or o.get("session_id")
                    if rid:
                        ids.add(rid)
    return ids


def cmd_append(a):
    if bool(a.file) == bool(a.json):
        sys.exit("give exactly one of --file or --json")
    raw = open(a.file, encoding="utf-8").read() if a.file else a.json
    try:
        rep = json.loads(raw)
    except ValueError as e:
        sys.exit(f"invalid JSON: {e}")
    # Model comes from the harness (decisions/human/2026-11-07-fork-deploy-meta-bash.md §3):
    # 11-06 lines mixed qwen3.8-flash-next / qwen38-flash-next. A differing given value goes to notes.
    env_model = os.environ.get("FARM_MODEL", "").strip()
    if env_model and isinstance(rep, dict):
        given = rep.get("model")
        if isinstance(given, str) and given.strip() and given.strip() != env_model:
            rep["notes"] = f"{rep.get('notes') or ''} [model given: {given.strip()}]".strip()
        rep["model"] = env_model
    errs = validate(rep)
    if errs:
        sys.exit("rejected:\n  " + "\n  ".join(errs))
    path = os.path.join(LOG_DIR, f"{a.date or today()}.jsonl")
    if rep["run_id"] in logged_run_ids(path):
        sys.exit(f"rejected: run_id {rep['run_id']} already has a line in {path}")
    line = json.dumps(rep, ensure_ascii=False, separators=(", ", ": ")) + "\n"
    # A `>>` append without a trailing newline (scout ff6bac70, 2026-11-16 line 135) glues the next
    # report onto the same line; start on a fresh line in that case.
    try:
        with open(path, "rb") as fh:
            fh.seek(0, os.SEEK_END)
            if fh.tell() > 0:
                fh.seek(-1, os.SEEK_END)
                if fh.read(1) != b"\n":
                    line = "\n" + line
    except OSError:
        pass
    old = os.umask(0o002)
    try:
        fd = os.open(path, os.O_WRONLY | os.O_APPEND | os.O_CREAT, 0o664)
    finally:
        os.umask(old)
    try:
        os.write(fd, line.encode("utf-8"))
    finally:
        os.close(fd)
    print(f"appended to {path}")


def cmd_coverage(a):
    d = a.date or today()
    logged = logged_run_ids(os.path.join(LOG_DIR, f"{d}.jsonl"))
    con = sqlite3.connect(f"file:{KB}?mode=ro", uri=True)
    rows = con.execute(
        "SELECT run_id, author, min(created_at) FROM attempts "
        "WHERE substr(created_at,1,10)=? AND run_id IS NOT NULL AND run_id<>'' "
        "GROUP BY run_id ORDER BY 3", (d,)).fetchall()
    missing = [r for r in rows if r[0] not in logged]
    print(f"{d}: runs with KB attempts={len(rows)} with_report={len(rows)-len(missing)} missing={len(missing)}")
    for rid, author, first in missing:
        print(f"  missing {rid} {author} first_attempt={first}")


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)
    ap = sub.add_parser("append")
    ap.add_argument("--file")
    ap.add_argument("--json")
    ap.add_argument("--date", help="override UTC date (default today)")
    ap.set_defaults(fn=cmd_append)
    cp = sub.add_parser("coverage")
    cp.add_argument("--date")
    cp.set_defaults(fn=cmd_coverage)
    a = p.parse_args()
    a.fn(a)


if __name__ == "__main__":
    main()
