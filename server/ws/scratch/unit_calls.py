import json, subprocess
def rpc(method, params):
    out = subprocess.run(['python3','tools/rpc.py','ethereum',method,json.dumps(params)],capture_output=True,text=True).stdout
    r = json.loads(out)
    if 'error' in r: return f'ERROR {r["error"]}'
    return r['result']
def call(to, data):
    return rpc('eth_call',[{'to':to,'data':data},'latest'])
# totalSupply of USDP
print('USDP totalSupply:', call('0x1456688345527bE1f37E9e627DA0837D6f08C925','0x18160ddd'))
print('CDPRegistry getCdpsCount:', call('0x1a5Ff58BC3246Eb233fEA20D32b79B5F01eC650c','0xbce092c4'))
print('Vault usdp():', call('0xb1cFF81b9305166ff1EFc49A129ad2AfCd7BCf19','0x74e6076c'))
