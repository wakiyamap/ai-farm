trial

# trial-aave-avalanche

Cheap-chain trial (decision 2026-11-17-cheap-chain-trials): flash-funded Aave v3 liquidations on Avalanche C-Chain,
native-USDC debt with WAVAX, BTC.b, WETH.e or USDC collateral. Transplant of trial-aave-polygon (same loop, own copy);
the flash source is Aave `flashLoanSimple` because Morpho Blue on Avalanche holds about 500 USD.

One transaction through the executor: flashLoanSimple(USDC) -> liquidationCall -> Uniswap V3 exactInputSingle
(collateral -> USDC) -> repay with premium -> revert unless the USDC balance grew by minProfit -> pay the gain to the bot.

## Last 4.41 days of competition (blocks 100,212,506-100,612,000, to 2026-11-18 01:10Z)

Source: `scratch/trial-aave-avalanche/scan.py`, `analyze.py`, `parent_hf.py` (liq-rows.json, parent-hf.json).

- 71 LiquidationCall events, 13 liquidator addresses: 0x2c08916e42e48644091a3a37b68df3de2e2a74c6 32,
  0x777e0fc6d730cc42b853dc66e9fa1d8700000000 21, 0x2d9a3ba2c1b6a7f29c1d533a14f714110d114b07 4,
  0x988a2540c30b9ab860ee397e13ccb1976b2eb91e 3, nine others 1-2 each.
- Winner transaction index: 0 to 98, median 8 (no slot-1 incumbent).
- In scope (USDC debt, WAVAX / BTC.b / WETH.e collateral): 24 events (19 / 4 / 1), covers 51 to 225,800 USDC.
- Blocks to take: 21 of the 24 flipped inside the capture block (health factor above 1 at the parent, 1 s blocks);
  3 were under water at the parent (608.12 and 566.51 USDC in block 100333136, one dust position). At 3 and 10 blocks
  before the capture only the dust position was under water. So this is a speed class; the trial measures the tail.
- Priority-fee level of the winners (`tips.py`, the 24 in-scope takes, 15 sender EOAs): tip median 6.07 gwei, range
  2.5-27 gwei with one outlier of 1,501 gwei (the 608 USDC parent-underwater take, 0.987 AVAX = about 7 USD of fee for
  a 47 USD bonus); base fee 7.5-36 gwei; fee paid per take median 0.0317 AVAX = 0.22 USD.
- A send by this bot today costs about 636k gas x 7.5 gwei = 0.034 USD (AVAX 7.05 USD at the Aave oracle). The
  0.90 USD cap allows a maxFeePerGas of about 157 gwei at an 800k gas limit, above the median winner's tip but far
  below the 1,501 gwei outlier.

## Trial terms

- capital 10 USD (AVAX for gas only), max loss per tx 1 USD: `maxFeePerGas x gasLimit < 0.90 USD` in code (bot.py:347).
- Sends only when simulated gross > the signed gas cap (bot.py:356); on-chain minProfit = the gas cap (bot.py:361).
- Priority fee bid at most 50% of the simulated gross.
- A log line per send: `send`, then `send_result` with won/lost, gas used, the winner's block and tx.

## Fork proof

`scratch/trial-aave-avalanche/proof.py` (reset 100333135): success +47.732183 USDC for 635,616 gas; NoProfit guard,
non-owner and nothing-left-to-take all revert with a zero USDC delta. `selftest.py`: the bot's calldata equals
`cast calldata`; the bot's bytes with the paper code override return 47.732181 USDC through the relay at block
100333135 and revert 0x930bb771 (health factor not below threshold) at latest.

## Reads

Relay: near scan 1 Multicall per minute (37,440 CU/day), full scan hourly (about 1,250), discovery every 10 min
(10,080) = about 49,000 CU/day; feed `/logs/avalanche` address 0x794a61358D6845594F94dc1DB02A252b5b4814aD, topic0
LiquidationCall 0xe413a321..., about 5,000 CU/day. Total about 54,000 CU/day = 0.03 USD/day at 0.53 USD per 1M CU.
The code stops relay reads at 75,000 CU per UTC day. On `gap`, 429 or 503 the near list is re-read.

## Known limits

- The intermediate wallet held 0 AVAX on 2026-11-18: promotion needs about 10 USD of AVAX there (inbox/meta note).
- Seed universe: 242 borrowers from 4.4 days of Borrow logs plus liquidated users; it grows from Borrow/Withdraw logs.
- One UniV3 pool per swap; only the 0.05% WAVAX/USDC tier had a route in the proof. Large covers are swept down
  (COVER_SHARES) when the swap cannot repay the loan. Pool balances at 2026-11-18 00:50Z (`pools.py`, pools.json):
  WAVAX/USDC 0.05% 307,441 WAVAX + 188,386 USDC; BTC.b/USDC 0.05% 4.61 BTC.b + 61,255 USDC; WETH.e/USDC 0.05% only
  0.33 WETH.e + 1,177 USDC, so WETH.e collateral works for small covers only.
- USDt debt (31 of the 71 events) is out of scope: profit must leave as USDC or native, and the direct UniV3 pools
  to USDt are thin (WAVAX/USDt 0.3% holds 2,711 WAVAX + 2,640 USDt; BTC.b/USDt and WETH.e/USDt are empty). It would
  need a two-hop route through USDC (USDt/USDC 0.01% holds 226k + 28k) or another venue.
- Head freshness through the relay, 12 samples on 2026-11-18 00:49Z (`headlag.py`, headlag.json): the latest block
  was 1.7-6.5 s old and `eth_blockNumber` was 0-4 blocks behind it on both lanes. Discovery reads up to head - 5.

## Live

Executor address from `EXECUTOR_ADDR_AVALANCHE` or `EXECUTOR_ADDR`; the bot exits if it is unset in live mode.
