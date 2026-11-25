trial

# trial-benqi-avalanche

Cheap-chain trial (decision 2026-11-17-cheap-chain-trials): flash-funded liquidations on Benqi Lending, the
Compound v2 fork on Avalanche C-Chain (comptroller 0x486Af39519B4Dc9a7fCcd318217352830E8AD9b4, from the DefiLlama
benqi adapter). Debt markets qiUSDCn (native USDC) and qiUSDTn (USDt); collateral markets qiAVAX, qiBTC.b, qiETH and
the two stable markets. Close factor 0.5, liquidation incentive 1.10, protocol seize share 0.03: the taker keeps
about 7% of the repaid debt before swap costs.

One transaction through the executor: Aave flashLoanSimple(debt) -> qiDebt.liquidateBorrow -> qiColl.redeem ->
(wrap AVAX) -> Uniswap V3 exactInput collateral -> debt -> repay with premium -> (USDt surplus -> USDC) -> revert
unless the USDC balance grew by minProfit -> pay the gain to the bot as USDC.

## Last 7.1 days of competition (blocks 99,975,805-100,615,805, to 2026-11-18 01:40Z)

Source: `scratch/trial-benqi-avalanche/scan.py`, `analyze.py`, `parent.py`, `after.py` (liq-detail.json).

- 55 LiquidateBorrow events, 12 liquidator contracts, 24 sender EOAs, 64,673 USD repaid:
  0x2c08916e42e48644091a3a37b68df3de2e2a74c6 16, 0xcba6efccec3ee12f078f78eee8c0d7505b0941b2 13 (dust, QI collateral),
  0x777e0fc6d730cc42b853dc66e9fa1d8700000000 10, 0x5ac9bc14376bf2727c6211960cf3cec1e2f295bd 3,
  0x988a2540c30b9ab860ee397e13ccb1976b2eb91e 3, 0x2d9a3ba2c1b6a7f29c1d533a14f714110d114b07 3, six others 1-2 each.
- In scope (USDC or USDt debt; AVAX, BTC.b, WETH.e or stable collateral): 26 takes, 60,684 USD repaid; 21 with
  20 USD or more repaid (median 336 USD, largest 13,966), by 3 contracts (0x2c08916e 14, 0x777e0fc6 5, 0x2d9a3ba2 2)
  through 9 senders. Out of scope: sAVAX collateral (6 takes, no UniV3 liquidity), LINK.e, AVAX / AUSD / DAI.e /
  .e-stable debt.
- Blocks to take: all 21 had shortfall 0 at the parent block (`getAccountLiquidity`), so they were taken in the
  block they became takeable (about 1 s blocks). Winner transaction index 1-69, median 8 (no slot-1 incumbent).
  After every take of 100 USD or more the account had no shortfall left (+0, +3, +10 blocks). Of all 55 takes, 23
  were takeable at the parent: 22 small ones (14 USD repaid or less, mostly QI-collateral dust) and one 245 USD
  AUSD-debt take (one block).
- Priority-fee level of the 21 winners: tip 0.48-17.5 gwei, median 3.7; base fee 7.5-36 gwei; they use
  1.3-3.4M gas.
- A send by this bot costs about 1.3-1.5M gas x (7.5 gwei + tip) = 0.08-0.15 USD (AVAX 7.18 USD at the Benqi
  oracle). The 0.90 USD cap allows a maxFeePerGas of about 66 gwei at a 1.87M gas limit, above every winner's tip in
  the census at a normal base fee.

This is a speed class; the trial measures how often an account is still in shortfall when the farm arrives.

## Trial terms

- capital 10 USD (AVAX for gas only), max loss per tx 1 USD: `maxFeePerGas x gasLimit < 0.90 USD` in code (bot.py:369).
- Sends only when simulated gross > the signed gas cap (bot.py:378); on-chain minProfit = the gas cap (bot.py:383).
- Priority fee bid at most 50% of the simulated gross.
- A log line per send: `send`, then `send_result` with won/lost, gas used, the winner's block and tx.

## Fork proof

`scratch/trial-benqi-avalanche/proof.py` (reset 100331843): success +0.927555 USDC on 14.195968 USDt repaid for
1,266,140 gas (qiAVAX collateral, the two-hop route and the USDt -> USDC payout hop all exercised); NoProfit guard,
non-owner and nothing-left-to-take (MarketError(1, 3)) revert with a zero USDC delta; nothing is left in the
executor. `selftest.py`: the bot's calldata equals `cast calldata`; the bot's own route search with the paper code
override returns 0.927555 USDC through the relay at block 100331843 and reverts at latest; one full and one near
scan ran (251 accounts, 156 debtors, 0 in shortfall, 364 CU).

## Reads

Relay: near scan 1 Multicall per minute (37,440 CU/day), full scan hourly (about 2,500), discovery every 10 min
(10,080) = about 50,000 CU/day; feed `/logs/avalanche`, two filters: address
0xB715808a78F6041E46d61Cb123C9B4A27056AE9C (qiUSDCn) and 0xd8fcDa6ec4Bdc547C0827B8804e89aCd817d56EF (qiUSDTn),
topic0 LiquidateBorrow 0x298637f6..., about 6,000 CU/day. Total about 56,000 CU/day = 0.03 USD/day at 0.53 USD per
1M CU. The code stops relay reads at 75,000 CU per UTC day. On `gap`, 429 or 503 the near list is re-read.

## Known limits

- The intermediate wallet held 0 AVAX on 2026-11-18 (`gate status`): promotion needs about 10 USD of AVAX there
  (inbox/meta note; trial-aave-avalanche waits for the same).
- Seed universe: 251 accounts from 67 days of Borrow logs on the two debt markets plus the accounts liquidated in
  the census; they hold 79% of the two markets' total borrows (13.42M of 16.95M USD). Older borrowers are missing
  until they borrow again (Borrow logs every 10 min).
- The trigger is another taker's LiquidateBorrow or the 60 s scan, not the oracle update itself, so the bot is at
  least one block behind the first taker by design.
- One UniV3 route per collateral: WAVAX -> USDC 0.05% (pool holds 307k WAVAX + 188k USDC), BTC.b -> USDC 0.05%
  (4.6 BTC.b + 61k USDC), WETH.e -> WAVAX -> USDC (46.6 WETH.e + 19k WAVAX in the first pool), USDt <-> USDC 0.01%
  (226k + 28k). Large repayments are swept down (REPAY_SHARES) when slippage eats the bonus.
- AVAX-debt positions (qiAVAX borrow) are not taken: the repayment would be native and the executor is ERC-20 only.

## Live

Executor address from `EXECUTOR_ADDR_AVALANCHE` or `EXECUTOR_ADDR`; the bot exits if it is unset in live mode.
