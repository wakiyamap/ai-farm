import json, subprocess
def rpc(method, params):
    out = subprocess.run(['python3','tools/rpc.py','ethereum',method,json.dumps(params)],capture_output=True,text=True).stdout
    r = json.loads(out)
    if 'error' in r: return f'ERROR {r["error"]}'
    return r['result']
FROM, HEAD = 26418621, 26468872
t0 = '0x4bafc1b25a3e727ead9384f3708c85489bdad9585fb211bbae2f76cf68d97339'
for name, f in [
  ('Buyout7d', {'address':'0x9cCbb2F03184720Eef5f8fA768425AF06604Daf4','topics':[t0],'fromBlock':hex(FROM),'toBlock':hex(HEAD)}),
  ('auctionAll7d', {'address':'0x9cCbb2F03184720Eef5f8fA768425AF06604Daf4','fromBlock':hex(FROM),'toBlock':hex(HEAD)}),
  ('vaultAll7d', {'address':'0xb1cFF81b9305166ff1EFc49A129ad2AfCd7BCf19','fromBlock':hex(FROM),'toBlock':hex(HEAD)}),
]:
    logs = rpc('eth_getLogs',[f])
    print(name, len(logs) if isinstance(logs,list) else logs)
    if isinstance(logs,list) and logs:
        for l in logs[:5]: print('  ', int(l['blockNumber'],16), l['topics'][0][:20], l['transactionHash'])
# control: same query shape (address+topic0) on USDC Transfer
usdc_t0='0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef'
logs = rpc('eth_getLogs',[{'address':'0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48','topics':[usdc_t0],'fromBlock':hex(HEAD-500),'toBlock':hex(HEAD)}])
print('USDC Transfer control 500 blocks:', len(logs) if isinstance(logs,list) else logs)
# auction vault() getter
v = rpc('eth_call',[{'to':'0x9cCbb2F03184720Eef5f8fA768425AF06604Daf4','data':'0xfbfa77cf'},'latest'])
print('auction.vault():', v)
