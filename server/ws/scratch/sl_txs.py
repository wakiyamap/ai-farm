import json, subprocess, time, sys, collections

CUTOFF = "2026-11-14T16:22:00"  # 7d ago UTC
ADDRS = {
    "PriorityPool": "0xDdC796a66E8b83d0BcCD97dF33A6CcFBA8fd60eA",
    "SDLPool": "0x0B2eF910ad0b34bf575Eb09d37fd7DA6c148CA4d",
    "StratB_CommunityVCS": "0xac12290b097f6893322f5430627e472131fbc1b5",
    "StratA_VCS": "0x4852e48215a4785ee99b640caced5378cc39d2a4",
    "RebaseController": "0x1711e93eec78ba83d38c26f0ff284eb478bdbec4",
    "LINK_StakingPool": "0xb8b295df2cd735b15BE5Eb419517Aa626fc43cD5",
    "POL_StakingPool": "0x2ff4390dB61F282Ef4E6D4612c776b809a541753",
}
import urllib.request
def get(url):
    req = urllib.request.Request(url, headers={"User-Agent": "farm-scout/1.0 (research)"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)

for name, addr in ADDRS.items():
    tally = collections.Counter()
    senders = collections.Counter()
    pages = 0
    older = False
    cursor = ""
    while pages < 8 and not older:
        url = f"https://eth.blockscout.com/api/v2/addresses/{addr}/transactions?filter=to&page_size=50"
        if cursor: url += f"&page_token={cursor}"
        try:
            d = get(url)
        except Exception as e:
            print(f"{name}: fetch error {e}"); break
        pages += 1
        for tx in d.get("items", []):
            ts = tx.get("timestamp", "")
            if ts and ts < CUTOFF:
                older = True
                break
            meth = tx.get("method") or "transfer/?"
            f = tx.get("from", {}).get("hash", "?")
            tally[meth] += 1
            senders[(meth, f)] += 1
        cursor = d.get("next_page_params", {}).get("page_token", "") if d.get("next_page_params") else ""
        if not cursor: break
        time.sleep(0.3)
    print(f"== {name} ({pages} pages, truncated={older})")
    for m, c in tally.most_common(10):
        print(f"   {m}: {c}")
        for (mm, s), cc in senders.most_common(20):
            if mm == m:
                print(f"      by {s}: {cc}")
