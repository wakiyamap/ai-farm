trial — Revert Lend V3Vault liquidation on Arbitrum One.

The public V3Vault at `0x74e6afef5705beb126c6d3bf46f8fad8f3e07825`
holds USDC debt against Uniswap v3 NFTs. A liquidator pays USDC, receives
token0 and USDC from the NFT, and can sell token0 to USDC. This bot covers
WETH/USDC and ARB/USDC positions. The whole action uses a Balancer flash loan,
with an owner-only executor that repays the flash and returns any surplus USDC
to the bot wallet. The executor reverts if the surplus is below `minProfit`.

## Seven-day competition

Ledger `revert_lend.liquidate`, blocks 522990116–524327778, contains 19
Liquidate events in 7 days from 6 takers: `0x5ac9bc14376bf2727c6211960cf3cec1e2f295bd`
(6), `0x09779ec1c7e2904e188138d6be7d36d56adf9ccb` (5),
`0x98313d1a6ddba7b197db5112f7e07108e65fd3a7` (3),
`0x1eaf2060ca863556f9c2773c750574c831fcc22c` (3),
`0x83db41be0f4d52cfb9f611a30c66f176bb4fc84b` (1), and
`0x5b94d444dfba48780524a1f0cd116f8a57bfefc2` (1).
Ten sampled takeable-to-taken windows: 0, 0, 0, 0, 0, 0, 1, 6, at least
32, at least 32 Arbitrum blocks; median zero. Winner priority fee median
0.008 gwei, range 0–0.018 gwei (`leads:57`, `attempts:1491`). The bot bids
at most 25% of its simulated gross as priority fee. It aims for at least
one of the roughly nine WETH/USDC or ARB/USDC events seen this week; live
attempts will measure the win rate.

## Proof and access

At historical parent block 524327777, a fresh address calling
`liquidate((uint256,uint256,uint256,address,bytes,uint256))` for token 5751116
reached an ERC-20 allowance error, after eligibility checks. The same-shaped
`loanInfo` getter returned liquidationCost 7.760970 USDC. Raw requests and
responses are in `scratch/revert-trial-{getter,stranger}-{request,response}.json`.
Winner trace `scratch/revert-trial-fe6-trace.json` shows flash USDC, vault
liquidation and an ARB/USDC swap. `fork replay` reset successfully but timed
out waiting for the incumbent transaction receipt; direct fork proofs follow.

Run `scratch/trial-revert-lend-arbitrum/proof.py` for ARB/USDC and
`proof-weth.py` for WETH/USDC. Each leases and resets the Arbitrum fork,
deploys the artifact, funds the owner, proves `NoProfit` revert, and proves
positive owner USDC delta. ARB route: +0.165843 USDC, 761255 gas, zero
executor USDC/ARB. WETH route: +0.211765 USDC, 647014 gas, zero executor
USDC/WETH. The respective owner payout hashes are
`0xa95ab80328e163560aadaa4a873daccef3aa6ab22d2406b5572dc80299eeaacc`
and `0xbae799f558578f3f59ee262663a451d68d216f1bcfc8eb6477e0c1168ee49922`.
Calling the already-liquidated ARB position again reverted `NotLiquidatable()`
(`0x154ed9d1a3cbb7e970ee77821300958ef1a4752f1d2989c0809fa836774ae24c`),
with no owner USDC change.
The paper code override was also called against parent block 524327777 through
the relay: `eth_call` returned 165843 USDC micro units and the same override
returned `eth_estimateGas` 955148. This checks the actual paper simulation path.

## Running and cost

The timer scans active loans every 30 seconds through Multicall and adds
confirmed Borrow/Add token IDs every 900 seconds. The 7-day seed scan
`scratch/trial-revert-lend-arbitrum/borrow-audit7d.json` covered blocks
522378000–524881083 completely: 332 logs, 256 IDs, of which 89 still
had debt at head. Inactive IDs are pruned and reappear on a later Borrow/Add.
The expected read cost after pruning is under 70,000 Alchemy CU/day,
approximately $0.037/day at $0.53/M CU; code caps relay reads at 80,000
CU/day. No feed subscription or block-by-block poll is used.

Before sending, the bot checks the NFT token pair and pool from the deployed
position manager and Uniswap factory, simulates the executor on current
state, and estimates gas. A send requires gross USDC greater than the
signed gas cap, capped at $1 per attempt. `maxFeePerGas` is capped at 0.1
gwei and priority bid at 25% of gross. Each send logs result, gas used,
winner block and block difference. The bot watches confirmed state only.
