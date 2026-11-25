trial

# trial-ryeth-arb-arbitrum

Sommelier's Real Yield ETH cellar on Arbitrum (`0xC47bB288178Ea40bF520a91826a3DEE9e0DbFA4C`, verified
`CellarWithOracleWithBalancerFlashLoansWithMultiAssetDepositWithNativeSupport`) lets anyone deposit rETH or wstETH with
`multiAssetDeposit(asset, amount, receiver)` at its price router's value (deposit fee 0 for both, read from
`alternativeAssetData`) and lets anyone `redeem` shares for WETH in the same transaction (no share lock). When rETH is
cheaper in the Uniswap V3 rETH/WETH 0.05 pct pool than the cellar's price, one transaction does:

    Morpho Blue flash WETH -> SwapRouter02 WETH -> rETH -> cellar.multiAssetDeposit -> cellar.redeem -> WETH -> repay

and the executor reverts unless its WETH grew by `minProfit`. The gain is unwrapped and paid to the bot wallet as ETH.

## Competition, last 7 days (blocks 523,717,125-526,117,125; `scratch/rf1c5/ryeth_takes.py`)

| block | tx | sender -> target | flash | size (WETH) | kept (WETH) | gas (ETH) | tx index |
|---|---|---|---|---|---|---|---|
| 525,988,179 | 0x4efdd4df342a... | 0x953c1ba7 -> itself | none (own funds) | 1.0 | not measured (probe at -1 block: 0.00285 available) | 0.000102 | 2 |
| 525,996,087 | 0x0f08d461ed6f... | 0x953c1ba7 -> itself | none | 2.0 | same (0.00382 available) | 0.000083 | 6 |
| 525,998,837 | 0xe7af5a330c8a... | 0xab36085a -> new contract | Balancer V2 | 2.0 | 0.000543 | 0.000051 | 1 |
| 526,077,494 | 0xc932a7594a8e... | 0xf62b10b2 -> 0x0b2d9635 | Balancer V2 | 6.0 | 0.003050 | 0.000099 | 1 |

Three operators, four takes, all within 9 hours on 2026-11-20/21, none before in the 7 days. Priority fee: none
(Arbitrum orders by arrival). Blocks to take: a gain stood for at least 14,400 blocks (1 h) before every take and for
57,600 blocks (4 h) before three of them (`scratch/trial-ryeth-arb-arbitrum/series-windows.json`, the
bot's own probe at -1, -4, -12, -40, -240, -1,200, -2,400, -14,400, -57,600 blocks). A gain of 0.00091 WETH stood at
block 525,000,000 (three days before the first take) and 0.00095 WETH stands at head 526,117,993 (03:10 UTC 11-21).
This is not a speed contest; the incumbents arrive hours late and leave most of the day uncovered.

## What the bot does

- Every 120 s: one `probe()` eth_call with 12 candidates (rETH and wstETH routes x 0.5 / 1 / 2 / 4 / 8 / 16 WETH).
- Best gain >= 0.00002 WETH: read the base fee, `eth_estimateGas` the take (Arbitrum: never a constant), gas limit =
  estimate x 1.2, cap = gas limit x (base fee x 1.25). Send only when gross > cap, cap < 0.95 USD at 4,000 USD per ETH,
  and the exact call with `minProfit = cap` simulates above cap.
- Paper: logs `paper_sim`. Live: sends through the signer, logs `send_result` with won / lost, gas used, the tx index and
  the winner's block (newest `MultiAssetDeposit` on the cellar).
- Sizes: the pool's depth caps the useful size near 2-4 WETH; larger candidates return 0.
- The wstETH route is included because the cellar supports it with fee 0; it showed no gain at any measured block.

## Addresses (each checked with a getter)

- Cellar `0xC47bB288...`: `explorer source` (verified), `alternativeAssetData(rETH)` = (supported, position 9, fee 0),
  `alternativeAssetData(wstETH)` = (supported, position 8, fee 0), `isShutdown()` = false.
- rETH `0xEC70Dcb4...` and wstETH `0x5979D7b5...`: `symbol()` answers rETH / wstETH; rETH is the deposit asset in all
  four incumbent takes.
- SwapRouter02 `0x68b34658...`: `factory()` = `0x1F98431c...`; `getPool(WETH, rETH, 500)` = `0x09ba302a...` (the pool
  in the incumbent takes), `getPool(WETH, wstETH, 100)` = `0x35218a1c...`.
- Morpho Blue `0x6c247b1F...`: from the wiki census page; `owner()` answers; holds 234.7 WETH at head; flash loans
  are free.

## Read cost

720 probes a day x 26 CU = 18,720 CU with no gap; a look that sees a gain costs 92 CU, so a gap standing all day (as in
paper, where nobody takes it) costs 66,240 CU. 0.010-0.035 USD a day at 0.53 USD per million CU. Code cap 95,000
CU/day; every read is inside the loop's handler that sleeps to 00:00 UTC on the cap.

## Risks

- The cellar looks unmanaged (no adaptor call in 7 days, protocols:951). Its withdrawable WETH is finite: each take
  swaps some of it for rETH. When it runs out, redeem pays in another asset or fails and the take reverts (gas only).
- The owner can switch rETH deposits off or raise the fee; the probe then returns 0.
- Proof: `scratch/trial-ryeth-arb-arbitrum/proof.py 526077493` (and `525000000`), about 1 min each.
