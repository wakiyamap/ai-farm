#!/usr/bin/env python3
"""Redact secrets and host/network identifiers from a directory tree, in place.

Usage:
  python3 -I sanitize.py <dir> [--secrets <file>] [--identities <file>]
                         [--wordlist <bip39-english.txt>] [--hints <file>] [--check-only]

- --identities: operator-specific names (host, user, organisation) are kept out of
  this file and read from a private TSV: <regex> TAB <replacement> [TAB i].
  A replacement of "-" makes the pattern a residual check only.
- --check-only: run the residual scan without changing anything.

- Text files: regex rules below, plus exact-match replacement of every string
  listed in --secrets (one per line; the file itself is never copied).
- SQLite files: the same replacement on every TEXT value in every table,
  then VACUUM so old pages do not keep the original text.
- Other binary files: scanned for exact secrets; a hit deletes the file.
- Symlinks, sockets, FIFOs and device nodes are deleted (never published).
- After redaction, a residual scan reports anything that still looks like a
  secret. Precise findings (an exact secret, the seed's words in any spacing or
  punctuation, a key-bearing URL, a vendor key, a host/network identifier) make
  the exit code 2. Heuristic hints (64-hex near a key word, 12+ BIP-39 words in
  a row) are noisy in contract sources and are only written to --hints <file>.
- Any other failure exits with code 1 (the tree is then only partly redacted
  and must not be packed).

The rules never print a secret value; findings show the file and line number
with the match masked.
"""
import os
import re
import sqlite3
import stat
import sys

RULES = [
    # Private key blocks and extended keys.
    (re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----.*?-----END [A-Z ]*PRIVATE KEY-----", re.S),
     "<REDACTED_PRIVATE_KEY>"),
    (re.compile(r"\b[xt]prv[1-9A-HJ-NP-Za-km-z]{100,}"), "<REDACTED_KEY>"),
    # RPC URLs that embed the key in the path.
    (re.compile(r"((?:https?|wss?)://[A-Za-z0-9.-]*alchemy\.com/v2/)[A-Za-z0-9_-]+"), r"\1<REDACTED>"),
    (re.compile(r"((?:https?|wss?)://[A-Za-z0-9.-]*(?:infura\.io|quiknode\.pro|ankr\.com|blastapi\.io|drpc\.org)/(?:v3/|rpc/)?)[A-Za-z0-9_-]{16,}"),
     r"\1<REDACTED>"),
    # Query-string credentials.
    (re.compile(r"([?&](?:api[_-]?key|apikey|access_token|token|auth|key)=)[^&\s\"'<>]+", re.I), r"\1<REDACTED>"),
    # key: value / "key": "value" style credentials (addresses are kept).
    (re.compile(r"(?i)((?:x-api-key|authorization|api[_-]?key|apikey|client[_-]?secret|secret|access[_-]?token|refresh[_-]?token|id[_-]?token|password|passwd)[\"']?\s*[:=]\s*[\"']?)"
                r"(?:Bearer\s+)?(?!0x[0-9a-fA-F]{40}\b)(?!<REDACTED)[A-Za-z0-9._~+/=-]{16,}"),
     r"\1<REDACTED>"),
    (re.compile(r"(?i)\bBearer\s+(?!<REDACTED)[A-Za-z0-9._~+/=-]{16,}"), "Bearer <REDACTED>"),
    # Vendor key formats.
    (re.compile(r"\bsk-(?:ant-[a-z0-9]+-|proj-)?[A-Za-z0-9_-]{20,}"), "<REDACTED_KEY>"),
    (re.compile(r"\bgh[pousr]_[A-Za-z0-9]{30,}"), "<REDACTED_KEY>"),
    (re.compile(r"\bgithub_pat_[A-Za-z0-9_]{40,}"), "<REDACTED_KEY>"),
    (re.compile(r"\btskey-[A-Za-z0-9-]{16,}"), "<REDACTED_KEY>"),
    (re.compile(r"\beyJ[A-Za-z0-9_-]{10,}\.eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}"), "<REDACTED_JWT>"),
    # Network identifiers.
    (re.compile(r"\b[a-z0-9-]+\.tail[0-9a-f]{4,}\.ts\.net\b"), "<tailnet-host>"),
    (re.compile(r"\btail[0-9a-f]{4,}\.ts\.net\b"), "<tailnet>"),
    (re.compile(r"\b192\.168\.\d{1,3}\.\d{1,3}\b"), "<lan-ip>"),
    (re.compile(r"\b10\.\d{1,3}\.\d{1,3}\.\d{1,3}\b"), "<private-ip>"),
    (re.compile(r"\b172\.(?:1[6-9]|2\d|3[01])\.\d{1,3}\.\d{1,3}\b"), "<private-ip>"),
    (re.compile(r"\b100\.(?:6[4-9]|[7-9]\d|1[01]\d|12[0-7])\.\d{1,3}\.\d{1,3}\b"), "<tailnet-ip>"),
    (re.compile(r"\bfd7a:115c:a1e0:[0-9a-fA-F:]+"), "<tailnet-ip6>"),
    # Host and operator identifiers are appended from --identities at startup.
]

# Heuristic hints: reported to the hints file only.
HINTS = [
    ("hex64-near-key-word", re.compile(r"(?i)(?:priv|secret|mnemonic|seed|signing)[^\n]{0,40}\b(?:0x)?[0-9a-f]{64}\b")),
]

# Residual scan: things that should not survive. Reported, not auto-fixed.
RESIDUAL = [
    ("alchemy-url-with-key", re.compile(r"alchemy\.com/v2/(?!<REDACTED>)[A-Za-z0-9_-]{8,}")),
    ("tailnet", re.compile(r"\.ts\.net\b|\btail[0-9a-f]{6}\b")),
    ("private-ip", re.compile(r"\b(?:192\.168|10\.\d{1,3}|100\.(?:6[4-9]|[7-9]\d|1[01]\d|12[0-7]))\.\d{1,3}\.\d{1,3}\b")),
    ("vendor-key", re.compile(r"\bsk-[A-Za-z0-9_-]{20,}|\bgh[pousr]_[A-Za-z0-9]{30,}|\beyJ[A-Za-z0-9_-]{10,}\.eyJ")),
]

TEXT_LIMIT = 200 * 1024 * 1024


def load_secrets(path):
    """Return (regex matching any secret or None, list of secrets, set of 6-word seed windows)."""
    if not path:
        return None, [], set()
    out = set()
    with open(path, encoding="utf-8", errors="replace") as f:
        for line in f:
            s = line.rstrip("\n")
            if len(s) >= 8:
                out.add(s)
    # Longest first so a secret that contains another is replaced whole.
    secrets = sorted(out, key=len, reverse=True)
    windows = set()
    for s in secrets:
        w = s.split(" ")
        if len(w) >= 6 and all(x.isalpha() and x.islower() for x in w):
            for i in range(len(w) - 5):
                windows.add(tuple(w[i:i + 6]))
    rx = re.compile("|".join(re.escape(s) for s in secrets)) if secrets else None
    return rx, secrets, windows


def seed_window_hit(text, windows):
    """The seed's words in order, whatever separates them (JSON arrays, newlines, commas)."""
    if not windows:
        return False
    toks = re.findall(r"[a-z]+", text.lower())
    return any(tuple(toks[i:i + 6]) in windows for i in range(len(toks) - 5))


def load_identities(path):
    """Append operator rules to RULES and residual checks to RESIDUAL; return how many."""
    if not path:
        return 0
    n = 0
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.rstrip("\n")
            if not line.strip() or line.lstrip().startswith("#"):
                continue
            parts = line.split("\t")
            if len(parts) < 2:
                sys.exit(f"bad identities line (need regex TAB replacement): {n + 1}")
            flags = re.I if len(parts) > 2 and "i" in parts[2] else 0
            rx = re.compile(parts[0], flags)
            if parts[1] != "-":
                RULES.append((rx, parts[1]))
            RESIDUAL.append(("operator-id", rx))
            n += 1
    return n


def load_wordlist(path):
    if not path or not os.path.exists(path):
        return None
    with open(path, encoding="utf-8") as f:
        return {w.strip() for w in f if w.strip()}


def redact(text, secret_rx):
    if secret_rx is not None:
        text = secret_rx.sub("<REDACTED_SECRET>", text)
    for rx, rep in RULES:
        text = rx.sub(rep, text)
    return text


def is_sqlite(path):
    try:
        with open(path, "rb") as f:
            return f.read(16) == b"SQLite format 3\x00"
    except OSError:
        return False


def is_text(path):
    try:
        with open(path, "rb") as f:
            chunk = f.read(8192)
    except OSError:
        return False
    if b"\x00" in chunk:
        return False
    try:
        chunk.decode("utf-8")
        return True
    except UnicodeDecodeError as e:
        # A multibyte character cut at the chunk boundary is still text.
        return e.start >= len(chunk) - 4


def sanitize_sqlite(path, secret_rx):
    con = sqlite3.connect(path)
    con.text_factory = lambda b: b.decode("utf-8", errors="replace")
    changed = 0
    tables = [r[0] for r in con.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")]
    for t in tables:
        qt = '"' + t.replace('"', '""') + '"'
        cols = [r[1] for r in con.execute(f"PRAGMA table_info({qt})")]
        if not cols:
            continue
        try:
            rows = con.execute(f"SELECT rowid, * FROM {qt}").fetchall()
        except sqlite3.OperationalError:
            # WITHOUT ROWID tables or virtual tables: handled by the FTS rebuild below.
            continue
        for row in rows:
            rowid, vals = row[0], row[1:]
            for c, v in zip(cols, vals):
                if isinstance(v, str):
                    nv = redact(v, secret_rx)
                    if nv != v:
                        qc = '"' + c.replace('"', '""') + '"'
                        try:
                            con.execute(f"UPDATE {qt} SET {qc}=? WHERE rowid=?", (nv, rowid))
                            changed += 1
                        except sqlite3.DatabaseError:
                            pass
    # Rebuild FTS indexes so their shadow tables match the redacted content.
    for (name, sql) in con.execute("SELECT name, sql FROM sqlite_master WHERE type='table'").fetchall():
        if sql and "VIRTUAL TABLE" in sql.upper() and "FTS" in sql.upper():
            qn = '"' + name.replace('"', '""') + '"'
            try:
                con.execute(f"INSERT INTO {qn}({qn}) VALUES('rebuild')")
            except sqlite3.DatabaseError:
                pass
    con.commit()
    con.execute("PRAGMA journal_mode=DELETE")
    con.execute("VACUUM")
    con.close()
    return changed


def mnemonic_runs(text, words, min_len=12):
    toks = re.findall(r"[a-z]+", text)
    run = 0
    for t in toks:
        run = run + 1 if t in words else 0
        if run >= min_len:
            return True
    return False


def residual_scan_text(rel, text, secret_rx, windows, words, findings, hints):
    if secret_rx is not None and secret_rx.search(text):
        findings.append((rel, 0, "exact-secret"))
    if seed_window_hit(text, windows):
        findings.append((rel, 0, "seed-words"))
    for i, line in enumerate(text.splitlines(), 1):
        for name, rx in RESIDUAL:
            if rx.search(line):
                findings.append((rel, i, name))
        for name, rx in HINTS:
            if rx.search(line):
                hints.append((rel, i, name))
    if words and mnemonic_runs(text, words):
        hints.append((rel, 0, "bip39-word-run"))


def blob_has_secret(blob, secret_rx, windows):
    if secret_rx is None and not windows:
        return False
    text = blob.decode("utf-8", errors="ignore")
    return (secret_rx is not None and secret_rx.search(text) is not None) or seed_window_hit(text, windows)


def main():
    args = sys.argv[1:]
    if not args:
        print(__doc__)
        sys.exit(1)
    root = args[0]
    secrets_path = args[args.index("--secrets") + 1] if "--secrets" in args else None
    wordlist_path = args[args.index("--wordlist") + 1] if "--wordlist" in args else None
    hints_path = args[args.index("--hints") + 1] if "--hints" in args else None
    ident_path = args[args.index("--identities") + 1] if "--identities" in args else None
    check_only = "--check-only" in args
    n_ident = load_identities(ident_path)
    if not n_ident:
        print("warning: no --identities given; host/operator names are not redacted or checked")
    secret_rx, secrets, windows = load_secrets(secrets_path)
    words = load_wordlist(wordlist_path)

    stats = {"text": 0, "text_changed": 0, "sqlite": 0, "sqlite_cells": 0, "binary": 0, "removed": []}
    findings = []
    hints = []

    for dp, dns, fns in os.walk(root):
        dns[:] = [d for d in dns if d != ".git"]
        for fn in fns:
            p = os.path.join(dp, fn)
            rel = os.path.relpath(p, root)
            try:
                st = os.lstat(p)
            except FileNotFoundError:
                # A -wal/-shm file that SQLite folded back into its database.
                continue
            if stat.S_ISLNK(st.st_mode):
                if check_only:
                    findings.append((rel, 0, "symlink"))
                    continue
                os.unlink(p)
                stats["removed"].append(rel + " (symlink)")
                continue
            if not stat.S_ISREG(st.st_mode):
                # Sockets, FIFOs, device nodes: opening them blocks or fails.
                if check_only:
                    findings.append((rel, 0, "special-file"))
                    continue
                os.unlink(p)
                stats["removed"].append(rel + " (special file)")
                continue
            if is_sqlite(p):
                stats["sqlite"] += 1
                if not check_only:
                    stats["sqlite_cells"] += sanitize_sqlite(p, secret_rx)
                with open(p, "rb") as f:
                    blob = f.read()
                if blob_has_secret(blob, secret_rx, windows):
                    findings.append((rel, 0, "exact-secret-in-sqlite"))
                continue
            if is_text(p) and os.path.getsize(p) <= TEXT_LIMIT:
                stats["text"] += 1
                with open(p, encoding="utf-8", errors="surrogateescape") as f:
                    text = f.read()
                new = text if check_only else redact(text, secret_rx)
                if new != text:
                    stats["text_changed"] += 1
                    with open(p, "w", encoding="utf-8", errors="surrogateescape") as f:
                        f.write(new)
                residual_scan_text(rel, new, secret_rx, windows, words, findings, hints)
                continue
            stats["binary"] += 1
            with open(p, "rb") as f:
                blob = f.read()
            if any(s.encode() in blob for s in secrets) or blob_has_secret(blob, secret_rx, windows):
                if check_only:
                    findings.append((rel, 0, "exact-secret-in-binary"))
                    continue
                os.unlink(p)
                stats["removed"].append(rel + " (binary containing a secret)")

    print(f"text files: {stats['text']} (changed {stats['text_changed']})")
    print(f"sqlite files: {stats['sqlite']} (cells changed {stats['sqlite_cells']})")
    print(f"other binary files: {stats['binary']}")
    for r in stats["removed"]:
        print(f"removed: {r}")
    if hints_path:
        with open(hints_path, "w", encoding="utf-8") as f:
            for rel, line, name in sorted(set(hints)):
                f.write(f"{name}: {rel}" + (f":{line}" if line else "") + "\n")
        print(f"heuristic hints: {len(set(hints))} (written to {hints_path}; not counted as findings)")
    if findings:
        print(f"\nRESIDUAL FINDINGS ({len(findings)}): check these by hand before publishing")
        seen = set()
        for rel, line, name in findings:
            key = (rel, line, name)
            if key in seen:
                continue
            seen.add(key)
            print(f"  {name}: {rel}" + (f":{line}" if line else ""))
        sys.exit(2)
    print("\nresidual scan: clean")


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except BaseException as e:
        # Never let a crash look like "findings" (exit 2): the tree is half done.
        print(f"\nsanitize.py FAILED: {type(e).__name__}: {e}", file=sys.stderr)
        print("The tree is only partly redacted. Do not pack or publish it.", file=sys.stderr)
        sys.exit(1)
