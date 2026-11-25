import json, subprocess
def rpc(method, params):
    out = subprocess.run(['python3','tools/rpc.py','ethereum',method,json.dumps(params)],capture_output=True,text=True).stdout
    r = json.loads(out)
    if 'error' in r: return f'ERROR {r["error"]}'
    return r['result']
FROM, HEAD = 26418621, 26468872
usdc_t0='0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef'
logs = rpc('eth_getLogs',[{'address':'0x1456688345527bE1f37E9e627DA0837D6f08C925','topics':[usdc_t0],'fromBlock':hex(FROM),'toBlock':hex(HEAD)}])
print('USDP Transfer 7d:', len(logs) if isinstance(logs,list) else logs)
if isinstance(logs,list):
    for l in logs[-10:]: print('  ', int(l['blockNumber'],16), l['transactionHash'])
# DUCK transfers 7d
logs = rpc('eth_getLogs',[{'address':'0x92E187a03B6CD19CB6AF293ba17F2745Fd2357D5','topics':[usdc_t0],'fromBlock':hex(FROM),'toBlock':hex(HEAD)}])
print('DUCK Transfer 7d:', len(logs) if isinstance(logs,list) else logs)
