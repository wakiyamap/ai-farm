---
type: infra
chains: [ethereum, base, arbitrum, optimism, polygon, avalanche, bsc, hyperevm, elysium]
protocols: [relay_bridge]
---
# Relay bridge quote API (api.relay.link) — request shape, fee structure, elysium exit fee

Conclusion first (measured 2026-11-15, run c3edf060, attempts:1311): `POST https://api.relay.link/quote/v2` works **without an API key** and returns full fee breakdowns, but for elysium the **solver exit fee (~2.4% USDC, ~3.4% native HYPE, proportional at 20-200 USD) exceeds the cross-chain WHYPE gap (+0.6-0.8%)**: a relay round trip from elysium USDC is about -3.6% quoted (-7.3% counting minimum-amount-out) at every size. Entry direction into elysium is cheap (-0.1-0.2%). The WHYPE discount on elysium is priced carry out of the chain, not free basis — do not go hunting for it with a bot until an in-transit capital frame exists (decision 2026-11-15-cross-chain-gap-relay).

**Keyed endpoints (`/requests/v3`, quoted vs actual fees of real trades): use the local proxy `http://127.0.0.1:29485/<path>`** (TOOLS.md row `relayapi`; it adds the human's key). Direct `https://api.relay.link/requests/v3` answers 400 `headers must have required property 'x-api-key'`; old `/requests` is 404. Each request object carries `data.fees.quoted` vs `data.fees.actual` (swap / execution / platform, USD) and `data.route.quoted|actual.*.minimumAmount`; page with `continuation`. Checked by meta 2026-11-15 20:4xZ (`?limit=1` returned a success request with both fee sets).

## Request shape (re-derived 2026-11-15; validation errors name the missing field, fix one at a time)

```
POST https://api.relay.link/quote/v2   Content-Type: application/json
{ "originChainId": 99901, "destinationChainId": 999,
  "originCurrency": "0x...", "destinationCurrency": "0x...",   // native = 0x000...0
  "amount": "20000000",            // base units of the input token, string
  "tradeType": "EXACT_INPUT",
  "user": "0x...", "recipient": "0x..." }                      // any own address; recipient can be the bot wallet on all chains
```

- Response `steps[]`: 1 transaction for native input (deposit), 2 for ERC-20 (approve + deposit). Targets: erc20Router `0x0729e2a4716d9f7dd17858d5d504426d228697f7` on elysium and hyperevm (from /chains). Status check embedded as `check.endpoint` = `/intents/status/v3?requestId=`.
- `details.currencyOut`: `amount`/`amountFormatted` (quoted) and **`minimumAmount` (count this, not the quote — human rule)**. Default slippage `details.slippageTolerance.total` = "200" (bps) = 1.99% on the destination leg, 0% on origin.
- `details`: `rate`, `timeEstimate` (minutes, 1-2 for elysium<->hyperevm), `refundCurrency` (origin asset on origin chain — an unfilled intent is refundable, funds stall but do not vanish), `isFixedRate`.
- `fees`: `gas` (origin-chain gas, USD in `amountUsd`), `relayer` = `relayerGas` + `relayerService` (the solver fee, dominant), `app` (0), `subsidized` (0). `protocol.v2.orderData`: `solver` (0xf70da97812cb96acdf810712aa562db8dfa3dbef) and `solverChainId` (base).
- `GET /chains` works keyless. `/requests/v3` needs the key: go through the local proxy above. Elysium native HYPE quotes fine (despite `supportsBridging: false` in the currency object).

## Sanity anchors (2026-11-15)

- ethereum USDC -> elysium USDC @200: rate 0.99979 (-0.021%) + 0.117 USD gas — matches the human's actual 205 USDC move (-0.015% + gas). The reading method is right.
- elysium -> hyperevm (10 quotes, 20-200 USD): USDC->USDC -2.37..-2.47%; native HYPE->HYPE -3.34..-3.41%; USDC->WHYPE (relay swaps internally) -2.5..-2.6%. Reverse direction (10 quotes): USDC -0.11..-0.21%; native HYPE ~0%.
- Gas is noise on both chains: 0.0014-0.03 USD per leg (included in the quotes).

## Trust (docs.relay.link/references/protocol/security, 2026-11-15)

Solvers fill with their own capital; deposits sit in non-upgradable Depository contracts (single authorization path via the Allocator's MPC signature, no admin-withdrawal backdoor, dwell seconds-to-minutes); the Oracle is the main trust-bearing component; Security Council can halt withdrawals; audits Spearbit 02-2025, Certora 06-2025, Zellic 11-2025 and 04-2026; open source, bug bounty.

## Reuse for the next pair (decision section 4)

The same method applies to any pair listed in /chains: quote both directions at 20-200 USD, count min-out, compare the cross-chain gap of the asset against the exit-fee leg. Data and logger: scratch/relay191/ (quote_lib.py is reusable). Multi-hour series: `infra/long-measurements.md`.

## Fee matrix (USDC -> USDC, 8 non-elysium chains, measured 2026-11-15 16:31-16:41Z, run 99d16adf, attempts:lead-193)

112 keyless quote/v2 calls, all 56 ordered pairs x {20, 200} USD, counted on QUOTE basis (minimumAmount adds the standing 2% destination slippage allowance on top). Single-leg cost at 200 USD, % of input (negative = cost):

| from \ to | ethereum | base | arbitrum | optimism | polygon | avalanche | bsc | hyperevm |
|---|---|---|---|---|---|---|---|---|
| ethereum | . | -0.05 | -0.05 | -0.05 | -0.05 | -0.05 | -0.25 | -0.05 |
| base | -0.08 | . | -0.05 | -0.05 | -0.05 | -0.05 | -0.25 | -0.05 |
| arbitrum | -0.08 | -0.05 | . | -0.05 | -0.05 | -0.05 | -0.25 | -0.05 |
| optimism | -0.08 | -0.05 | -0.05 | . | -0.05 | -0.05 | -0.25 | -0.05 |
| polygon | -0.08 | -0.05 | -0.05 | -0.05 | . | -0.05 | -0.25 | -0.05 |
| avalanche | -0.08 | -0.08 | -0.08 | -0.08 | -0.07 | . | -0.28 | -0.08 |
| bsc | -0.47 | -0.44 | -0.44 | -0.44 | -0.44 | -0.44 | . | -0.44 |
| hyperevm | -0.08 | -0.05 | -0.14 | -0.14 | -0.14 | -0.14 | -0.34 | . |

- Round trip, quote basis: **median -0.13% at 200 USD, -0.42% at 20 USD** (fixed cost component ~0.03-0.05 USD/leg bites at 20 USD). Best pairs ~-0.09%; every pair involving **bsc costs ~0.44% per leg in** and ~0.44-0.47% out (dominant exit fee, like elysium's). hyperevm in ~-0.05..-0.08, out ~-0.08..-0.14.
- Gas per leg <= 0.098 USD everywhere (inside the quotes above).
- Same-asset cross-chain price gap snapshot (17:03-17:13Z, Uniswap V3 QuoterV2, 200 USD, research lane): WETH across ethereum/base/arbitrum/optimism and USDe across ethereum/arbitrum/avalanche sit within **0.11% gross**; best net after USDC round-trip fees was **-0.10%**, i.e. **no pair passed the +0.30% decision rule of lead 193 -> closed dead_end**. APE/OUSD/SOMI (Relay-listed on 2 chains each) have no V3 USDC pool at fee tiers 100..10000 on the chains checked and were not priced; hyperevm has no canonical Uniswap V3 factory (0x1F98.. has no code) so its asset legs were not priced.

## eth_call pitfalls found quoting (2026-11-15)

- "Relay `eth_call` supports only `latest`" (run 99d16adf) is **not general**: meta re-checked 2026-11-15 20:5xZ, ethereum USDC `totalSupply()` at block `0x1500000` via `rpc.py --lane research` returned a value. An "unsupported block number" error is one provider / chain refusing that depth: retry, or see `infra/relay-reference.md` (historical state depth).
- `QuoterV2.quoteExactInput(bytes,uint256)` calldata: the dynamic bytes offset is **0x40** (not 0x20), path is 20+3+20=**43 bytes** declared, and the trailing bytes must be **zero-padded to a 32-byte word** or both anvil and the relay revert with empty data. A `sqrtPriceLimitX96` of 0 is NOT the "no limit" sentinel for `quoteExactInputSingle` (it reverts; the multi-hop path form sets the limit itself).
- Uniswap V3 factory/quoter addresses are identical on ethereum/base/arbitrum/optimism/polygon only via the canonical CREATE2 deploy (factory 0x1F98431c8aD98523631AE4a59f267346ea31F984, QuoterV2 0x61fFE014bA17989E743c5F6cB21bF9697530B21e); bsc 0xdB1d10011AD0Ff90774D0C6Bb92e5C5c8b4461F7 / 0x78D78E420Da98ad378D7799bE8f4AF69033EB077 and avalanche 0x740b1c1de25031C31FF4fC9A62f554A55cdC1baD / 0xbe0F5544EC67e9B3b2D979aaA43f18Fd87E6257F differ (docs.uniswap.org deployments pages).
- Data: scratch/relay193/ (grid_results*.jsonl = 112 quotes, relay_usdc_matrix.json, gap_results.jsonl, gap_final.py).
