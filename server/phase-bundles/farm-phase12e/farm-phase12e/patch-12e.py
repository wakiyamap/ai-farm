#!/usr/bin/env python3
"""Phase 12e text patches.

  patch-12e.py check <run-role> <farm.nft>            every old text occurs exactly once
  patch-12e.py apply <run-role> <farm.nft> <outdir>   write patched copies into <outdir>
  patch-12e.py tools <TOOLS.md> <out>                 add the explorer row (and note WebFetch) to a
                                                      copy of TOOLS.md; prints what it did

run-role: every claude-harness role may run `explorer ...`; the researcher (researcher-claude)
  may use the built-in WebFetch tool (human decision 2026-11-15; it was refused under
  --permission-mode dontAsk because it was not on the list).
farm.nft: the earner may reach 127.0.0.1:29484 (farm-explorer). The bots may not.
TOOLS.md is meta's file and changes often, so it is not held to a sha256: the row is inserted
  after the `| web |` row if that row exists exactly once, and nothing is done otherwise.
"""
import sys

RUN_ROLE = [
    ("""Bash(ledger *),Bash(websearch *),Bash(curl *),""",
     """Bash(ledger *),Bash(websearch *),Bash(explorer *),Bash(curl *),"""),
    ("""      echo "$common,Bash(date*),Bash(python3 *),Bash(jq *),Edit($ws/tools/**),Edit($ws/inbox/**),Edit(//srv/farm/prompts/roles/TOOLS.md)" ;;
""",
     """      # WebFetch (12e): docs pages that curl gets as an empty JavaScript shell; allowed for this role only
      echo "$common,WebFetch,Bash(date*),Bash(python3 *),Bash(jq *),Edit($ws/tools/**),Edit($ws/inbox/**),Edit(//srv/farm/prompts/roles/TOOLS.md)" ;;
"""),
]

NFT = [
    ("""# 9001-9009 (fork nodes), 29483 (farm-search, earner only). 9013""",
     """# 9001-9009 (fork nodes), 29483 (farm-search, earner only), 29484 (farm-explorer, earner only). 9013"""),
    ("""        meta skuid earner fib daddr type local tcp dport != { 53, 8000, 8003, 8545, 8546, 9001-9009, 29483 } reject with tcp reset
""",
     """        meta skuid earner fib daddr type local tcp dport != { 53, 8000, 8003, 8545, 8546, 9001-9009, 29483, 29484 } reject with tcp reset
"""),
]

EXPLORER_ROW = ("| explorer | Etherscan lookups for an address you already know: verified source, ABI, creation tx, "
                "tx history. A local service holds the API key. No search by name. `explorer chains` shows which "
                "chains the key covers; for the others use that chain's own explorer or Routescan | "
                "`explorer source <chain> <addr> [--out DIR]` / `explorer abi\\|creation\\|txs <chain> <addr>` | all |\n")
WEB_OLD = 'Fetch: harness built-in, but refused in "don\'t ask" sessions (researcher 11-15): then `curl -s`'
WEB_NEW = 'Fetch: harness built-in (WebFetch: researcher-claude only, since 12e; refused for the other claude roles): otherwise `curl -s`'


def patched(path, pairs, check_only=False):
    text = open(path, encoding="utf-8").read()
    for i, (old, new) in enumerate(pairs, 1):
        n = text.count(old)
        if n != 1:
            sys.exit(f"{path}: patch {i} matches {n} times (expected 1); nothing was changed")
        if not check_only:
            text = text.replace(old, new)
    return text


def tools(path, out):
    text = open(path, encoding="utf-8").read()
    did = []
    if "| explorer |" in text:
        did.append("explorer row: already there")
    else:
        rows = [ln for ln in text.splitlines(keepends=True) if ln.startswith("| web |")]
        if len(rows) == 1 and rows[0].endswith("\n"):
            text = text.replace(rows[0], rows[0] + EXPLORER_ROW)
            did.append("explorer row: added after the web row")
        else:
            did.append(f"explorer row: NOT added (found {len(rows)} `| web |` rows); meta adds it from the note")
    if text.count(WEB_OLD) == 1:
        text = text.replace(WEB_OLD, WEB_NEW)
        did.append("web row: WebFetch wording updated")
    elif WEB_NEW not in text:
        did.append("web row: wording not found, left as it is; meta updates it from the note")
    with open(out, "w", encoding="utf-8") as f:
        f.write(text)
    for d in did:
        print("  " + d)


def main():
    a = sys.argv
    if len(a) == 4 and a[1] == "tools":
        return tools(a[2], a[3])
    if len(a) < 4 or a[1] not in ("check", "apply"):
        sys.exit(__doc__)
    if a[1] == "check":
        patched(a[2], RUN_ROLE, True)
        patched(a[3], NFT, True)
        print(f"  run-role: {len(RUN_ROLE)} patches match, farm.nft: {len(NFT)} patches match")
        return
    for path, pairs, name in ((a[2], RUN_ROLE, "run-role"), (a[3], NFT, "farm.nft")):
        with open(f"{a[4]}/{name}", "w", encoding="utf-8") as f:
            f.write(patched(path, pairs))
    print(f"  patched copies written to {a[4]}")


if __name__ == "__main__":
    main()
