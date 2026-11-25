trial: ETH2x-FLI-P issue / redeem arbitrage on Polygon (cheap-chain trial, decision 2026-11-17-cheap-chain-trials)

## What it does

Aave v2 on Polygon is frozen, so its aToken amWETH cannot be minted any more and is worth about 32 pct more than WETH
wherever it is the only way in. Index Coop's ETH2x-FLI-P SetToken (deleveraged: 0.00218 amWETH + 56 units of USDC.e
per token) can still be issued and redeemed by anyone at NAV. Its SushiSwap pair (about 7,470 FLI / 21.6 WETH) and
the Curve pools that hold aTokens price that premium independently, and they drift apart whenever CRV, POL, ETH or
MAI move. One transaction, funded by a Morpho Blue flash loan of WPOL, closes the gap:

- `issue_crv`: WPOL -> CRV (Uniswap V3) -> atricrypto3 LP (Curve CRV pool) -> amWETH (remove one coin) -> issue FLI
  -> sell FLI on SushiSwap -> WETH -> WPOL
- `redeem_mai`: WPOL -> WETH -> buy FLI on SushiSwap -> redeem -> amWETH -> am3CRV (atricrypto3) -> MAI (Curve
  metapool) -> USDC.e -> WPOL
- `issue_mai`, `redeem_crv`: the same two venues in the other direction (never positive at the blocks tested so far).

Every 30 s the bot asks the executor, in one `eth_call` (`probe`), what each route would gain at 500 / 1,000 / 2,000
WPOL. If the best gain is above the gas cap of the send (`gasLimit x maxFeePerGas`), it simulates the exact call and
(live) sends it with `minProfit = cap`. The executor reverts unless the WPOL balance grew by `minProfit`, unwraps the
gain and pays it to the bot wallet as POL.

## Competition, last 5.2 days (blocks 97,296,091-97,598,491)

Source: `scratch/r8bc8/takes.json` (every DebtIssuanceModuleV2 log for the SetToken).

| sender | contract | atomic takes | notes |
|---|---|---|---|
| 0x7c4106a773a04634e2c5b6b96b0d0cd9c8e2d893 | 0xc9781615b459dbba2333d8093de140b91525857f | 69 | kept 508.8 WPOL (7.4 per take), minimum priority fee, tx index 31-245 |
| 0xc3afb378... | 0x91a7fbae... | 14 | profit in USDC.e; some sends at tx index 0 with 4-5 POL gas; also redeems FLI from its own wallet |
| 0x7d6d03bc1c659d0fab8540c65aca34b663135acf | 0x4d7d7e39da005479b0a1470584692936ed2cdae6 | 11 | since 2026-11-18, profit kept in the contract |
| 0xde0a99fb39e78efd3529e31d78434f7645601163 | 0x3cb2452c615007b9ef94d5814765eb48b71ae520 | 6 | MAI route |
| 0x3de7e4a0, 0x9cacc286, 0xd035d5b7, 0xbb89e8af | own contracts | 3, 3, 1, 1 | 0xbb89e8af paid 37 POL gas at index 0 once |

Blocks to take (`scratch/trial-fli-arb-polygon/series-windows.json`, the bot's own `take()` at earlier blocks, 18
takes): the gain above 1 WPOL was already there 3 blocks before the take in 15 of 18, 10 blocks (15 s) before in 10,
100 blocks before in 4; median 10 blocks. Priority fee level: the Polygon minimum (about 30 gwei) for the two main
operators; two operators sometimes pay 4-37 POL to be first in the block.

## Addresses

Verified on Blockscout: SetToken 0x3Ad707dA309f3845cd602059901E39C4dcd66473 (`SetToken`), DebtIssuanceModuleV2
0xf2dC2f456b98Af9A6bEEa072AF152a7b0EaA40C9. From the incumbents' traces (`scratch/r8bc8/dumpcalls.py`), each with a
getter answering in the fork runs: Morpho Blue 0x1bF0c2541F820E775182832f06c0B7Fc27A25f67, SushiSwap router
0x1b02dA8Cb0d097eB8D57A175b88c7D8b47997506, Uniswap V3 SwapRouter 0xE592427A0AEce92De3Edee1F18E0157C05861564, Curve
atricrypto3 0x92215849c439E1f8612b6646060B4E3E5ef822cC, Curve CRV / atricrypto3-LP pool
0xc7c939A474CB10EB837894D1ed1a77C61B268Fa7, Curve MAI / am3CRV 0x447646e84498552e62eCF097Cc305eaBFFF09308, Aave v2
LendingPool 0x8dFf5E27EA6b7AC08EbFdf9eB090F32ee9a30fcf.

## Loss bound

A lost attempt costs gas only: at most `gasLimit x maxFeePerGas`, about 1.2-1.4 POL (0.10-0.12 USD) at 250 gwei base
fee; the code refuses a send whose cap is 0.95 USD or more at 0.15 USD per POL. `capital_usd` 10 is the whole budget.

## Read cost

One `eth_call` per 30 s = 2,880 x 26 CU = 74,880 CU/day, plus about 70 CU per opportunity: about 76,000 CU/day =
0.04 USD/day at 0.53 USD per million CU. Code cap 95,000 CU/day. No feed filter.

## Logs (`logs/bot.jsonl`)

`start`, `check` (one line per 10 quiet minutes), `opportunity`, `opportunity_skip`, `simulate_revert`, `paper_sim`,
`send_result` (won / lost, gas used, send block, winner block, tx index), `signer_reject`, `read_budget`.

## Not covered

Other amWETH sources (liquidations on Aave v2 with receiveAToken, other aToken pools) and the other Polygon
SetTokens are not routed. The SushiSwap pair holds about 21.6 WETH: the class ends when it is drained or when the
premium disappears.
