import json, os, urllib.request
base = os.environ["RPC_RELAY_URL"].rstrip("/")
T = {
 "ethereum": ["0x6B175474E89094C44Da98b954EedeAC495271d0F","0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48","0xdAC17F958D2ee523a2206206994597C13D831ec7","0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2","0x2260FAC5E5542a773Aa44fBCfeDf7C193bc2C599","0x5f98805A4E8be255a32880FDeC7F6728C6568bA0"],
 "base": ["0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913"],
 "arbitrum": ["0xaf88d065e77c8cC2239327C5EDb3A432268e5831","0x82aF49447D8a07e3bd95BD0d56f35241523fBab1","0xFd086bC7CD5C481DCC9C85ebE478A1C0b69FCbb9"],
 "optimism": ["0x0b2C639c533813f4Aa9D7837CAf62653d097Ff85"],
 "polygon": ["0x3c499c542cEF5E3811e1192ce70d8cC03d5c3359"],
 "avalanche": ["0xB97EF9Ef8734C71904D8002F8b6Bc66Dd9c48a6E"],
 "bsc": ["0x8AC76a51cc950d9822D68b83fE1Ad97B32Cd580d"],
 "elysium": ["0xb47c4C8F73F009CC0C0d3f92B388d13E293F0B65"],
}
for ch, addrs in T.items():
    for a in addrs:
        body = json.dumps({"jsonrpc":"2.0","id":1,"method":"eth_call","params":[{"to":a,"data":"0x95d89b41"},"latest"]}).encode()
        r = json.loads(urllib.request.urlopen(urllib.request.Request(f"{base}/{ch}?lane=research", data=body, headers={"content-type":"application/json"}), timeout=30).read())
        res = r.get("result", "")
        sym = ""
        try:
            if res and len(res) >= 194:
                n = int(res[66:130], 16); sym = bytes.fromhex(res[130:130+2*n]).decode()
            elif res and len(res) == 66:
                sym = bytes.fromhex(res[2:]).rstrip(b"\0").decode()
        except Exception as e:
            sym = f"?{e}"
        print(ch, a, sym or r)
