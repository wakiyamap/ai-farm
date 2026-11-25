#!/usr/bin/env python3
"""Static check of a bot manifest's deployment fields (read-only, no RPC).

Catches the review blocker class that cost 5 review rounds on 11-07..11-09
(gearbox-v3, reserve-folio-dtf, moonwell-whale, morpho-watcher): an `executor`
value that is not exactly one existing file path, missing/garbled constructor
args, malformed addresses. It does NOT check that the args match the
constructor or that the contract is safe: that stays the reviewer's job.

  python3 tools/manifest-check.py bots/paper/<id>/manifest.yaml [...]
  python3 tools/manifest-check.py --all          # every bots/paper/*/manifest.yaml

Paths are resolved from the workspace root (/srv/farm/ws), as the gate does.
Exit 1 if any manifest has an ERROR.
"""
import glob
import json
import os
import re
import sys

import yaml

WS = "/srv/farm/ws"
REQUIRED = ["id", "chains", "strategy", "capital_usd", "allowed_contracts",
            "max_loss_per_tx_usd", "max_loss_guarantee", "executor", "fork_evidence"]
ADDR = re.compile(r"^0x[0-9a-fA-F]{40}$")
HEX = re.compile(r"^0x([0-9a-fA-F]{2})*$")


def constructor_inputs(artifact):
    try:
        abi = json.load(open(artifact)).get("abi", [])
    except Exception as e:  # noqa: BLE001
        return None, f"artifact is not a forge JSON artifact ({e.__class__.__name__})"
    for item in abi:
        if item.get("type") == "constructor":
            return item.get("inputs", []), None
    return [], None


NON_CODE_EXT = (".md", ".json", ".jsonl", ".yaml", ".yml", ".txt", ".log", ".lock")
SKIP_DIRS = {"node_modules", "state", "logs", ".git", "venv", ".venv", "__pycache__"}


# human note inbox/meta/2026-11-15-morpho-nextblock-pool-init.md: morpho-nextblock-ethereum sent
# setPoolAllowed only when its first WBTC opportunity arrived and spent that block on setup.
# Heuristic: the executor ABI has owner/setup-style state-changing functions and no bot code file
# logs `executor armed`. A reviewer check, not proof (wiki pitfalls/executor-setup-at-startup.md).
# Since decision 2026-11-15-executor-no-baked-targets any setup-style function warns (setup txs should
# not exist at all); the `armed` hint is appended when the line is missing.
SETUP_FN = re.compile(r"^(set|allow|approve|register|whitelist|enable|add)[A-Z_]", re.ASCII)


def setup_functions(artifact):
    try:
        abi = json.load(open(artifact)).get("abi", [])
    except Exception:  # noqa: BLE001
        return []
    return sorted({i.get("name", "") for i in abi if i.get("type") == "function"
                   and i.get("stateMutability") in ("nonpayable", "payable")
                   and SETUP_FN.match(i.get("name", ""))})


def code_mentions(bot_dir, needle):
    for root, dirs, files in os.walk(bot_dir):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        for f in files:
            if f.lower().endswith(NON_CODE_EXT):
                continue
            try:
                with open(os.path.join(root, f), errors="ignore") as fh:
                    if needle in fh.read(2_000_000).lower():
                        return True
            except OSError:
                continue
    return False


def reads_executor_addr(bot_dir):
    for root, dirs, files in os.walk(bot_dir):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        for f in files:
            if f.lower().endswith(NON_CODE_EXT):
                continue
            try:
                with open(os.path.join(root, f), errors="ignore") as fh:
                    text = fh.read(2_000_000)
            except OSError:
                continue
            if "EXECUTOR_ADDR" in text or "executor.json" in text:
                return True
    return False


# phase 11c (inbox/meta/2026-11-14-phase11c-executor-env.md): before 11-13T18:35Z nothing set
# EXECUTOR_ADDR, so `process.env.EXECUTOR_ADDR || '<fork address>'` ran live with the fork address
# and could never send (morpho-nextblock, gearbox-v3-watcher, franken). New bots must exit in
# live mode when the address is missing instead of falling back to a literal.
FORK_FALLBACK = re.compile(r"EXECUTOR_ADDR\w*\b.{0,40}?(\|\||\?\?|\bor\b|,)\s*['\"]0x[0-9a-fA-F]{40}['\"]")


def executor_fallbacks(bot_dir):
    hits = []
    for root, dirs, files in os.walk(bot_dir):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        for f in files:
            if f.lower().endswith(NON_CODE_EXT):
                continue
            p = os.path.join(root, f)
            try:
                with open(p, errors="ignore") as fh:
                    for i, line in enumerate(fh, 1):
                        if FORK_FALLBACK.search(line):
                            hits.append(f"{os.path.relpath(p, bot_dir)}:{i}")
            except OSError:
                continue
    return hits


# human 2026-11-17 (inbox/meta/2026-11-17-human-bold-live-patch.md item 3): my_address() returns
# {"ok": true, "address": "0x..."}; paper never runs the live branch (wiki pitfalls/signer-my-address-dict.md).
MY_ADDR_EXTRACT = re.compile(r"""\[\s*['"]address['"]\s*\]|\.get\(\s*['"]address['"]|\.address\b""")


def my_address_unextracted(bot_dir):
    hits = []
    for root, dirs, files in os.walk(bot_dir):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        for f in files:
            if f.lower().endswith(NON_CODE_EXT):
                continue
            p = os.path.join(root, f)
            try:
                with open(p, errors="ignore") as fh:
                    lines = fh.read(2_000_000).splitlines()
            except OSError:
                continue
            for i, line in enumerate(lines):
                if "my_address(" in line and "def my_address" not in line:
                    near = "\n".join(lines[i:i + 4])
                    if not MY_ADDR_EXTRACT.search(near):
                        hits.append(f"{os.path.relpath(p, bot_dir)}:{i + 1}")
    return hits


# phase 11c + human 2026-11-17 (inbox/meta/2026-11-17-human-review-noise.md item 1): after a promote the
# reviewer checks that the live start line shows the address from state/executor.json. Three trial bots
# (trial-aave4-base, trial-morpho-cbbtc-base, trial-revert-lend-arbitrum) logged `start` without it and
# each produced an inbox/human note. Heuristic: a quoted 'start'/'startup' log key with "executor" within
# the next 3 lines.
START_KEY = re.compile(r"""['"](start|startup)['"]""")


def start_logs_executor(bot_dir):
    seen_start = False
    for root, dirs, files in os.walk(bot_dir):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        for f in files:
            if f.lower().endswith(NON_CODE_EXT):
                continue
            try:
                with open(os.path.join(root, f), errors="ignore") as fh:
                    lines = fh.read(2_000_000).splitlines()
            except OSError:
                continue
            for i, line in enumerate(lines):
                if START_KEY.search(line) and ("log" in line.lower() or "print" in line.lower()):
                    seen_start = True
                    if "exec" in "\n".join(lines[i:i + 4]).lower():
                        return True
    return False if seen_start else None


# meta run 7f148f8e (2026-11-17): the live service does not put /opt/farm/lib on sys.path. Five trial
# bots promoted 11-16/17 do `import farmbot_signer` without it; trial-aave-arbitrum logged
# "No module named 'farmbot_signer'" 31 times live (bots/live/trial-aave-arbitrum/logs/bot.jsonl) and
# can never sign. Paper never imports the signer, so only a static check sees it
# (wiki pitfalls/signer-import-path.md).
def signer_import_unpathed(bot_dir):
    imports, pathed = [], False
    for root, dirs, files in os.walk(bot_dir):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        for f in files:
            if not f.endswith(".py"):
                continue
            p = os.path.join(root, f)
            try:
                text = open(p, errors="ignore").read(2_000_000)
            except OSError:
                continue
            if "/opt/farm/lib" in text:
                pathed = True
            for i, line in enumerate(text.splitlines(), 1):
                if re.search(r"^\s*(import farmbot_signer|from farmbot_signer import)", line):
                    imports.append(f"{os.path.relpath(p, bot_dir)}:{i}")
    return [] if pathed else imports


def check(path):
    errs, warns = [], []
    try:
        m = yaml.safe_load(open(path))
    except Exception as e:  # noqa: BLE001
        return [f"YAML does not parse: {e}"], warns
    if not isinstance(m, dict):
        return ["manifest is not a mapping"], warns
    for k in REQUIRED:
        if k == "allowed_contracts" and m.get(k) == []:
            if not m.get("executor"):
                errs.append("`allowed_contracts` is empty and there is no `executor`: the bot could call nothing")
            # else: correct for an executor bot since gate phase 10d (decisions/human/2026-11-11-executor-bots-funds.md)
        elif m.get(k) in (None, "", []):
            errs.append(f"missing field `{k}`")
    ex = m.get("executor")
    if isinstance(ex, str) and ex:
        if any(c in ex for c in "\n ") or not ex.endswith(".json"):
            errs.append("`executor` must be ONE plain path ending in .json, nothing else "
                        f"(got {ex[:90]!r}...); move prose to `executor_note` "
                        "(wiki pitfalls/manifest-path-scalar.md)")
        elif not os.path.isfile(os.path.join(WS, ex)):
            errs.append(f"`executor` file does not exist from {WS}: {ex}")
        else:
            inputs, err = constructor_inputs(os.path.join(WS, ex))
            if err:
                errs.append(f"`executor`: {err}")
            elif inputs:
                args = m.get("executor_args")
                # phase 9e (decisions/human/2026-11-10-gate-manifest-ledger.md): a 32-byte word
                # written `{bot}` is filled by the gate with the bot's address at promotion.
                bot_words = []
                if isinstance(args, str) and "{bot}" in args:
                    s = args.strip()
                    parts = (s[2:] if s.startswith("0x") else s).split("{bot}")
                    off = 0
                    for part in parts[:-1]:
                        off += len(part)
                        if off % 64:
                            errs.append("`{bot}` must replace one whole 32-byte word "
                                        f"(it starts at hex digit {off}, not a multiple of 64)")
                        bot_words.append(off // 64)
                        off += 64
                    args = "0x" + ("0" * 64).join(parts)
                if not isinstance(args, str) or not HEX.match(args.strip()):
                    errs.append(f"constructor takes {len(inputs)} arg(s) "
                                f"({', '.join(i.get('type', '?') for i in inputs)}) but "
                                "`executor_args` is missing or not 0x-hex (use `cast abi-encode`; "
                                "an owner arg that must be the bot wallet is better as owner = msg.sender, "
                                "since the gate deploys from the bot wallet)")
                else:
                    static = all(not (i.get("type", "").endswith("[]") or i.get("type") in ("bytes", "string")
                                      or i.get("type", "").startswith("tuple")) for i in inputs)
                    n = (len(args.strip()) - 2) // 64
                    if static and n != len(inputs):
                        errs.append(f"`executor_args` holds {n} words, constructor has {len(inputs)} static inputs")
                    # decisions/human/2026-11-15-executor-no-baked-targets.md item 1: targets (market,
                    # borrower, tokens, exit pool, route) are call arguments; constructor args are the
                    # owner `{bot}` only. Warning, not refusal (protocol singletons may be constants).
                    baked = ([f"{k} `{inp.get('name') or '?'}` ({inp.get('type', '?')})"
                              for k, inp in enumerate(inputs) if k not in bot_words] if static
                             else (["dynamic-type args"] if len(inputs) > len(bot_words) else []))
                    if baked:
                        warns.append("constructor args other than `{bot}`: " + ", ".join(baked[:6])
                                     + ": pass markets, borrowers, tokens, pools and routes as arguments of "
                                     "the execution call, not at deploy (decision 2026-11-15-executor-no-baked-"
                                     "targets; protocol singletons may be constants; wiki "
                                     "pitfalls/executor-no-baked-targets.md)")
                    if static:
                        for k, inp in enumerate(inputs):
                            if (inp.get("type") == "address" and "owner" in inp.get("name", "").lower()
                                    and k not in bot_words):
                                warns.append(f"constructor arg {k} `{inp.get('name')}` is a fixed address: if it "
                                             "must be the bot wallet, write that word as `{bot}` (gate phase 9e)")
            elif m.get("executor_args") not in (None, "", "0x"):
                warns.append("`executor_args` given but the constructor takes no inputs")
    if isinstance(ex, str) and ex.strip():
        # phase 10e (inbox/meta/2026-11-11-phase10e-gate-watchdog.md, rule 2 of
        # decisions/human/2026-11-11-executor-bots-funds.md): `gate promote` refuses an executor
        # bot none of whose code files mention EXECUTOR_ADDR or executor.json (.md, manifests and
        # JSON don't count). reserve-dutch-ethereum read EXEC_ADDRESS and restart-looped live 11-10.
        if not reads_executor_addr(os.path.dirname(os.path.abspath(path))):
            errs.append("bot has an `executor` but no code file mentions `EXECUTOR_ADDR` or "
                        "`executor.json`: live, read the executor address from env EXECUTOR_ADDR "
                        "(fallback state/executor.json); the gate refuses the promote otherwise")
        for hit in executor_fallbacks(os.path.dirname(os.path.abspath(path))):
            warns.append(f"{hit}: EXECUTOR_ADDR falls back to a hard-coded address; in live mode exit "
                         "with a clear message when it is unset instead (phase 11c; multi-chain bots read "
                         "EXECUTOR_ADDR_<CHAIN>)")
        if start_logs_executor(os.path.dirname(os.path.abspath(path))) is not True:
            warns.append("no `start` log line with the executor address found: log it at startup, e.g. "
                         "log('start', mode=MODE, executor=EXEC), so the reviewer can match it with "
                         "state/executor.json after the promote (phase 11c)")
        art = os.path.join(WS, ex.strip())
        fns = setup_functions(art) if os.path.isfile(art) else []
        if fns:
            # decision 2026-11-15-executor-no-baked-targets item 2: no post-deploy setup tx at all;
            # only if unavoidable: all at live startup + `executor armed` + a README reason.
            armed = code_mentions(os.path.dirname(os.path.abspath(path)), "executor armed")
            warns.append(f"executor has setup-style functions ({', '.join(fns[:5])}): pass what they set "
                         "(pools, approvals, targets) as execution-call arguments so no setup tx is needed "
                         "(decision 2026-11-15-executor-no-baked-targets item 2); if truly unavoidable, send "
                         "them at live startup, log `executor armed`, and give the reason in the README"
                         + ("" if armed else " (no code file logs `executor armed` yet)")
                         + " (wiki pitfalls/executor-no-baked-targets.md)")
    for a in m.get("allowed_contracts") or []:
        if isinstance(a, int) and not isinstance(a, bool):  # YAML 1.1 reads unquoted 0x.. as int: lossless
            if 0 < a < 2 ** 160:
                continue
            errs.append(f"allowed_contracts entry is not an address: {a}")
            continue
        s = str(a).split()[0] if a else ""
        if not ADDR.match(s):
            errs.append(f"allowed_contracts entry is not a 40-hex address: {str(a)[:60]!r}")
    cap = m.get("capital_usd")
    if isinstance(cap, (int, float)) and cap > 400:
        errs.append(f"capital_usd {cap} > 400")
    loss = m.get("max_loss_per_tx_usd")
    if isinstance(loss, (int, float)) and loss > 50:
        errs.append(f"max_loss_per_tx_usd {loss} > 50")
    # gate-ctl reads these numbers line by line as float(line.split(":", 1)[1]), not via YAML:
    # an inline comment or quotes crash `gate promote` (morpho-watcher 11-10 02:55Z, inbox/meta
    # 2026-11-10-morpho-capital-inline-comment.md). Mirror that parse here.
    try:
        raw_lines = open(path).read().splitlines()
    except OSError:
        raw_lines = []
    # (gate-ctl:348/350 parse the raw remainder; only principal_usdc strips '#', gate-ctl:213)
    for key, strip_comment in (("capital_usd", False), ("max_loss_per_tx_usd", False), ("principal_usdc", True)):
        for line in raw_lines:
            if line.startswith(key + ":"):
                val = line.split(":", 1)[1]
                try:
                    float(val.split("#")[0] if strip_comment else val)
                except ValueError:
                    errs.append(f"`{key}` line {line.strip()[:60]!r} is not a bare number: the gate parses "
                                "it with float() and crashes; drop inline comments/quotes (move prose to a "
                                "`*_note` field)")
    if "base" in (m.get("chains") or []) and not m.get("principal_usdc"):
        warns.append("Base bot without principal_usdc: principal must come from a flash loan")
    unpathed = signer_import_unpathed(os.path.dirname(os.path.abspath(path)))
    if unpathed:
        errs.append(f"{unpathed[0]}: `import farmbot_signer` but no code file adds /opt/farm/lib to sys.path; "
                    "the live service does not, so every live send fails with ModuleNotFoundError. Add "
                    "`sys.path.append(\"/opt/farm/lib\")` at the top (wiki pitfalls/signer-import-path.md)")
    for hit in my_address_unextracted(os.path.dirname(os.path.abspath(path))):
        warns.append(f"{hit}: farmbot_signer.my_address() returns a dict {{\"ok\", \"address\"}}; no "
                     "[\"address\"] / .get(\"address\") within 3 lines (wiki pitfalls/signer-my-address-dict.md)")
    check_send_route(m, errs, warns)
    check_holding(m, raw_lines, errs, warns)
    check_trial(m, warns)
    return errs, warns


# decision 2026-11-17-cheap-chain-trials.md section 1 (inbox/meta/2026-11-17-human-cheap-chain-trials.md
# item 3): a `trial:` bot is off ethereum, capital_usd <= 20, max_loss_per_tx_usd <= 1. Warnings only.
def check_trial(m, warns):
    strat = str(m.get("strategy") or "").strip()
    bot_id = str(m.get("id") or "")
    if not strat.lower().startswith("trial:"):
        if bot_id.startswith("trial-"):
            warns.append("id starts with `trial-` but `strategy` does not start with `trial:`")
        return
    chains = m.get("chains") or []
    if "ethereum" in chains:
        warns.append("trial bot lists ethereum in `chains`: cheap-chain trials are for non-ethereum chains only")
    cap = m.get("capital_usd")
    if not isinstance(cap, (int, float)) or cap > 20:
        warns.append(f"trial bot capital_usd {cap!r}: must be a number <= 20")
    loss = m.get("max_loss_per_tx_usd")
    if not isinstance(loss, (int, float)) or loss > 1:
        warns.append(f"trial bot max_loss_per_tx_usd {loss!r}: must be a number <= 1")
    if not bot_id.startswith("trial-"):
        warns.append(f"trial bot id {bot_id!r} should be `trial-<target>-<chain>`")


# phase 12c (inbox/meta/2026-11-15-phase12c-private-send-wiki-bm25.md item 1): the signer rejects
# every send of a bot whose send_route is neither public nor private; private only acts on ethereum.
def check_send_route(m, errs, warns):
    if "send_route" not in m:
        return
    route = m.get("send_route")
    if route not in ("public", "private"):
        errs.append(f"`send_route` is {route!r}: must be `public` or `private` (the signer rejects every "
                    "send otherwise; wiki infra/private-send.md)")
    elif route == "private" and "ethereum" not in (m.get("chains") or []):
        warns.append("`send_route: private` has an effect on ethereum only, and `chains` has no ethereum")


def bare_number(raw_lines, key):
    """Value of `key:` parsed as gate-ctl does (float of the raw remainder), or an error string."""
    for line in raw_lines:
        if line.startswith(key + ":"):
            try:
                return float(line.split(":", 1)[1]), None
            except ValueError:
                return None, (f"`{key}` line {line.strip()[:60]!r} is not a bare number: the gate parses it "
                              "with float(); drop inline comments/quotes")
    return None, f"`{key}` is not a top-level `{key}:` line"


def holding_bot_swept():
    """True once an archived bot with holding_usd has been stopped (real-funds stop-and-sweep ran)."""
    for p in glob.glob(f"{WS}/bots/archive/*/manifest.yaml"):
        try:
            if any(l.startswith("holding_usd:") for l in open(p)):
                return True
        except OSError:
            continue
    return False


def exitall_in_abi(artifact):
    try:
        abi = json.load(open(artifact)).get("abi", [])
    except Exception:  # noqa: BLE001
        return False
    return any(i.get("type") == "function" and i.get("name") == "exitAll" and not i.get("inputs")
               for i in abi)


# phase 12d (inbox/meta/2026-11-15-phase12d-holding-frame.md item 1; decision 2026-11-15-holding-frame):
# mirrors gate-ctl's promote refusals for a holding-frame bot.
def check_holding(m, raw_lines, errs, warns):
    if not m.get("holding_usd") and not m.get("holding_max_hours"):
        # earner.md template: "omit or 0". A bare `holding_usd:` / `holding_usd: 0` is a non-holding bot,
        # but the gate float()s the raw line, so a leftover template comment may still crash it.
        for key in ("holding_usd", "holding_max_hours"):
            if key in m and bare_number(raw_lines, key)[1]:
                warns.append(f"`{key}` is empty or commented: delete the line for a non-holding bot (the gate "
                             "parses it with float())")
        return
    if not m.get("holding_usd"):
        errs.append("`holding_max_hours` without `holding_usd`")
        return
    h, err = bare_number(raw_lines, "holding_usd")
    if err:
        errs.append(err)
    elif h > 100:
        errs.append(f"holding_usd {h:g} > 100 (per-bot cap; 200 over all live bots)")
    elif h <= 0:
        errs.append(f"holding_usd {h:g} must be > 0")
    else:
        p = m.get("principal_usdc")
        if not isinstance(p, (int, float)) or h > p:
            errs.append(f"holding_usd {h:g} > principal_usdc {p!r}: the held asset is bought with principal USDC")
        if h > 20 and not holding_bot_swept():
            warns.append(f"holding_usd {h:g} > 20 while no holding bot has been stopped and swept with real "
                         "funds yet: make the first one about 20 (phase 12d)")
    ex = m.get("executor")
    if not (isinstance(ex, str) and ex.strip()):
        errs.append("a holding_usd bot needs an `executor` (the asset stays in it; `gate stop` calls exitAll())")
    elif os.path.isfile(os.path.join(WS, ex.strip())) and not exitall_in_abi(os.path.join(WS, ex.strip())):
        errs.append("executor ABI has no `exitAll()` with zero inputs: the gate refuses the promote "
                    "(wiki methods/holding-frame.md)")
    hrs, err = bare_number(raw_lines, "holding_max_hours")
    if err:
        errs.append(err.replace("is not a top-level", "is missing: need a top-level"))
    elif not 0 < hrs <= 168:
        errs.append(f"holding_max_hours {hrs:g} must be > 0 and <= 168 (7 days)")


def main():
    paths = sys.argv[1:]
    if paths == ["--all"]:
        paths = sorted(glob.glob(f"{WS}/bots/paper/*/manifest.yaml"))
    if not paths or paths[0] in ("-h", "--help"):
        sys.exit(__doc__)
    bad = 0
    for p in paths:
        errs, warns = check(p)
        bad += bool(errs)
        print(f"{'FAIL' if errs else 'OK  '} {p}")
        for e in errs:
            print(f"  ERROR {e}")
        for w in warns:
            print(f"  warn  {w}")
    print(f"{len(paths) - bad}/{len(paths)} ok")
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
