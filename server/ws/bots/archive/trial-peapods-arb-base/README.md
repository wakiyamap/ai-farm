trial: Peapods pod bond / debond round trips on Base. Measures by sending how often the farm, looking every 30 s, still finds a gap the 0xc0ffee... executors left open.

## Mechanism

A Peapods pod (pTKN) is minted from its underlying by anyone with `bond(token, amount, minOut)` and burnt back with `debond(amount, [], [])`. On Base the pods pPWIF and pMIGGLES trade against PEAS in Aerodrome V2 volatile pairs. When PEAS moves on the Aerodrome Slipstream PEAS/USDC pool 0xb0a65b3a..., a pod's price in WETH terms drifts from its underlying's price on Uniswap V2, and a round trip pays, all in one transaction through the executor:

1. Flash-borrow 0.001-0.006 WETH from the Balancer V2 Vault (fee 0).
2. WETH -> USDC (Uniswap V3 0.01 pct) -> PEAS (Slipstream), buy the pod with PEAS in its pair, `debond`, sell the underlying for WETH (Uniswap V2). The `_rev` routes go the other way: buy the underlying, `bond`, sell the pod for PEAS, PEAS -> USDC -> WETH.
3. Repay the loan; revert `NoProfit` unless the WETH balance grew by `minProfit`; unwrap the gain and pay it to the bot wallet as native ETH.

Routes (`scratch/podbase/routes.py`, `trace-*.json`; tokens, factories and the pair fee checked with getters, `scratch/podbase/info.py`):

| route | path | copied from |
|---|---|---|
| `pwif` | WETH -> USDC (0xb4cb8009, Uniswap V3) -> PEAS (0xb0a65b3a, Slipstream) -> pPWIF (pair 0xb9537095, Aerodrome V2, 30 bps) -> debond PWIF -> WETH (0xd09fbc1a, Uniswap V2) | executor 0x2b38d0ee, tx 0x8a698d44... |
| `miggles` | same first two legs -> pMIGGLES (pair 0x9f759e19, Aerodrome V2, 30 bps) -> debond MIGGLES -> WETH (0x17a3ad8c, Uniswap V2) | executor 0x91cb0fcb, tx 0x492f3003... (it uses the PancakeV3 WETH/USDC pool 0x72ab388e; the bot uses the Uniswap V3 one) |
| `pwif_rev`, `miggles_rev` | the mirror of the two above with `bond` | no incumbent take traced; seen paying by the farm executor's `probe()` at block 59,285,647 |

## Competition, 12 h (blocks 59,186,000-59,402,248, `scratch/flashcensus/base.json`)

At least seven Balancer flash recipients run pod round trips touching PEAS, each driven by rotating vanity 0xc0ffee... EOAs and paying out to 0xc0ffeefeed8b9d27...: 0x2b38d0ee 19 takes, 0xff9de8ad 21, 0x91cb0fcb 16, 0x6a2fb93c 16, 0x3dc8b11f 14, 0x21c5ee97 6, 0x7bf53a7a 4 (96 in 12 h). Sampled gains 0.000007-0.00074 WETH per take against 0.000006-0.00009 ETH gas.

Blocks to take (18 takes of 0x2b38d0ee and 0x91cb0fcb; the farm executor's `probe()` at 0.002 WETH run as a code override at blocks before each take, `scratch/trial-peapods-arb-base/series.py`, `series-windows-2.json`, `series-windows-2-fine.json`; 0.2 s blocks):

| a gain was already visible | at the parent block | 1 block before it | 2 | 3 | 5 (1 s) | 15 (3 s) | 30 (6 s) | 50 (10 s) | 150 (30 s) |
|---|---|---|---|---|---|---|---|---|---|
| takes of 18 | 17 | 17 | 12 | 9 | 4 | 2 | 2 | 2 | 0 |

So the gaps open in bursts and the big ones (0.0001-0.0007 WETH) are gone within 1-3 blocks (0.2-0.6 s): the farm cannot win those. Two of 18 were small gaps (0.00004 WETH, about 0.07 USD, on both pods at once) that stood for 10 s or longer before 0x2b38d0ee took them. Those are what this trial sends at.

Priority fee level: the incumbents pay 0.0012-0.106 gwei maxPriorityFeePerGas, growing with the gain (0.015-0.018 gwei on the two small long-standing gaps); takes sit at transaction index 2-37. The bot bids at most 20 pct of its simulated gross, spread over its gas limit, between 0.0001 and 0.05 gwei (0.0045 gwei on a 0.00004 WETH gap).

## How it sends

`check()` runs on a 30 s timer. No feed: on 2026-11-19 Base already had its 8 feed log filters (the feed answers 429 `base already has 8 log filters`), and the PEAS/USDC pool Swap filter (about 2,800 logs/day) would cost about 100k feed CU/day, more than a trial may read. The feed code is kept behind `FEED_ENABLED = False` (feed `/logs/base`, address 0xb0a65b3a6f9da0e5eb057e0d5327deddbe17309e, topic0 0xc42079f9...). With a 30 s timer the bot sees a gap that stands t seconds with probability about t / 30, so it catches roughly half of the 10-30 s gaps and none of the sub-second ones. Each look:

1. One `eth_call` of the executor's `probe()`: it tries all four routes at 0.002 WETH, reverts every trial and returns the gains. Zero means the round trip does not pay.
2. For the best route with a gain: latest base fee, sweep 0.001 / 0.002 / 0.003 / 0.004 / 0.006 WETH with `run()` calls, take the best.
3. Gas limit = `eth_estimateGas` x 1.20 + 600,000 (a pod transfer may also sell the pod's pending fees), refused above 3.2m. Tip = min(0.05 gwei, 20 pct of gross / gas limit). `maxFeePerGas` = base fee x 1.05 + tip, refused above 0.1 gwei.
4. cap = gas limit x maxFeePerGas + 1e11 wei L1 data fee allowance (the incumbents' receipts show an L1 fee of about 1e9 wei). Send only if the simulated gain is above the cap, with `minProfit = cap + 1`, after simulating that exact call at the signed gas limit. The cap in USD is taken at 4,000 USD/ETH and refused at 0.90 USD; typical cap 1.8e13-6e13 wei (0.03-0.11 USD at 1,800 USD/ETH).
5. One send per look: the routes share the WETH/USDC and PEAS/USDC legs, so a second one in the same block would revert.

A lost attempt costs gas only: about 1m gas x (0.005 gwei base fee + tip), 5e12-3e13 wei (0.01-0.05 USD).

## The 1 USD per-send bound (fixed 2026-11-19 after review 57f67367)

Base charges the L1 data fee and the operator fee at inclusion; no signed field bounds them, so the cap in step 4 is an expected cost, not a bound. The enforceable worst case of one send is the wallet's native balance, so the wallet itself stays under 1 USD:

- `capital_usd: 0.75`, all native, no top-up (was 10). At 1,800 USD/ETH that is 4.2e14 wei: the executor deployment (about 1e13 wei) plus 7 sends at the largest cap seen (6e13 wei) or about 20-40 lost attempts at their real cost.
- Live, right before the signer call, `take()` reads ETH/USD (`slot0` of the Uniswap V3 WETH/USDC pool) and the wallet's balance, and `wallet_bound()` refuses the send while balance x price is 0.95 USD or more (`opportunity_skip`, `wallet_at_or_above_usd_bound`). Wins add about 0.07 USD each; ETH would have to rise 26.7 pct for the funded wallet to reach the line, and then the bot stops sending. A balance below the cap logs `wallet_below_gas_cap`: the trial is over.
- `scratch/trial-peapods-arb-base/guardtest.py` runs that decision with explicit balances (`guardtest-result.json`): 0.75 USD passes; 0.9501, 10 and 18 USD are refused. The live branch itself is not exercised in paper.

## Fork proof

`python3 scratch/trial-peapods-arb-base/proof.py [parent block] [result file]` (leases and releases the Base fork, a few minutes). At reset 59,389,298, the parent of incumbent take 0x8a698d44... (`proof-result-59389298.json`): deploy the artifact, fund the owner; `probe()` answers for the owner and reverts for a stranger; non-owner `run` revert `0x577352d8...c17c` (NotOwner); guard revert `0xee04e75b...ff43` (NoProfit, 1,041,164 gas); success `pwif` at 0.003 WETH `0x2a3aa5e1...5d13`, block 59,389,302, 846,052 gas, gross +0.000257658 ETH (the incumbent's take in that block made 0.000259333), owner +0.000173053 ETH net at the fork's 0.1 gwei gas price; success `miggles` at 0.001 WETH `0xdd027f75...476c`, gross +0.000040365 ETH (owner -0.000025005 ETH net at the fork's 0.1 gwei: at the live 0.005 gwei base fee the gas is about 0.000004 ETH, and the bot only sends when the gain is above its signed cap); the repeated calls revert; nothing is left in the executor. The `_rev` routes: see `proof-result-59285647.json` and the manifest. `selftest.py <block>` checks the bot's two hand ABI encodings against `cast calldata` and replays the bot's own `check()` at a past block: `paper_sim` success at 59,389,298 (gross 2.58e14 wei, cap 6.2e13) and at 59,291,400, 34 blocks before the incumbent took a small gap (gross 4.09e13 wei, cap 1.78e13, tip 0.0045 gwei); `nothing_to_take` at 59,380,000.

### Executor clears its leftovers (fixed 2026-11-19 after review b0031010)

The `_rev` proof ended with 1 wei PWIF and 1 wei MIGGLES in the executor (a `bond` leaves a wei of the underlying). `run()` now calls `_clear()` after the profit check: whatever is left of each step's token goes to the owner, so the executor holds no token after a success. Re-run with the new artifact (run cb0420ed, 14:48-14:51Z): `proof-fix-59285647.json` (`pwif_rev` +0.000718773 ETH net, `miggles_rev` +0.000083672 ETH net, 837k gas each, leftovers `{}`) and `proof-fix-59389298.json` (`pwif` +0.000172245 ETH net, 854,129 gas; `miggles` gross +0.000040365 ETH; leftovers `{}`). The fork transactions are byte-identical to the earlier ones, so their hashes repeat; the gas used is about 8-31k higher. `executor-runtime.hex` was re-taken from the fork deployment.

### Cleanup is strict (fixed 2026-11-19 after review 9566836b)

`_clearToken` no longer ignores failures: `run()` reverts `Leftover(token)` when a step token's balance cannot be read, when the dust transfer to the owner fails or returns false, or when a balance is still held after it; `_clear` also reverts when a bond / deposit allowance is not back to 0. A success therefore implies an empty executor. `proof.py` reads the executor's native balance, 7 token balances and 7 x 9 allowances right after each success (no skipped reads) and asserts zero: `proof-fix2-59285647.json` (`pwif_rev`, `miggles_rev`) and `proof-fix2-59389298.json` (`pwif`, `miggles`); hashes and deltas are in the manifest's `fork_evidence`. The revert paths, which no real route reaches, are unit-tested with mock tokens: `python3 scratch/trial-peapods-arb-base/leftover-test/run.py` (5 passed). Source sha256 `835323403217bcbf32c7c97d5c846aba854cea45edfbcdb726e09d3972d04245`.

## Reads

Timer 2,880 x 26 CU = 74,880 CU/day; a sweep is about 200 CU (a few to a few dozen a day). About 80,000 CU/day, 0.04 USD at 0.53 USD per million CU; the code stops at 93,000 relay CU/day. No feed CU, no per-block polling. (For reference, the pool had 1,407 swaps in 666 blocks in 12 h, `facts.json`.)

## Logs and closing

`logs/bot.jsonl`: `check`, `opportunity` (sweep, gas estimate, limit, tip, cap), `opportunity_skip`, `simulate_revert`, `paper_sim`, `send`, `send_result` (won / lost, gas used, L1 fee, the winner's block and tx: the last PEAS/USDC pool swap up to our block), `signer_reject`, `feed_error`, `read_budget`. After 7 days live or when the gas budget is spent: count sends, wins and net ETH, write an `attempts` row and set lead 296 `measured` or `blocked_infra` (how many blocks late, how much fee short).
