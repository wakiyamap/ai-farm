"""arbitrum/optimism stopped bots: normal tx list via explorer -> sends by bot (excl. deploy+sweep), failed count, native in/out."""
import json, subprocess
INTER = "0x915bd260dcb166f86a499d5fdb3775b5bec70427"
addrs = json.load(open("/srv/farm/ws/scratch/meta-bad6-addrs.json"))
gate = json.load(open("/srv/farm/ws/scratch/meta-bad6-gate.json"))
for b, (addr, chain) in addrs.items():
    if chain not in ("arbitrum", "optimism"):
        continue
    r = subprocess.run(["explorer", "txs", chain, addr], capture_output=True, text=True)
    fund = swept = 0
    sends = 0
    other_to = {}
    for line in r.stdout.splitlines():
        p = line.split()
        if len(p) < 8 or p[3] == "via":
            continue
        frm, to, val, inp = p[3].lower(), p[5].lower(), int(p[7]), (p[8] if len(p) > 8 else "")
        if frm == INTER and to == addr.lower():
            fund += val
        elif frm == addr.lower() and to == INTER:
            swept += val
        elif frm == addr.lower():
            if inp.startswith("0x60"):
                continue  # executor deploy
            sends += 1
            other_to[to] = other_to.get(to, 0) + 1
    print(json.dumps({"bot": b, "chain": chain, "funded_native": fund / 1e18, "swept_native": swept / 1e18,
                      "bot_sends_excl_deploy_sweep": sends, "to": other_to, "stderr": r.stderr.strip()[:120]}))
