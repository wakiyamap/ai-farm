#!/usr/bin/env python3
"""Phase 10f: exact-text patches for gate-ctl - an executor artifact kept inside the bot's own
paper directory, and a state/executor.json copied over from another bot.

  patch-10f.py check <gate-ctl>
  patch-10f.py apply <gate-ctl> <outdir>

Every old text must occur exactly once, or nothing is written. Safe to re-run (markers).
"""
import os
import sys

GATE = [
("promote: the executor artifact and its arguments are read before anything moves",
r'''        self.check_deploy_gas(bot_id, text, chains, bot_addr)    # before anything moves (10b, hyperevm)
''',
r'''        # an unreadable artifact or bad executor_args must refuse here, not after the bot has been
        # moved to live and funded (10f; 2026-11-10 reserve-dutch-ethereum-v2)
        self.executor_code(text, bot_addr)
        self.check_deploy_gas(bot_id, text, chains, bot_addr)    # before anything moves (10b, hyperevm)
''',
"not after the bot has been"),

("executor_code: an artifact under bots/paper/<id>/ is found in bots/live/<id>/ after the move",
r'''        try:
            with open(os.path.join(WS, art), encoding="utf-8") as f:
                artifact = json.load(f)
''',
r'''        path = os.path.join(WS, art)
        # an artifact kept inside the bot's own paper directory moves with the bot at promotion:
        # after `adopt` the same file is under bots/live/<id>/ (10f)
        moved = re.match(r"bots/paper/([^/]+)/(.+)$", art)
        if not os.path.exists(path) and moved and os.path.exists(f"{LIVE}/{moved.group(1)}/{moved.group(2)}"):
            path = f"{LIVE}/{moved.group(1)}/{moved.group(2)}"
        try:
            with open(path, encoding="utf-8") as f:
                artifact = json.load(f)
''',
"moved = re.match(r\"bots/paper/([^/]+)/(.+)$\", art)"),

("deploy: a state/executor.json that this bot's key did not produce does not count as an executor",
r'''        if os.path.exists(f"{LIVE}/{bot_id}/state/executor.json"):
            die(f"{bot_id} already has an executor (state/executor.json)")
''',
r'''        if self.executor_state_ok(bot_id):
            die(f"{bot_id} already has an executor (state/executor.json)")
''',
"if self.executor_state_ok(bot_id):\n            die("),

("deploy_executor: a stale state/executor.json is removed before the deployment is sent",
r'''        code = self.executor_code(manifest_text, frm)
        if code is None:
            return None
        out = {}
        for chain in chains:
            max_fee, tip = self.fees(chain)
''',
r'''        code = self.executor_code(manifest_text, frm)
        if code is None:
            return None
        ej = f"{LIVE}/{bot_id}/state/executor.json"
        if os.path.exists(ej) and not self.executor_state_ok(bot_id):
            # copied over with the bot's files (e.g. from an archived live bot): the address in it
            # belongs to another key. The signer would allow it and `deploy` would see "an executor".
            # Remove it before spending the deployment gas (10f).
            try:
                os.remove(ej)
            except OSError as exc:
                die(f"stale state/executor.json of {bot_id} cannot be removed ({exc}); remove {ej} as root, "
                    f"then run `gate-ctl deploy {bot_id}`")
            log(op="stale_executor_state_removed", bot=bot_id)
        out = {}
        for chain in chains:
            max_fee, tip = self.fees(chain)
''',
'log(op="stale_executor_state_removed", bot=bot_id)'),

("executor_state_ok(): was state/executor.json written for this bot's own key",
r'''    def check_deploy_gas(self, bot_id, manifest_text, chains, bot_addr):
''',
r'''    def executor_state_ok(self, bot_id):
        """True when state/executor.json exists and every address in it is the contract this bot's
        own key creates at the recorded nonce (keccak(rlp([bot, nonce]))) - i.e. the gate wrote it
        for this bot. A file copied in from another bot fails this (10f)."""
        try:
            with open(f"{LIVE}/{bot_id}/state/executor.json", encoding="utf-8") as f:
                st = json.load(f)
            frm = self.addr(f"bot:{bot_id}")
            import rlp as _rlp
            return bool(st) and all(
                v["address"].lower() == "0x" + farmkeys.keccak256(_rlp.encode([bytes.fromhex(frm[2:]), v["nonce"]]))[-20:].hex()
                for v in st.values())
        except (OSError, ValueError, KeyError, TypeError, AttributeError):
            return False

    def check_deploy_gas(self, bot_id, manifest_text, chains, bot_addr):
''',
"def executor_state_ok(self, bot_id):"),
]


def patch(text, hunks, name):
    for title, old, new, marker in hunks:
        if marker in text:
            print(f"  {name}: already applied: {title}")
            continue
        n = text.count(old)
        if n != 1:
            raise SystemExit(f"{name}: cannot apply '{title}': old text found {n} times (expected 1); "
                             "nothing was changed")
        text = text.replace(old, new)
        print(f"  {name}: applied: {title}")
    return text


def main(argv):
    if len(argv) == 2 and argv[0] == "check":
        out = None
    elif len(argv) == 3 and argv[0] == "apply":
        out = argv[2]
    else:
        sys.exit(__doc__)
    with open(argv[1], encoding="utf-8") as f:
        text = patch(f.read(), GATE, "gate-ctl")
    if out:
        with open(os.path.join(out, "gate-ctl"), "w", encoding="utf-8") as f:
            f.write(text)


if __name__ == "__main__":
    main(sys.argv[1:])
