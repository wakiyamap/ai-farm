#!/usr/bin/env python3
"""Offline tests for phase 15b: gate-ctl send_deploy() with a fake chain. Nothing is sent anywhere.

  test-15b.py <gate-ctl> <run-role> [--old]

--old: run against the installed (unpatched) files and only report how many cases pass.
"""
import importlib.machinery
import importlib.util
import os
import sys
import tempfile
import time
import types

OLD = "--old" in sys.argv
GATE, RUN = sys.argv[1], sys.argv[2]
time.sleep = lambda s: None                     # send_deploy waits 3 s between tries


def load_gate(tmp):
    sys.path[:0] = ["/opt/farm/pylib", "/opt/farm/lib"]
    try:
        import farmkeys  # noqa: F401
        import farmchains  # noqa: F401
    except ImportError:                          # off the server: minimal stand-ins
        fk = types.ModuleType("farmkeys")
        fk.sign_eip1559 = lambda priv, tx: b"\x02signed"
        sys.modules["farmkeys"] = fk
        fc = types.ModuleType("farmchains")
        for n in ("CHAIN_IDS", "ETH_USD_FEED"):
            setattr(fc, n, {"optimism": 10})
        fc.CORE = ()
        for n in ("usdc_scale", "price_ok", "native", "max_tx_gas", "feed_chain", "nitro",
                  "transfer_gas_budget", "usdc_gas_budget"):
            setattr(fc, n, lambda *a, **k: None)
        sys.modules["farmchains"] = fc
    loader = importlib.machinery.SourceFileLoader("gatectl15b", GATE)
    m = importlib.util.module_from_spec(importlib.util.spec_from_loader(loader.name, loader))
    loader.exec_module(m)
    m.LOG = os.path.join(tmp, "gate.log")
    return m


class FakeRpc:
    def __init__(self, balances, send_errors):
        self.balances, self.send_errors, self.sent = list(balances), list(send_errors), []

    def call(self, chain, method, params, lane="live"):
        if method == "eth_getBalance":
            b = self.balances.pop(0) if len(self.balances) > 1 else self.balances[0]
            return hex(b)
        if method == "eth_sendRawTransaction":
            self.sent.append(params[0])
            if self.send_errors:
                e = self.send_errors.pop(0)
                if e:
                    raise RuntimeError(e)
            return "0xdeadbeef"
        raise AssertionError(method)


RESULTS = []


def case(name):
    def wrap(fn):
        RESULTS.append((name, fn))
        return fn
    return wrap


def gate(m, balances, send_errors=()):
    g = m.Gate.__new__(m.Gate)
    g.rpc = FakeRpc(balances, send_errors)
    return g


NEED = 10**15
RAW = b"\x02signed"
INSUFF = "insufficient funds for gas * price + value: have 0 want 2728981750626"


@case("wallet reads 0 twice, then funded: one send, the hash is returned")
def t_wait(m):
    g = gate(m, [0, 0, NEED])
    assert g.send_deploy("b1", "optimism", "0xabc", RAW, NEED) == "0xdeadbeef"
    assert len(g.rpc.sent) == 1


@case("node answers 'insufficient funds' twice although the wallet reads funded: the same bytes are resent")
def t_resend(m):
    g = gate(m, [NEED], [INSUFF, INSUFF, None])
    assert g.send_deploy("b1", "optimism", "0xabc", RAW, NEED) == "0xdeadbeef"
    assert g.rpc.sent == ["0x" + RAW.hex()] * 3


@case("any other send error is raised at once, without a retry")
def t_other(m):
    g = gate(m, [NEED], ["nonce too low"])
    try:
        g.send_deploy("b1", "optimism", "0xabc", RAW, NEED)
    except RuntimeError as exc:
        assert "nonce too low" in str(exc)
    else:
        raise AssertionError("no error")
    assert len(g.rpc.sent) == 1


@case("never funded: gives up after DEPLOY_SEND_TRIES, nothing sent, exit 2, deploy_executor_not_sent logged")
def t_giveup(m):
    g = gate(m, [0])
    try:
        g.send_deploy("b1", "optimism", "0xabc", RAW, NEED)
    except SystemExit as exc:
        assert exc.code == 2
    else:
        raise AssertionError("did not give up")
    assert g.rpc.sent == []
    assert "deploy_executor_not_sent" in open(m.LOG).read()


@case("deploy_executor sends only through send_deploy")
def t_wired(m):
    src = open(GATE, encoding="utf-8").read()
    body = src.split("    def deploy_executor(", 1)[1].split("\n    def ", 1)[0]
    assert "self.send_deploy(bot_id, chain, frm, raw, int(gas * 1.2) * max_fee)" in body
    assert "eth_sendRawTransaction" not in body


@case("run-role: the claude paper-reviewer may run `paper stop`")
def t_run(m):
    src = open(RUN, encoding="utf-8").read()
    assert "Bash(paper archive *),Bash(paper stop *),Edit(" in src


def main():
    with tempfile.TemporaryDirectory() as tmp:
        m = load_gate(tmp)
        ok = 0
        for name, fn in RESULTS:
            try:
                fn(m)
                ok += 1
                print(f"  ok    {name}")
            except Exception as exc:              # noqa: BLE001
                print(f"  FAIL  {name}: {exc!r}")
        print(f"{ok}/{len(RESULTS)} passed")
        if ok != len(RESULTS) and not OLD:
            sys.exit(1)


if __name__ == "__main__":
    main()
