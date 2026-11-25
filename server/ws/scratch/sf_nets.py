import json
d = json.load(open('/srv/farm/ws/scratch/superfluid-networks.json'))
for n in d:
    if n.get('isTestnet'):
        continue
    c = n.get('contractsV1', {})
    print(n['name'], n['chainId'], {k: c.get(k) for k in ['host', 'cfaV1', 'cfaV1Forwarder', 'gdaV1', 'toga', 'batchLiquidator']}, n.get('subgraphV1', {}))
