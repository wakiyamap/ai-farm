import subprocess, json

def rpc(method, params):
    r = subprocess.run(["python3","/srv/farm/ws/tools/rpc.py","arbitrum",method,json.dumps(params)],
                       capture_output=True, text=True, timeout=90)
    if r.returncode != 0:
        return ("ERR", (r.stdout + r.stderr).strip()[:300])
    try: return ("OK", json.loads(r.stdout).get("result"))
    except Exception: return ("ERR", r.stdout[:300])

# receipt of one withdraw tx: gasUsed, effective gas price
st, rc = rpc("eth_getTransactionReceipt", ["0x9e3e88fd038fd2e8e83f981af93a029cce712cf8352abbb85a0648c747b3cfd5"])
if st=="OK":
    gu = int(rc["gasUsed"],16); gp = int(rc["effectiveGasPrice"],16)
    print("withdraw gasUsed:", gu, "gasPrice gwei:", gp/1e9, "arb cost ETH:", gu*gp/1e18)

# TheoVault 0xc138 - rule out newer-gen
for a in ["0xc138D7D5C2b62aE9D44a393cC7D1097425CAeF60"]:
    st, code = rpc("eth_getCode", [a,"latest"])
    print(a, "code_len:", (len(code)-2)//2 if code else 0)
    st, res = rpc("eth_call", [{"to":a,"data":"0x95d89b41"},"latest"])
    print(" symbol:", (res or "?")[:200] if st=="OK" else st)
    st, res = rpc("eth_call", [{"to":a,"data":"0xad7a672f"},"latest"])  # totalBalance
    print(" totalBalance:", st, res)

# balances decode
for a, name, dec in [("0x4fE17dEFc597cC3bD6fBe16135d8Ac42D421907e","TETH42161/WETH",18),
                     ("0xF37Fe9396Bb95f7823A29090c939847f1817bC8a","TUSDC42161/USDC",6),
                     ("0x3ca8F12D7B376E9Ef338d1C432CA1b51DD319009","TUSDCH42161/USDC",6),
                     ("0x54602E5cBa09e01EeE9B2050F1F4f0Dc902CeE34","maweETH_Theo/weETH",18)]:
    st, res = rpc("eth_call", [{"to":a,"data":"0xad7a672f"},"latest"])
    if st=="OK" and res:
        v = int(res,16)/10**dec
        print(name, f"totalBalance: {v:,.4f}")
