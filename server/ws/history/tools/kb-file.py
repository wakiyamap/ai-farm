#!/usr/bin/env python3
"""Run `kb add` / `kb update` with the JSON read from a file instead of argv.

Why: 4 inbox/meta notes (2026-11-07..08: kb-add-long-argument-truncation,
2026-11-07-kb-argv-tail-cut, kb-write-long-value-parse-error,
kb-parse-long-reason-2026-11-08) report long values failing with
"not valid JSON: Expecting ',' delimiter" at a column equal to the input
length. `kb` itself has no length limit (it json.loads argv[...] as given), so
the text was cut or its quoting broken before kb saw it (shell single quotes,
an apostrophe in the text, the agent's tool layer). Writing the JSON to a file
with the Write tool and passing the path avoids shell quoting entirely, and on
a parse error this tool prints the length and the tail it actually read.

Usage (one command, no chaining):
  python3 /srv/farm/ws/tools/kb-file.py add <table> --file scratch/<name>.json
  python3 /srv/farm/ws/tools/kb-file.py update <table> <id> --file scratch/<name>.json

The file holds exactly the JSON object you would have passed to kb. kb
validation, author/run recording and duplicate checks are unchanged: this tool
only calls /opt/farm/bin/kb with the re-serialized object as one argv element
(no shell).
"""
import json
import os
import re
import subprocess
import sys

KB = "/opt/farm/bin/kb"
MAX_BYTES = 64 * 1024


def die(msg, code=2):
    print(f"kb-file: {msg}", file=sys.stderr)
    sys.exit(code)


def load(path):
    if not os.path.isfile(path):
        die(f"no such file: {path}")
    size = os.path.getsize(path)
    if size > MAX_BYTES:
        die(f"{path} is {size} bytes (> {MAX_BYTES}); move long evidence into a wiki page and link it")
    with open(path, encoding="utf-8") as fh:
        text = fh.read()
    try:
        obj = json.loads(text)
    except ValueError as exc:
        tail = text[-80:].replace("\n", "\\n")
        die(f"{path} is not valid JSON: {exc}; read {len(text)} chars, tail: {tail!r}")
    if not isinstance(obj, dict):
        die("the file must hold one JSON object ({...})")
    return obj


# inbox/meta/2026-11-15-kb-update-wrong-id-near-miss.md: `update protocols 214` meant id 14 and
# overwrote bsc/ming silently. Echo the row's key fields before the update, and refuse when the
# JSON carries a key field that differs from the row (key fields can't be changed anyway).
KEYS = {"protocols": ("chain", "protocol"), "actors": ("chain", "address"), "leads": ("chain", "target")}


def check_target_row(table, row_id, obj):
    keys = KEYS.get(table)
    if not keys:
        return
    proc = subprocess.run([KB, "query", "--json",
                           f"SELECT {', '.join(keys)} FROM {table} WHERE id = {int(row_id)} LIMIT 1"],
                          capture_output=True, text=True, check=False)
    line = next((l for l in proc.stdout.splitlines() if l.startswith("{")), None)
    if not line:
        die(f"{table} id {row_id} not found (kb query: {proc.stderr.strip()[:200]})")
    row = json.loads(line)
    print(f"kb-file: updating {table} {row_id}: " + ", ".join(f"{k}={str(row[k])[:80]}" for k in keys),
          file=sys.stderr)
    bad = [k for k in keys if k in obj and str(obj[k]).lower() != str(row[k]).lower()]
    if bad:
        die(f"{table} id {row_id} has " + ", ".join(f"{k}={str(row[k])[:80]!r}" for k in bad)
            + " but the file says " + ", ".join(f"{k}={str(obj[k])[:80]!r}" for k in bad)
            + ": wrong id? Look it up with kb query; drop key fields from the file to skip this check")
    # inbox/meta/2026-11-15-kb-file-update-payload-fields.md: kb refuses an update whose payload
    # carries key fields, even unchanged ones. They have just been checked against the row, so
    # strip them here and the file may carry them as a wrong-id guard.
    for k in keys:
        if k in obj:
            del obj[k]
            print(f"kb-file: key field {k} matches the row; checked, not sent", file=sys.stderr)
    if not obj:
        die("nothing to update: the file holds only key fields")


# inbox/meta/2026-11-21-scout-kbfile-id-race.md: a scout quoted "attempts id=1750" for a row
# that was really 3472 (1750 is an 11-17 row; revisions show one insert, no race). Re-read the
# new row by id and print its key fields, so the id an agent copies is checked against its text.
ADD_KEYS = dict(KEYS, attempts=("chain", "target", "outcome"))


def echo_added_row(table, out):
    m = re.search(r"ok added \S+ id=(\d+)", out)
    keys = ADD_KEYS.get(table)
    if not m or not keys:
        return
    proc = subprocess.run([KB, "query", "--json",
                           f"SELECT id, {', '.join(keys)} FROM {table} WHERE id = {int(m.group(1))} LIMIT 1"],
                          capture_output=True, text=True, check=False)
    line = next((l for l in proc.stdout.splitlines() if l.startswith("{")), None)
    if line:
        row = json.loads(line)
        print(f"kb-file: stored row {table}:{row['id']} = "
              + ", ".join(f"{k}={str(row[k])[:80]}" for k in keys) + " (quote this id)")


def main(argv):
    if not argv or argv[0] in ("-h", "--help", "help"):
        print(__doc__.strip())
        return 0
    if "--file" not in argv:
        die("missing --file <path>; run with --help")
    i = argv.index("--file")
    if i + 1 >= len(argv):
        die("--file needs a path")
    path = argv[i + 1]
    rest = argv[:i] + argv[i + 2:]
    if len(rest) == 2 and rest[0] == "add":
        kb_args = ["add", rest[1]]
    elif len(rest) == 3 and rest[0] == "update" and rest[2].isdigit():
        kb_args = ["update", rest[1], rest[2]]
    else:
        die("usage: add <table> --file <path> | update <table> <id> --file <path>")
    obj = load(path)
    if kb_args[0] == "update":
        check_target_row(kb_args[1], kb_args[2], obj)
    payload = json.dumps(obj, ensure_ascii=False)
    if kb_args[0] == "add":
        proc = subprocess.run([KB, *kb_args, payload], capture_output=True, text=True, check=False)
        sys.stdout.write(proc.stdout)
        sys.stderr.write(proc.stderr)
        if proc.returncode == 0:
            echo_added_row(kb_args[1], proc.stdout)
        return proc.returncode
    proc = subprocess.run([KB, *kb_args, payload], check=False)
    if proc.returncode and kb_args[0] == "update":
        print("kb-file: hint: an update payload holds only the columns you change (see `kb schema`);"
              " key fields are checked and dropped by this tool", file=sys.stderr)
    return proc.returncode


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
