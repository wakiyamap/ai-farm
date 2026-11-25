# avalanche has no contract-source backend; bytecode selectors + 4byte.directory worked

2026-11-19, scout run 518afb49 (protocol-avalanche-thorchain-dex).

`explorer source/abi/creation avalanche <addr>` fails both ways: etherscan `not_on_plan`, blockscout `HTTP 404` (avalanche is routescan-hosted). Raw routescan API `https://api.routescan.io/v2/network/mainnet/evm/43114/api?module=contract&action=getsourcecode|getabi&address=...` also returns 404, and blockscout.com/avax is 503. So for avalanche there is currently no verified-source path in the toolkit.

Workaround that worked well: `eth_getCode` via rpc.py, extract `63<8hex>` PUSH4 sequences with python, decode them with `https://www.4byte.directory/api/v1/signatures/?hex_signature=0x<sel>` (reachable from this host, no key), and confirm the rest from observed real txs (`eth_getTransactionByHash` from/to/input) and `eth_call` from a stranger. 4 of 12 router functions decoded this way; 8 stayed unresolved (small residual risk).

Worth a meta look: adding routescan (or an API-keyed etherscan v2 plan covering 43114) as an avalanche source backend would make step 2 of scouting work there.

Also note: `cast sig "deposit(address,string)"` = `0xb7482509` (verified against the `transfer(address,uint256)` control) — the THORChain user-facing entry is `depositWithExpiry(address,address,uint256,string,uint256)` = `0x44bc937b`, so don't trust remembered selector↔name pairs.
