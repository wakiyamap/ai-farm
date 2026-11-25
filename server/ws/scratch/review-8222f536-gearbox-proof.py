#!/usr/bin/env python3
"""Gearbox V3 flash-loan executor fork proof v5 (earner run ec9955a8, 2026-11-07).

Rerun: python3 scratch/gearbox-v3/proof-flash5.py   (from the workspace root)

v5 = the v4 recipe (attempt 366) with the cushion leg DROPPED (lead 48 open detail
settled: withdrawCollateral from the EOA reverted in the v4 proof; premium-only was
already positive) and a same-tx premium sweep to a constructor-owner.

Leases the shared ethereum fork only for the run, releases it at the end.

At fork block 26287069 (reset; mainnet liquidation tx1
0x906b3d51233d9538bdcfbc583ca91fd0eda77102b8d85b1abb9d5f1941b8d847 mined at 26287070;
account 0x56631dcb... liquidatable, attempts 358):
  1. controls: facade.underlying() == WETH; isLiquidatable(account,10000)==1;
     cm.adapterToContract(wmooAdapter) == WMoo, routerAdapter/aethAdapter registered
     (measured registration, attempts 365).
  2. deploy GearboxFlashLiquidator5 --args [owner] (constructor takes the owner),
     fund the owner (native only; its WETH balance must be 0 at start).
  3. success: flashLiquidate(facade, account, BPT, wmooAdapter, routerAdapter,
     aethAdapter 0x5deb1929..., principal 4e18, minRateRAY 0x02a649c112686927b4
     (tx1 measured), minProfit 1e17): Morpho flash -> liquidateCreditAccount with the
     three tx1-layout adapter calls -> NoProfit guard -> Morpho pulls principal ->
     premium swept to owner. status 1, OWNER WETH delta >= minProfit, executor WETH
     balance ends exactly 0 (the sweep + pull-back invariant).
  4. revert case: same call on a healthy account reverts; balances unchanged.
Writes scratch/review-8222f536-gearbox-proof.json.
"""
import json
import subprocess
import urllib.request

FORK = "http://127.0.0.1:9013"
RESET_BLOCK = 26287069
LIQ_BLOCK = 26287070
TARGET = "0x56631dcb1ea548d2629e82e01375090ed1f81b7e"
FACADE = "0x4da50da058ad6cc96bb63edff55b534d2a2cbe92"
WMOO = "0x1a711a5bc48b5c1352c1882fa65dc14b5b9e829d"
BPT = "0x57c23c58b1d8c3292c15becf07c62c5c52457a42"
WRAP = "0x0bfc9d54fc184518a81162f8fb99c2eaca081202"
WMOO_ADAPTER = "0xb4adb364309ec7af0ec286d706b7cb6c3c46381d"      # tx1 calls[0] target
ROUTER_ADAPTER = "0x0214d10f4922c8407351c509150761e0bd487989"    # tx1 calls[1] target
AETH_ADAPTER = "0x5deb19295e463eee1457c009d3e9a3f84211868e"      # tx1 calls[2] target
MIN_RATE_RAY = 0x02a649c112686927b4                               # tx1 measured rate floor
WETH = "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2"
MORPHO = "0xbbbbbbbbbb9cc5e90e3b3af64bdaf62c37eeffcb"
OWNER = "0xc0ffee0000000000000000000000000000000001"
PRINCIPAL = 4 * 10**18
MIN_PROFIT = 10**17
ARTIFACT = "scratch/gearbox-v3/contracts/out/GearboxFlashLiquidator5.sol/GearboxFlashLiquidator5.json"
S_GETACCTS = "0x3b007fb9"    # compressor.getCreditAccounts(address,uint256,uint256)
S_ISLIQ = "0x8340e24d"       # creditManager.isLiquidatable(address,uint16)
S_BALOF = "0x70a08231"       # balanceOf(address)
COMPRESSOR = "0x81cb9eA2d59414Ab13ec0567EFB09767Ddbe897a"

_id = [0]

def rpc(method, params):
    _id[0] += 1
    body = json.dumps({"jsonrpc": "2.0", "id": _id[0], "method": method, "params": params}).encode()
    req = urllib.request.Request(FORK, data=body, headers={"content-type": "application/json"})
    return json.loads(urllib.request.urlopen(req, timeout=60).read())

def word(x):
    if isinstance(x, int):
        return format(x, "x").rjust(64, "0")
    return x[2:].lower().rjust(64, "0")

def call(to, data, what, frm=None):
    p = {"to": to, "data": data}
    if frm:
        p["from"] = frm
    r = rpc("eth_call", [p, "latest"])
    if "error" in r:
        raise RuntimeError(f"eth_call {what} on {to} reverted: {r['error'].get('message') if isinstance(r['error'],dict) else r['error']}")
    return r["result"]

def shell(args):
    p = subprocess.run([str(a) for a in args], capture_output=True, text=True)
    if p.returncode != 0:
        raise RuntimeError(f"{' '.join(str(a) for a in args)}:\n{p.stdout[-400:]}\n{p.stderr[-400:]}")
    return p.stdout

def send(tx):
    return json.loads(shell(["fork", "send", "ethereum-review", json.dumps(tx)]))

def addr_of(dep_output):
    toks = [w for w in dep_output.replace(",", " ").split() if w.lower().startswith("0x") and len(w) == 42]
    return toks[-1]

def encode_liquidate(sel, facade, account, bpt, wa, ra, aa, principal, rate, min_profit):
    return ("0x" + sel[2:] + word(facade) + word(account) + word(bpt) + word(wa) + word(ra)
            + word(aa) + word(principal) + word(rate) + word(min_profit))

def main():
    out = {}
    shell(["fork", "lease", "ethereum-review", "15", "gearbox-v5 reviewer proof"])
    try:
        sel_flash = shell(["/opt/foundry/bin/cast", "keccak",
                           "flashLiquidate(address,address,address,address,address,address,uint256,uint256,uint256)"]).strip()[:10]
        sel_c2a = shell(["/opt/foundry/bin/cast", "keccak", "contractToAdapter(address)"]).strip()[:10]
        sel_a2c = shell(["/opt/foundry/bin/cast", "keccak", "adapterToContract(address)"]).strip()[:10]
        ctor_args = shell(["/opt/foundry/bin/cast", "abi-encode", "constructor(address)", OWNER]).strip()
        shell(["fork", "reset", "ethereum-review", str(RESET_BLOCK)])
        shell(["fork", "fund", "ethereum-review", OWNER, "1"])
        out["fork_gen_after_reset"] = shell(["fork", "status", "ethereum-review"]).strip().splitlines()[-1]
        blk = int(rpc("eth_getBlockByNumber", ["latest", False])["result"]["number"], 16)
        out["fork_block_after_reset"] = blk

        cm = "0x" + call(FACADE, "0xc12c21c0", "facade.creditManager()")[-40:]
        und = "0x" + call(FACADE, "0x6f307dc3", "facade.underlying()")[-40:]
        out["credit_manager"], out["underlying"] = cm, und
        if und.lower() != WETH.lower():
            raise RuntimeError(f"facade.underlying() = {und}, expected WETH")

        # measured adapter registration (positive controls for the three hardcoded calls)
        wrap_adapter = "0x" + call(cm, sel_c2a + word(WRAP), "cm.contractToAdapter(WRAP)")[-40:]
        wmoo_target = "0x" + call(cm, sel_a2c + word(WMOO_ADAPTER), "cm.adapterToContract(wmooAdapter)")[-40:]
        router_target = "0x" + call(cm, sel_a2c + word(ROUTER_ADAPTER), "cm.adapterToContract(routerAdapter)")[-40:]
        aeth_target = "0x" + call(cm, sel_a2c + word(AETH_ADAPTER), "cm.adapterToContract(5deb)")[-40:]
        out["wrap_adapter"], out["wmoo_adapter_target"] = wrap_adapter, wmoo_target
        out["router_adapter_target"], out["aeth_adapter_target"] = router_target, aeth_target
        if int(wrap_adapter, 16) == 0:
            raise RuntimeError("cm.contractToAdapter(WRAP) == 0: the wrapper adapter is unregistered")
        if wmoo_target.lower() != WMOO.lower():
            raise RuntimeError(f"adapterToContract(wmooAdapter) = {wmoo_target}, expected WMoo {WMOO}")
        if int(router_target, 16) == 0 or int(aeth_target, 16) == 0:
            raise RuntimeError("adapterToContract(routerAdapter/5deb) == 0: adapter unregistered")

        dep = shell(["fork", "deploy", "ethereum-review", ARTIFACT, OWNER, "--args", ctor_args])
        exec_addr = addr_of(dep)
        out["executor"] = exec_addr
        # constructor ran: owner() immutable must return OWNER
        own = "0x" + call(exec_addr, "0x8da5cb5b", "executor.owner()")[-40:]
        out["executor_owner"] = own
        if own.lower() != OWNER.lower():
            raise RuntimeError(f"executor.owner() = {own}, expected {OWNER}")

        accounts = []
        for off in range(0, 60, 10):
            page = call(COMPRESSOR, S_GETACCTS + word(cm) + word(off) + word(10), "compressor.getCreditAccounts()")
            body = page[2:]
            n = int(body[:64], 16)
            accounts += ["0x" + body[64 + i * 64:128 + i * 64][-40:] for i in range(n)]
        out["cm_accounts_n"] = len(accounts)

        liq_t = int(call(cm, S_ISLIQ + word(TARGET) + word(10000), "isLiquidatable(target)"), 16)
        out["isLiquidatable_target"] = liq_t
        if liq_t != 1:
            raise RuntimeError(f"positive control failed: isLiquidatable(target)={liq_t}")

        balw = int(call(WMOO, S_BALOF + word(TARGET), "balanceOf(target) WMoo"), 16)
        out["target_bal_WMoo"] = balw
        if balw == 0:
            raise RuntimeError("positive control failed: target holds no WMoo")

        morpho_weth = int(call(WETH, S_BALOF + word(MORPHO), "balanceOf(morpho) WETH"), 16)
        out["morpho_weth"] = morpho_weth
        if morpho_weth < PRINCIPAL:
            raise RuntimeError(f"Morpho WETH liquidity {morpho_weth} < principal {PRINCIPAL}")

        # owner WETH balance must start at 0: the sweep delta IS the profit
        ow_bal_pre = int(call(WETH, S_BALOF + word(OWNER), "balanceOf(owner) WETH pre"), 16)
        if ow_bal_pre != 0:
            raise RuntimeError(f"owner WETH balance pre = {ow_bal_pre}, expected 0")

        healthy = None
        for a in accounts:
            if a.lower() == TARGET:
                continue
            r = rpc("eth_call", [{"to": cm, "data": S_ISLIQ + word(a) + word(10000)}, "latest"])
            if "error" not in r:
                if int(r["result"], 16) == 1:
                    continue
                healthy = a
                break
            data = r["error"].get("data") or "0x"
            if data.startswith("0x532e7bb6") or data.startswith("0x309d1501"):
                healthy = a
                break
        if healthy is None:
            raise RuntimeError("no non-liquidatable control account found on this CM")
        out["healthy_account"] = healthy

        # --- independent NO_PROFIT guard before consuming the liquidatable account
        data_guard = encode_liquidate(sel_flash, FACADE, TARGET, BPT, WMOO_ADAPTER,
                                      ROUTER_ADAPTER, AETH_ADAPTER, PRINCIPAL,
                                      MIN_RATE_RAY, 4 * 10**18)
        guard = send({"from": OWNER, "to": exec_addr, "data": data_guard, "gasLimit": "0x31975d"})
        out["guard_tx"] = guard["transactionHash"]
        out["guard_status"] = int(guard["status"], 16)
        if out["guard_status"] != 0:
            raise RuntimeError("NO_PROFIT guard unexpectedly passed")
        if int(call(WETH, S_BALOF + word(OWNER), "owner post-guard"), 16) != ow_bal_pre:
            raise RuntimeError("NO_PROFIT guard changed owner balance")
        if int(call(WETH, S_BALOF + word(exec_addr), "executor post-guard"), 16) != 0:
            raise RuntimeError("NO_PROFIT guard changed executor balance")

        # --- success: premium sweep to the owner, executor ends at 0 WETH
        data = encode_liquidate(sel_flash, FACADE, TARGET, BPT, WMOO_ADAPTER,
                                ROUTER_ADAPTER, AETH_ADAPTER, PRINCIPAL, MIN_RATE_RAY,
                                MIN_PROFIT)
        rcpt = send({"from": OWNER, "to": exec_addr, "data": data, "gasLimit": "0x31975d"})
        st = int(rcpt["status"], 16)
        out["liquidate_status"] = st
        out["fork_tx_success"] = rcpt["transactionHash"]
        out["fork_tx_success_gasUsed"] = int(rcpt["gasUsed"], 16)
        if st != 1:
            rv = (rcpt.get("revertReason") or "")[:120]
            out["revert"] = rv
            raise RuntimeError(f"success call reverted: {rv}")
        ow_bal_post = int(call(WETH, S_BALOF + word(OWNER), "balanceOf(owner) WETH post"), 16)
        out["owner_weth_delta"] = ow_bal_post - ow_bal_pre
        if ow_bal_post - ow_bal_pre < MIN_PROFIT:
            raise RuntimeError(f"sweep check failed: owner delta {ow_bal_post - ow_bal_pre} < {MIN_PROFIT}")
        out["net_profit_raw"] = ow_bal_post - ow_bal_pre
        exec_bal_after = int(call(WETH, S_BALOF + word(exec_addr), "balanceOf(executor) after"), 16)
        out["executor_weth_after"] = exec_bal_after
        if exec_bal_after != 0:
            raise RuntimeError(f"sweep invariant failed: executor ends at {exec_bal_after}, expected 0")

        # --- revert case on the healthy account
        data_h = encode_liquidate(sel_flash, FACADE, healthy, BPT, WMOO_ADAPTER,
                                  ROUTER_ADAPTER, AETH_ADAPTER, PRINCIPAL, MIN_RATE_RAY,
                                  1)
        rcpt2 = send({"from": OWNER, "to": exec_addr, "data": data_h, "gasLimit": "0x31975d"})
        st2 = int(rcpt2["status"], 16)
        out["fork_tx_revert"] = rcpt2["transactionHash"]
        out["fork_tx_revert_status"] = st2
        if st2 != 0:
            raise RuntimeError(f"revert case did not revert: status={st2}")
        ow_bal_after = int(call(WETH, S_BALOF + word(OWNER), "balanceOf(owner) after revert"), 16)
        exec_bal_revert = int(call(WETH, S_BALOF + word(exec_addr), "balanceOf(executor) after revert"), 16)
        out["revert_balance_unchanged"] = (ow_bal_after == ow_bal_post and exec_bal_revert == exec_bal_after)
        if ow_bal_after != ow_bal_post or exec_bal_revert != exec_bal_after:
            raise RuntimeError("reverted call changed balances")

        out["reset_block"] = RESET_BLOCK
        out["liq_block"] = LIQ_BLOCK
        out["ok"] = True
    finally:
        with open("scratch/review-8222f536-gearbox-proof.json", "w") as f:
            json.dump(out, f, indent=1)
        shell(["fork", "release", "ethereum-review"])
    print(json.dumps(out, indent=1))

if __name__ == "__main__":
    main()
