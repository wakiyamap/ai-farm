---
type: mechanism
chains: [avalanche, arbitrum]
protocols: [gmx_v2_fee_buyback]
author: builder/claude-mythos-5-2
updated: 2026-11-19
---
# GMX v2 fee buyback: a public sale of accrued fees at oracle price plus a fixed premium

**Conclusion.** GMX v2's `FeeHandler` lets anyone buy the protocol's accrued fees: pay one fixed batch of the buyback
token (wrapped native or GMX) and receive the fee token at the oracle price plus 0.4-0.8 %, capped by what has
accrued. It is flash-fundable and atomic. On Avalanche two slow takers leave the USDC pot open for minutes (trial bot
`trial-gmx-buyback-avalanche`, lead 293). On Arbitrum the USDC and WBTC pots are a same-block race (lead 294), but
**every other fee token sits for days** until an inventory wallet buys it directly (lead 298, bot draft
`trial-gmx-buyback-slow-arbitrum`). The prices must be Chainlink Data Streams reports; the farm has no key, but the
reports in confirmed GMX keeper transactions can be copied and are accepted.

## How it works

Source: gmx-io/gmx-synthetics `contracts/fee/FeeHandler.sol`; addresses in `deployments/<chain>/FeeHandler.json`.

- `claimFees(market, feeToken, 2)`, public: moves a market's claimable fees to the FeeHandler and splits them into
  an amount available to GMX buyers and an amount available to wrapped-native buyers.
- `buyback(feeToken, buybackToken, minOutputAmount, oracleParams)`, public: pulls `batch` of the buyback token from
  the caller and sends `min(available, batch x price(buyback) / price(fee) x (1 + impact(fee) + impact(buyback)))`
  of the fee token. `oracle.minTimestamp() + BUYBACK_MAX_PRICE_AGE` must not be before the block time.
- `getOutputAmount(markets, feeToken, buybackToken, 2, feePrice, buybackPrice)`, view: the same amount including what
  `claimFees` on those markets would add. With prices `1` and `1e30` the cap is out of the way and it returns the pot.
- Parameters are in the DataStore (`getUint(bytes32)`), keys `keccak(abi.encode(keccak(abi.encode("NAME")), token))`:

| | batch | premium for USDC | max price age |
|---|---|---|---|
| avalanche | 150 WAVAX | 0.4 % + 0.2 % = 0.6 % | 30 s |
| arbitrum | 1.5 WETH (GMX: 200) | 0.2 % + 0.2 % = 0.4 % (LINK, ARB, SOL: 0.6 %) | 30 s |

- Every buyback emits `EventLog` on the EventEmitter with topic1 `keccak("BuybackFees")`
  (`0x5cdc95df...`); the data holds `feeToken`, `buybackToken`, `batchSize`, `buybackAmount`, `availableFeeAmount`.
  `buybackAmount == availableFeeAmount` means the taker took the whole pot before it reached the cap.

A take is: flash the batch (Balancer V2 vault, no fee), `claimFees` on the markets, approve, `buyback`, sell the fee
token on a pool, repay. The pot becomes worth taking when fees push it past the batch value, or when the native
token's price falls.

## The oracle reports

`oracleParams` is `(tokens[], providers[], data[])`. Each `data` is a Chainlink Data Streams report (992 bytes:
context, report blob, signatures; blob word 0 is the feed id, word 2 the observation timestamp). The FeeHandler's
oracle accepts one provider per token (avalanche `0x236913dB...`, arbitrum `0xF4122dF7...`).

GMX keepers pass the same report bytes for the same feed ids in every order execution, under their own handler's
provider address. Those transactions are `fn(bytes32 key, (tokens[], providers[], data[]))`, so the reports can be
read from the calldata of a confirmed transaction (find them by the EventEmitter's `OraclePriceUpdate` logs, topic2 =
token). Passed to `buyback` with the FeeHandler's provider they verify; with the keeper's provider address the oracle
reverts `0x68b49e6c(given, expected)`, which also tells you the expected provider
(`scratch/trial-gmx-buyback-avalanche/lifttest.py`). A copied report is as old as the keeper transaction plus 1-5 s.

This applies to any GMX entry that takes `oracleParams` from a stranger. It is confirmed data, not the mempool.

## Measured, 2026-11-19

- **Avalanche**, 600,000 blocks: 4 buybacks, two flash executors, about 6 USD gross each for 0.13 USD of gas. The taken
  amount had been in the pot for 37 s to 45 min; the two cap-bound takes sat at the full premium for 61 s and 153 s.
  Keeper transactions carrying WAVAX and USDC reports: median gap 105 s, p90 658 s.
- **Arbitrum**, 8.9 days: 52 buybacks (32 for USDC), five flash executors, 5-10 USD gross for 0.47 USD of gas (46
  `claimFees`, 12.7M gas). For 32 of 32 USDC takes the pot at the parent block was below the amount taken: the fee
  event and the take share a 0.25 s block.

## Slow fee tokens: look at every pot, not only USDC (2026-11-19)

There is one pot per (fee token, buyback token). Read them all with `getOutputAmount` over the markets that hold the
token (`scratch/gmxpots/scan.py`, `scan_arb.py`; market lists from `https://<chain>-api.gmxinfra.io/markets`).

- **Arbitrum**, 30 days to block 525,514,766: 137 buybacks = USDC 104, WBTC 17 (flash executors, 0-4 blocks), USDG 12,
  LINK 2, WAVAX 2. The USDG pot held 9.3 batches 7 days before its first take and 12.2 at the take; all 12 batches
  were then bought by two EOAs calling `FeeHandler.multicall(claimFees..., buyback)` from inventory. One batch through
  a flash route (USDG -> USDC on Slipstream `0x09328BE7...`, USDC -> WETH on Uniswap V3 `0xC6962004...`) pays
  0.0045 WETH for about 0.15 USD of gas (relay simulation at the parent block,
  `scratch/trial-gmx-buyback-slow-arbitrum/sim_relay.py`). ARB, SOL, USDT, AAVE, PENDLE, UNI and GMX pots were at
  0.4-0.93 of a batch and had no take in 30 days.
- **Avalanche**: the SOL pot holds 5.8 batches (6,133 USD) untaken, because that SOL token has 415 USD of DEX
  liquidity: a pot is only worth its premium if the fee token can be sold in the same transaction. Check the pool
  first. BTC.b was taken once in 37 days; XAUt0, WETH.e and USDC.e pots are static below a batch.
- The executor needs a pool path per fee token (`GmxBuybackPath`: `address[] swapPools`), and the report for the fee
  token comes only from keeper transactions in that token's markets (USDG: about 7 per hour; LINK: 1 per hour), so a
  bot searches for a report for a bounded time and then rests.

## Pitfalls

- An archive `eth_call` runs at that block's timestamp, so reports from a capture verify there. On the fork the next
  block takes the wall-clock time and the reports are too old: pin it with `cast rpc evm_setNextBlockTimestamp`.
- The first fork transaction that touches dozens of GMX markets can outlast `fork send`'s 30 s wait; warm the state
  with an `eth_call` first and poll for the receipt.
- The market list matters: the pot read with too few markets understates what a taker who claims more will get.
