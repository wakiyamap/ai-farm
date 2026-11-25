trial: Peapods pod bond / debond round trips on Arbitrum. Measures the farm's win rate against three incumbent executors by sending; one of the routes has an incumbent that is minutes to hours late.

## Mechanism

A Peapods pod (pTKN) is minted from its underlying by anyone with `bond(token, amount, minOut)` and burnt back with `debond(amount, [], [])`. Pods trade in Uniswap V2 / Camelot pairs against PEAS, another pod or a paired vault token. When a pod's pair price drifts from the price of its underlying (most often because PEAS moves on the Uniswap V3 PEAS/WETH pool 0x23d17764..., 1 pct), a round trip pays, all in one transaction through the executor:

1. Flash-borrow 0.002-0.02 WETH from the Balancer V2 Vault (fee 0).
2. Swap into the underlying, `bond` it and sell the pod through its pair (or buy the pod in its pair and `debond`).
3. Unwind to WETH, repay the loan; revert `NoProfit` unless the WETH balance grew by `minProfit`; unwrap the gain and pay it to the bot wallet as native ETH.

Routes, each copied from an incumbent take (`scratch/flashcensus/routes_full.py`, `trace-*.json`; tokens checked with `token0()` / `token1()` / `asset()` / `symbol()`):

| route | path | copied from |
|---|---|---|
| `parb` | WETH -> PEAS, bond pPEAS, deposit pfpPEAS-30, UNI-V2 pair -> pARB, debond -> ARB -> WETH | 0x9934b3b1 tx 0x0aae3583... |
| `parb_rev` | WETH -> ARB, bond pARB, pair -> pfpPEAS-30, redeem -> pPEAS, debond -> PEAS -> WETH | 0x9934b3b1 tx 0x916afab0... |
| `appeasusdc` | WETH -> PEAS, bond apPEASUSDC, Camelot pair -> USDC -> WETH | 0xda77151b tx 0x50e15fbe... |
| `apohm` | WETH -> PEAS, bond apPEAS, Camelot pair -> apOHM, debond -> OHM, Camelot WETH/OHM -> WETH | 0x429e114b tx 0x9d07ce01... |
| `apump` | WETH -> OHM (Camelot), bond apUMP, Camelot pair -> PEAS -> WETH | 0x9934b3b1 tx 0x0d378940... |
| `apump_rev` | WETH -> PEAS, Camelot pair -> apUMP, debond -> OHM -> WETH | 0x9934b3b1 tx 0xd378c353... |
| `ppeas_usdc_rev` | WETH -> USDC, deposit pfUSDC-6, UNI-V2 pair -> pPEAS, debond -> PEAS -> WETH | 0xda77151b tx 0xad8aa03c... |
| `appmax` | WETH -> PEAS, bond apPmax, Camelot pair -> apOHM, Camelot pair -> USDC -> WETH | 0xda77151b tx 0xba5c3d13... |

The incumbents chain two of these legs in one transaction now and then; the bot takes each leg on its own. Found by a census of Balancer / Aave flash-loan recipients (wiki `methods/flash-recipient-census.md`).

## Competition, last 7 days (blocks 523,126,000-525,545,222, `scratch/trial-peapods-arb-arbitrum/census7d.json`)

418 takes by three executors, each driven by one EOA: 0x9934b3b1 (EOA 0xe6ec466b) 196, 0xda77151b (EOA 0xaba3b0cf) 203, 0x429e114b (EOA 0x57ba1e40) 19. Bursty: 304 in the last 24 h, 9-47 per day before. Nobody else flash-borrows for these routes.

Blocks to take (each sampled take's exact call replayed with `eth_call` at earlier blocks, `scratch/flashcensus/windows.py`, 0.25 s blocks; the control 2,000 blocks earlier reverts for 38 of 40):

| executor | takes sampled | takeable 4 blocks (1 s) before | 12 blocks (3 s) | 40 blocks (10 s) | 400 blocks (100 s) | mean gain WETH | mean gas ETH |
|---|---|---|---|---|---|---|---|
| 0x9934b3b1 | 20 | 20 | 8 | 2 | - | 0.00035 | 0.000016 |
| 0xda77151b | 20 | 20 | 13 | 6 | - | 0.00042 | 0.000018 |
| 0x429e114b | 13 | 13 | 13 | 13 | 5 | 0.0032 | 0.000024 |

So the incumbents react in seconds, not in the block: about half of the two fast executors' takes stand 3 s or longer. On `apohm` the incumbent is far slower: its take 0x25390d74... (block 525,429,591, +0.0374 WETH) was the first trade on the pair since block 525,344,093, and the route showed a gain of 0.004-0.046 WETH at every sampled block in between, about 5.9 h (`series-525390726.json`, `series-525400000.json`, `pairswaps-0x04d30065-*.json`).

Priority fee level: the two fast executors set 0.021-0.023 gwei maxPriorityFeePerGas, the slow one 0; Arbitrum orders first come first served, so the bot bids 1 wei. Takes sit at transaction index 1-7.

## How it sends

`check()` runs on every Swap of the PEAS/WETH pool (feed `/logs/arbitrum`, address 0x23d17764f41aea93fdbb5beffa83571f0bf3f8b2, topic0 0xc42079f9...; at most one check per 5 s; on `gap`, 429 or 503 the timer re-reads state) and on a 60 s timer:

1. One `eth_call` of the executor's `probe()`: it tries all eight routes at 0.004 WETH, reverts every trial and returns the gains. Zero means the round trip does not pay.
2. For a route with a gain: latest base fee, sweep 0.002 / 0.004 / 0.006 / 0.01 / 0.02 WETH with `run()` calls, take the best.
3. Gas limit = `eth_estimateGas` x 1.20 + 600,000 (a pod transfer may also sell the pod's pending fees: on the fork a take used 0.905m gas where the relay estimated 0.605m); refused above 3.2m. `maxFeePerGas` = base fee x 1.05 + 1 wei, refused above 0.1 gwei.
4. cap = gas limit x maxFeePerGas. Send only if the simulated gain is above the cap, with `minProfit = cap + 1`, after simulating that exact call at the signed gas limit. The cap in USD is taken at 4,000 USD/ETH and refused at 0.90 USD; typical cap 3e13-5e13 wei (0.05-0.10 USD).

A lost attempt costs gas only (fork: 0.0001096 ETH at 0.1 gwei; about 0.00002 ETH at the live 0.02 gwei base fee).

## Fork proof

`python3 scratch/trial-peapods-arb-arbitrum/proof.py <parent block> <result file>` (leases and releases the Arbitrum fork, a few minutes). Re-run 2026-11-19 with the executor that clears leftovers (`_clear()`: after the profit check every step token still held goes to the owner, `Leftover(token)` revert otherwise). Reset 525,390,726 (`proof-fix-525390726.json`): `probe()` answers for the owner and reverts for a stranger; non-owner `run` revert `0xb9ac678a...f4f2` (NotOwner); guard revert `0x3c9917a4...cb5b` (NoProfit); successes with the owner's native delta net of gas: `appeasusdc` `0x8d6b372f...11a2` +0.000171474 ETH, `apohm` `0x08f7d9f4...d8c9` +0.009191829 ETH, `apump` `0x44948d1f...8964` +0.002906110 ETH, `ppeas_usdc_rev` `0x232a00c2...f291` +0.000859795 ETH; the repeated calls revert. After each success the script reads the executor's native balance, its 14 route-token balances and its allowances to the 6 bond / deposit targets and the vault: all zero (the 1 wei of OHM from `apump` is in the owner wallet). The other four routes do not pay at that block. Reset 525,372,868 (`proof-fix-525372868.json`): `parb` `0x4529bdc0...a1b4` +0.000150286 ETH net, plus `appeasusdc` and `apohm` again. Reset 525,387,186 (`proof-fix-525387186.json`): `parb_rev` `0xae15c02c...dcf0`, gross +0.000075982 ETH but -0.000016234 ETH net at the fork's 0.1 gwei gas price (the bot sends only when the gain is above the gas cap), plus `appeasusdc` and `apohm`; executor clean after each. `apump_rev` has a simulated gain only (probe), `appmax` has none yet; both use step kinds the other routes prove. `selftest.py <block>` checks the bot's two hand ABI encodings against `cast calldata` and replays the bot's own `check()` at a past block with the new runtime (`selftest-525390726.jsonl`).

## Reads

Timer 1,440 x 26 CU = 37,440 CU/day; feed-triggered checks at about 300 pool swaps/day x 26 CU = 7,800 CU/day; a sweep is about 200 CU. The code stops at 93,000 relay CU/day (0.05 USD at 0.53 USD per million CU). The feed filter's own CU is metered by the feed. No per-block polling.

## Logs and closing

`logs/bot.jsonl`: `check`, `opportunity` (sweep, gas estimate, limit, cap), `opportunity_skip`, `simulate_revert`, `paper_sim`, `send`, `send_result` (won / lost, gas used, the winner's block and tx: the last PEAS/WETH pool swap up to our block), `signer_reject`, `feed_error`, `read_budget`. After 7 days live or when the gas budget is spent: count sends, wins and net ETH, write an `attempts` row and set lead 295 `measured` or `blocked_infra`. If `apohm` keeps showing minute-long windows with gains above 10 USD, it is worth a non-trial bot of its own.
