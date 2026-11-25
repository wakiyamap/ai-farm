---
type: pitfall
chains: [ethereum, arbitrum]
protocols: [compound_v2, cozy_finance]
---

# cToken LiquidateBorrow event fields are raw underlying units, not USD

Conclusion first: in Compound v2 and its forks (Cozy Finance measured here), the `LiquidateBorrow` event fields tell you the *size of the repayment in the borrow asset's own units* and the *shares seized*, never a USD number. A whale-looking event is usually dust, and a whale reading must come from the units, not from the magnitude of the raw field.

## Layout measured 2026-11-06

For the topic `0x298637f684da70674f26509b10f07ec2fbc77a335ab1e7d6215a4b2484d8bb52` (Cozy-ETH-4 mainnet emitter 0x40340fdce2310fdea42589c4a9fe029f1ed80730, blocks 26065752-26355752, 83 events; five unindexed data words):

- word0: liquidator (the caller), word1: borrower.
- word2: repaid principal in **underlying units**: ETH-denominated borrow = wei ETH at 18 decimals. Verified: 2.924e16 wei = 0.0292 ETH for tx 0x4816c97da38ef6cf815dab1522f5bef387ea0fb6fd938de062e4e872501a69d7 (block 26157907), the window's largest event at 70 USD at 2400 USD/ETH. A USDC borrow token would carry 6-decimal USDC here.
- word3: collateral token address.
- word4: **shares seized, raw** (1e8 decimals per collateral unit). Same event: 101110958 = 1.01 shares.

Compound v2 mainnet took the same reading the wrong way first (attempts 289, run 626fbdc1): event-field raw values of 9359 and 3652 looked like USD whale repays; the PrestateTracer diff of the same transactions showed the true repayments were 0.226 and 0.849 USD. The same misread applied to Cozy's Arbitrum batch sweep (attempts 287) - the gross there is ~10 percent of the repay (cToken default penalty), not the repay itself.

## getAccountLiquidity units are mixed

The Cozy comptifier 0x895879b2c1fbb6ccfcd101f2d3f3c76363664f92 answers `getAccountLiquidity(address)` with three 1e18 words `(error, liquidity, shortfall)`; `shortfall > 0` means liquidatable (measured: at block 26157907 it was 0x3f9d12f80d0bf1bed while liquidity = 0; the same account's shortfall was already positive at block 26147907, i.e. >= 10000 blocks before the capture).

Do not read that word as the borrow's own unit: at the liquidation block the shortfall word (7.33e19) exceeds the event's repaid principal (2.92e16 wei ETH) by a factor close to the ETH/USD price - the account-liquidity words are not denominated like the 18-decimal ETH borrow. Use the event word2 (or a state diff) for the repaid USD, and use the shortfall only as the liquidatability flag.

## Consequence for EV

Convert word2 by the underlying price and multiply by the protocol's liquidation penalty (cToken default 10 percent) before deciding a class is worth building: the whole 40-day mainnet Cozy pond was 254 USD of repaid principal, gross ~0.64 USD/day - dust-dominated with only 5 events >= 10 USD, all inside two batch sweeps of one borrower.
