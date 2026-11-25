"""UniswapX Fill census over the last ~1 day per farm chain (reactors from Uniswap/UniswapX README, main branch, fetched 2026-11-13)."""
import json, subprocess, collections, os, sys
T = '0x78ad7ec0e9f89e74012afa58738b6b661c024cb0fd185ee2f616c0a28924bd66'  # Fill(bytes32,address,address,uint256)
R = {
    'ethereum': (['0x00000011F84B9aa48e5f8aA8B9897600006289Be', '0x0000000015757c461808EA25Eb309638B62681cf', '0x6000da47483062A0D734Ba3dc7576Ce6A0B645C4'], 12.0, 10000),
    'arbitrum': (['0xB274d5F4b833b61B340b654d600A864fB604a87c'], 0.25, 10000),
    'base': (['0x000000001Ec5656dcdB24D90DFa42742738De729', '0x000000008a8330B5d1F43A62Bf4C673A49f27ba0'], 2.0, 10000),
    'optimism': (['0x000000000923439A92daE8930613568824108631'], 2.0, 10000),
    'bsc': (['0x00000000a55e50C71b70Db3C8B58749cd1E18eB2'], 0.45, 5000),
    'polygon': (['0x00000000bAB6E234db8AD638B6A6395b7c499Bc4'], 1.5, 10000),
    'avalanche': (['0x00000000862cCF095823fc7576Fa6C7e6b7385ef'], 0.96, 10000),
}
days = float(sys.argv[1]) if len(sys.argv) > 1 else 1.0
res = {}
for chain, (addrs, bt, page) in R.items():
    head = int(json.loads(subprocess.run(['python3', '/srv/farm/ws/tools/rpc.py', chain, 'eth_blockNumber', '[]', '--lane', 'research'], capture_output=True, text=True).stdout)['result'], 16)
    frm = head - int(days * 86400 / bt)
    f = f'/srv/farm/ws/scratch/uniswapx-2685-filter-{chain}.json'
    json.dump({"address": addrs, "topics": [T]}, open(f, 'w'))
    out = f'/srv/farm/ws/scratch/uniswapx-2685-logs-{chain}.json'; aud = f'/srv/farm/ws/scratch/uniswapx-2685-audit-{chain}.json'
    for p in (out, aud):
        if os.path.exists(p): os.remove(p)
    r = subprocess.run(['python3', '/srv/farm/ws/tools/relay-log-scan.py', '--chain', chain, '--filter', f, '--from-block', str(frm), '--to-block', str(head),
                        '--max-requests', '80', '--page-blocks', str(page), '--output', out, '--audit', aud], capture_output=True, text=True)
    if r.returncode != 0 or not os.path.exists(out):
        res[chain] = {"error": (r.stderr or r.stdout)[-300:]}; print(chain, res[chain], flush=True); continue
    logs = json.load(open(out))
    if isinstance(logs, dict): logs = logs.get('logs', logs.get('result', []))
    fil = collections.Counter('0x' + l['topics'][2][-40:] for l in logs)
    by_reactor = collections.Counter(l['address'].lower() for l in logs)
    txs = len(set(l['transactionHash'] for l in logs))
    res[chain] = {"from": frm, "to": head, "fills": len(logs), "txs": txs, "fillers": len(fil), "top": fil.most_common(4), "by_reactor": dict(by_reactor)}
    print(chain, json.dumps(res[chain]), flush=True)
json.dump(res, open('/srv/farm/ws/scratch/uniswapx-2685-census.json', 'w'), indent=1)
