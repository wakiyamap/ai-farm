import json
import subprocess

vaults = [
    '0xd4c10158e9b7832e0dd7c121ce9eae0856e7f6d9',
    '0x37f14bcd72076c4f7ddd7fd29dcc519fabc935f7',
    '0xac72f4ec02edf994c18b208b99c2ffbe505418c7',
    '0x2e17509724dbe94d9cb03c3ecdab6a49bc78af94',
    '0x817e30fd53b2fe30f87a4dc450811029961babf9',
    '0xc8d05ac9be57779b0f46ac12313567f7359a8495',
    '0xd6f361320e61d0a912acf10c53e2d5c43aa79dc2',
    '0xea5b9650f6c47d112bb008132a86388b594eb849',
    '0x4eba099f97ffed8de47a14f835820815f141ea08',
    '0xd498bf281262e04b0dc8a1c6d14877cee46aaaae',
]

def logs(addresses, start, end):
    filt = {'address': addresses, 'fromBlock': hex(start), 'toBlock': hex(end)}
    p = subprocess.run(['python3', '/srv/farm/ws/tools/rpc.py', 'ethereum',
                        'eth_getLogs', json.dumps([filt])],
                       capture_output=True, text=True)
    if p.returncode:
        return {'error': p.stdout[:400], 'stderr': p.stderr[:200]}
    result = json.loads(p.stdout)['result']
    return {'count': len(result), 'sample': result[:2]}

if __name__ == '__main__':
    for start in range(26430648, 26480891, 8000):
        end = min(start + 7999, 26480890)
        print('vaults', start, end, json.dumps(logs(vaults, start, end)))
    print('control', json.dumps(logs('0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48', 26430648, 26430648)))
