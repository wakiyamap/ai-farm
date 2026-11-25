#!/usr/bin/env python3
"""Offline tests of bot-run (phase 11c). Usage: test-11c.py <path to bot-run>"""
import json
import os
import subprocess
import sys
import tempfile

BOT_RUN = os.path.abspath(sys.argv[1])
A = "0x514d99889ecb37a45ae345744c28bc26e76cf87c"
B = "0x00000000000000000000000000000000000000b2"
fails = 0


def run(state, env_extra=None, exit_code=0):
    """state: None = no file, str = raw file text, dict = json. Returns (rc, env lines, stderr)."""
    with tempfile.TemporaryDirectory() as d:
        os.mkdir(os.path.join(d, "state"))
        if state is not None:
            with open(os.path.join(d, "state", "executor.json"), "w", encoding="utf-8") as f:
                f.write(state if isinstance(state, str) else json.dumps(state))
        with open(os.path.join(d, "run.sh"), "w", encoding="utf-8") as f:
            f.write("#!/bin/sh\nenv | grep '^EXECUTOR_ADDR' | sort\necho BOT_MODE=$BOT_MODE\nexit %d\n" % exit_code)
        os.chmod(os.path.join(d, "run.sh"), 0o755)
        env = {"PATH": "/usr/bin:/bin", "BOT_MODE": "live"}
        env.update(env_extra or {})
        p = subprocess.run([sys.executable, "-I", "-B", BOT_RUN, d], env=env, capture_output=True, text=True, timeout=20)
        return p.returncode, p.stdout.split(), p.stderr


def check(name, ok, detail=""):
    global fails
    print(("PASS " if ok else "FAIL ") + name + ("" if ok else f"  [{detail}]"))
    fails += 0 if ok else 1


rec = {"address": A, "txHash": "0x" + "11" * 32, "nonce": 0}
rc, out, err = run({"ethereum": rec})
check("one chain: EXECUTOR_ADDR and EXECUTOR_ADDR_ETHEREUM are the recorded address",
      rc == 0 and out == [f"EXECUTOR_ADDR={A}", f"EXECUTOR_ADDR_ETHEREUM={A}", "BOT_MODE=live"], (rc, out, err))
rc, out, err = run(None)
check("no executor.json: run.sh starts, nothing set, nothing on stderr", rc == 0 and out == ["BOT_MODE=live"] and err == "", (rc, out, err))
rc, out, err = run({"ethereum": rec, "base": dict(rec, nonce=0)})
check("two chains, same address: EXECUTOR_ADDR is set",
      out == [f"EXECUTOR_ADDR={A}", f"EXECUTOR_ADDR_BASE={A}", f"EXECUTOR_ADDR_ETHEREUM={A}", "BOT_MODE=live"], (rc, out, err))
rc, out, err = run({"ethereum": rec, "base": dict(rec, address=B)})
check("two chains, different addresses: only the per-chain names, with a line on stderr",
      out == [f"EXECUTOR_ADDR_BASE={B}", f"EXECUTOR_ADDR_ETHEREUM={A}", "BOT_MODE=live"] and "differs" in err, (rc, out, err))
rc, out, err = run("{not json")
check("broken file: run.sh starts, nothing set, stderr says so", rc == 0 and out == ["BOT_MODE=live"] and "cannot read" in err, (rc, out, err))
rc, out, err = run({"ethereum": {"address": "0x1234"}, "base": "x"})
check("bad address: nothing set, stderr says so", rc == 0 and out == ["BOT_MODE=live"] and err.count("no valid address") == 2, (rc, out, err))
rc, out, err = run({"ethereum": rec}, {"EXECUTOR_ADDR": B, "EXECUTOR_ADDR_BASE": B})
check("values already in the environment are replaced by the file",
      out == [f"EXECUTOR_ADDR={A}", f"EXECUTOR_ADDR_ETHEREUM={A}", "BOT_MODE=live"], (rc, out, err))
rc, out, err = run(None, {"EXECUTOR_ADDR": B})
check("no file: an inherited EXECUTOR_ADDR is removed", out == ["BOT_MODE=live"], (rc, out, err))
rc, out, err = run({"ethereum": rec}, exit_code=7)
check("the exit code of run.sh is the exit code of the unit", rc == 7, (rc, out, err))
print("ALL PASS" if not fails else f"{fails} FAILED")
sys.exit(1 if fails else 0)
