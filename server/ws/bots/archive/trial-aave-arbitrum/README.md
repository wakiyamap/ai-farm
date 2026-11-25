trial — Aave v3 same-asset liquidation on Arbitrum One.

The last seven days through 2026-11-16 20:15 UTC contained 28 same-asset
LiquidationCall events in 25 transactions from 9 takers (ledger `aave_v3.liquidation`).
Across all asset pairs: 331 events / 188 transactions / 27 takers
(`attempts:1458`). Same-asset winner 0x0dc76a8cdc8194e2ed4810e729cea63d4b864104
at block 524318519 took WETH collateral with 0.1013254 WETH nominal gross
(tx 0x00422627b85bd9c908fbe681b73f36014e05ffb581a7d563bf7fb47ddf0617f7).
The receipt used 709804 gas at 0.05 gwei effective. Another same-asset
native USDC winner at block 524180028 paid 11.020528 gwei effective during a
fee spike (tx 0x4f34892f0a17eb9e75f233dc5ceefd0fe1d348437465707cd0d954a0ec531c5e).
The seven-day all-pair census measured median priority fee paid $0.054 per
winner tx, 15/188 near zero, maximum $49.07 (`attempts:1458`). This bot caps
maxFeePerGas at 0.1 gwei and its priority bid at 25% of simulated gross.

Same-asset takers (events): 0x5ac9bc14376bf2727c6211960cf3cec1e2f295bd
(17), 0x63b701c73d0609ea5c3144ee8ae6362a9ed1563c (4), and one each from
0x0b15604214d795ba9410cc8bcacf959a8f47a63e,
0x0dc76a8cdc8194e2ed4810e729cea63d4b864104,
0x9355ec6d797b6c8b73de9b52fffdb3bfa6d05fdb,
0xb1054f96f1518f2f794cb99b4c009cd13b14aa48,
0xc78a8d450cb70f546363c467315fba2fe089c121,
0xd12810b19b596347a3afac206d3ca65d08594b3f and
0xda7484fc8f4e78aa5d47e03292355267ca4ac919.

## Competition window

`scratch/trial-arb-aave-parent.json` queried the parent-block Aave health factor
for all 28 same-asset events: 13 were healthy at B-1 (0 blocks to take),
3 crossed at B-1 (1 block), 2 opened 2-3 blocks earlier, 1 opened 4-7
blocks earlier, 2 opened 257-1023 blocks earlier and 7 were already
unhealthy at B-1024. The large
WETH case at B=524318519 was HF 1.00141878 at B-2, 0.99980004 at B-1,
and was taken at B: **1 block**. Block timestamps on B-2, B-1 and B are all
1794704600, so the ledger scout's measured ~0.335 seconds/block is the time
scale. The longer-open cases in `scratch/trial-arb-aave-window.json` are dust;
the profitable WETH case is a speed contest. Trial policy permits sending to
measure a real win rate. A position's stale activity is never treated as a
takeability window.

## Mechanism and guard

The bot gets candidates from the older Aave watcher seed (3170 known debtors)
and 29,863 confirmed Borrow/Withdraw logs over blocks 521688075-524849763
(`scratch/trial-aave-arbitrum/borrow-logs.json`, 32 bounded relay requests).
These add 4592 distinct users for a 7762-user startup set; subsequent confirmed
Borrow/Withdraw logs add new users. A pool LiquidationCall feed wakes a
near-health scan after cascades; a timer also checks the 200 nearest-health debtors every
60 seconds and the whole candidate set hourly. Only WETH/WETH and native
USDC/USDC are considered. `getUserConfiguration` confirms that the user
borrows and supplies that same asset. The executor flash-borrows 0.1 WETH or
300 USDC from Balancer, liquidates, repays the flash, reverts on insufficient
profit, and returns all profit to the bot wallet as ETH or USDC. It clears
the Pool allowance and leaves no balance. There is no setup transaction.

Fresh stranger `eth_call` of Pool.liquidationCall at block 524646263 with user
0x1e55d5c09beb9f97e55809e5a9a00f209fdf3671 reached `ERC20: transfer
amount exceeds allowance`, after Aave had accepted the HF<1 eligibility.
At head the same shape reverted `HealthFactorNotBelowThreshold` as expected.
`scratch/trial-aave-arbitrum/proof.py` reproduces a NoProfit revert and a
successful wallet payout, with zero executor leftovers, on the real historical
WETH case. Fork `replay` of 0xf878b53e... reset to its parent but the fork
could not obtain the re-sent tx receipt; this proof uses direct pool state.

## Read and send costs

Baseline relay: near scan 28,800 CU/day, full scan 18,720, discovery 8,640,
block numbers 1,440 = about 57,600 CU/day. Feed: ~47 matching logs/day at
35 CU plus idle maintenance ~5,760 CU/day = about 7,400 CU/day. Allowing
opportunity checks, total expected ~65,000 CU/day = $0.034/day at $0.53/M CU.
The bot caps relay reads at 75,000 CU/day, reserving 25,000 for feed and
variance under the 100,000 CU/day trial ceiling. An actual send's gas limit
comes from `eth_estimateGas` plus 25% headroom; `maxFeePerGas × gasLimit`
must be under $1 at the current Aave WETH/USD oracle price. The fork estimate
was 478643 gas, limit 598304, so 0.1 gwei would cost at most 0.0000598304 ETH
(~$0.109 at $1820.68/ETH). The bot also requires simulated gross greater
than the whole signed gas cap, and sets on-chain minProfit to 125% of it.

Live sends use the signer, one call to the gate-deployed executor. Each send
logs won/lost, gas used and the winner block when observable. A signer
rejection ends that attempt. The bot never watches pending transactions.
