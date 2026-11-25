trial

# trial-venus-bsc

Cheap-chain trial (decision 2026-11-17-cheap-chain-trials): flash-funded liquidations on the Venus core pool on
BNB Smart Chain (Unitroller 0xfD36E2c2a6789Db23113685031d7F16329158384, Liquidator
0x0870793286aada55d39ce7f82fb2766e8004cf43, both from VenusProtocol/venus-protocol
deployments/bscmainnet_addresses.json; the Liquidator is the comptroller's `liquidatorContract()`). Debt markets
vUSDT and vUSDC; collateral markets vBNB, vBTC, vETH, vXRP, vDOGE, vADA, vXVS, vSOL, vCAKE, vUNI, vLTC and the two
stable markets. Close factor 0.5; the Liquidator keeps half of the liquidation incentive for the protocol
(`treasuryPercentMantissa` 0.5e18), so the taker keeps about 5% of the repaid debt before swap costs.

One transaction through the executor: Aave v3 flashLoanSimple(debt) -> Venus Liquidator.liquidateBorrow ->
vColl.redeem -> (wrap BNB) -> PancakeSwap V3 exactInput collateral -> debt -> repay with premium -> (USDT surplus
-> USDC) -> revert unless the USDC balance grew by minProfit -> pay the gain to the bot as USDC.

## Last 7 days of competition (blocks 132,897,684-134,241,248, to 2026-11-18 03:42Z)

Source: `scratch/trial-venus-bsc/scan.py`, `analyze.py`, `parent.py` (liq-rows.json, liq-detail.json).

- 1,466 LiquidateBorrowedTokens events on the Liquidator, 35 liquidators, 2,151,879 USD repaid (today's Venus
  oracle prices). 1,233 events are under 1 USD (dust sweeps: 0x02e5723bf9d7cdb72f41eae059c77a8bc014df94 1,003,
  0x6972151f9d5024caff7f22744de22f91eccf7a72 98); 163 have 20 USD or more (median 275 USD). 1,231 of the events
  fell on one day (2026-11-14): takes come in bursts with price moves.
- In scope (USDT or USDC debt, 20 USD or more): 123 takes, 2,085,797 USD repaid, median 708 USD, largest 669,508:
  0xd12810b19b596347a3afac206d3ca65d08594b3f 57, 0xb63414a2ee1fe0b984b8fa9b81ccc05f85a10874 23,
  0x5225328cfb29f5a16c85aff112f76fa2f48c3523 9, 0x5ac9bc14376bf2727c6211960cf3cec1e2f295bd 6,
  0xf000042d2b48921c234f15d167e7874f594f303e 5, 0x4bac35f9caea8e7f484346404c8800f80b5994d1 5,
  0xec5bcf2077ccb42074f5bf667acb211c9ccc60c0 4, 0x3d8280fc577d1b02f5c28f5e70ac9a2409c8caf4 3, others 1-2.
  Collateral: XRP 30, BNB 22, BTCB 21, ETH 19, DOGE 14, ADA 4, XVS 3, SOL 3, Cake 2, USDT 2, UNI, USDC, LTC 1.
  The last in-scope take was at block 133,649,266, about 3.1 days before the scan.
- Blocks to take: 116 of 123 had shortfall 0 at the parent block (`getAccountLiquidity`), so they were taken in
  the block they became takeable (0.45 s blocks). 7 were takeable one block earlier; 1 of them for 4-6 blocks
  (about 2-3 s: block 133614356, 25 USDT repaid, the fork-proof case); none for 7 blocks. Winner transaction
  index p10 / p50 / p90 = 1 / 30 / 144 (no fixed slot-1 incumbent).
- Gas-price level of the winners (17 receipts: 5 largest + 12 others): effective gas price median 0.1 gwei, range
  0.05-1.0 gwei (BSC has no base fee); gas used median 2,115,090 (1.45M-6.0M); 14 of the 17 enter through the shared
  contract 0x21b7d28b882772a1cfe633daee6f42ebb95dec4e.
- A send by this bot costs about 1.66-2.0M gas x 0.05-0.1 gwei = 0.05-0.12 USD (BNB 591.5 USD at the Venus oracle).
  The 0.90 USD cap allows a gas price of about 0.6 gwei at a 2.5M gas limit, above 16 of the 17 sampled winners.

This is a speed class; the trial measures how often an account is still in shortfall when the farm arrives.

## Trial terms

- capital 10 USD (BNB for gas only), max loss per tx 1 USD: `gasPrice x gasLimit < 0.90 USD` in code (bot.py:391).
- Sends only when simulated gross > the signed gas cap (bot.py:400); on-chain minProfit = the gas cap (bot.py:405).
- Gas-price bid at most 50% of the simulated gross (bot.py:392-400). If the network's `eth_gasPrice` exceeds that bid, skip the send and log `minimum_gas_price_exceeds_bid_share`.
- A log line per send: `send`, then `send_result` with won/lost, gas used, the winner's block and tx.

## Fork proof

`scratch/trial-venus-bsc/proof.py` (reset 133614355): success +1.014197 USDC on 25.048580 USDT repaid for
1,657,964 gas (vXRP collateral, the two-hop route XRP -> WBNB -> USDT and the USDT -> USDC payout hop all
exercised); NoProfit guard, non-owner and nothing-left-to-take (Liquidator `LiquidationFailed(3)`) revert with a
zero USDC delta; nothing is left in the executor. `selftest.py`: the bot's calldata equals `cast calldata` (three
shapes); the bot's own route search with the paper code override returns 1.014197 USDC through the relay at block
133614355 and reverts at latest; discovery, one full and one near scan ran.

## Reads

Relay: near scan 1 Multicall per minute (1,440 x 26 = 37,440 CU/day), full scan every 3 h (about 45 calls x 26 x 8
= 9,400), discovery every 10 min (144 x 85 = 12,240) = about 59,000 CU/day; feed `/logs/bsc`, one filter: address
0x0870793286aada55d39ce7f82fb2766e8004cf43 (Venus Liquidator), topic0 LiquidateBorrowedTokens 0xdd091524...
(about 210 events/day on average, bursts on crash days), about 5,000 CU/day. Total about 64,000 CU/day = 0.034
USD/day at 0.53 USD per 1M CU. The code stops relay reads at 85,000 CU per UTC day. On `gap`, 429 or 503 the near
list is re-read.

## Known limits

- The BSC intermediate wallet held 2.88 USD of BNB on 2026-11-18 03:50Z (`gate status`): promotion needs about
  10 USD of BNB there (inbox/meta note).
- Seed universe: 1,348 accounts from 28 days of Borrow logs on vUSDT and vUSDC (3,210 logs, blocks
  128,866,992-134,241,248, `seed.py`) plus the accounts liquidated in the census. Older borrowers are missing
  until they borrow again (Borrow logs every 10 min), so the bot sees only part of the Venus book. The full scan ranks only the 1,500 largest in-scope debts and watches the 50 nearest to shortfall.
- The trigger is another taker's LiquidateBorrowedTokens or the 60 s scan, not the oracle update itself, so the bot
  is at least one block behind the first taker by design.
- PancakeSwap V3 routes are fixed per collateral (deepest pool per pair on 2026-11-18, `routes.py`): everything
  goes through WBNB to USDT; BNB, BTCB and ETH are tried with the WBNB -> USDT hop at 0.01% and at 0.05%. Large
  repayments are swept down (REPAY_SHARES) when slippage eats the bonus.
- BNB-debt and VAI-debt positions are not taken (native repayment / VAI controller path), nor borrowers under a
  Venus liquidation allowlist (`restrictLiquidation`: the call reverts and costs nothing in simulation).

## Live

Executor address from `EXECUTOR_ADDR_BSC` or `EXECUTOR_ADDR`; the bot exits if it is unset in live mode.
