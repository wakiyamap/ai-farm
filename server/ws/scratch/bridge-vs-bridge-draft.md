---
type: infra
chains: [ethereum, base, arbitrum, optimism, polygon, avalanche, bsc, hyperevm]
protocols: [relay_bridge, across, stargate]
---
# Cross-bridge USDC quote comparison (Relay vs Across vs Stargate) — result and reachable keyless APIs

Conclusion first (measured 2026-11-16 11:01-11:07Z, run 284397a1, attempts/dead_end): going out one bridge and back another **never nets positive** on the 8 non-elysium farm chains. Best cross-bridge round trip at 200 USD was **-0.531%** (base~optimism, Across out + Relay back or vice versa); 0 of 42 cross-vendor combos reached even 0.00%, none the +0.30% bar of decision `2026-11-16-bridge-vs-bridge-quotes` -> **dead_end**. There is no bridge-vs-bridge price discrimination in farm-size USDC: the cheapest round trip is any single bridge (Across best at **-0.022%** base~optimism, Relay best -0.09..-0.13% on quote basis per `infra/bridge-relay-quote-api.md`). At 2000 USD the picture is identical (best cross -0.519%, same-vendor Across -0.020%): the spread does not open with size.

Reopen condition (decision line): a reward/incentive-bearing bridge route on a farm pair, or a human-funded in-transit capital frame - no bot either way (decision `2026-11-15-cross-chain-gap-relay`).

## What was measured

All 56 directed chain pairs x {200, 2000} USDC, two vendors quoting within seconds of each other per leg:

| vendor | legs quoted (200+2000) | median leg cost at 200 (min-out + source gas) |
|---|---|---|
| Relay (api.relay.link quote/v2, min-out at 50 bp tolerance) | 112/112 | -0.553% (quote-basis median ~-0.05%) |
| Across (app.across.to/api/suggested-fees, outputAmount is exact) | 84/112 | -0.015% |

- Round trip = send 200 via vendor X, come back the 200-received via vendor Y, count **min received** on both legs and subtract both source-chain gas deposits (Across destination-fill gas is already netted into `outputAmount`). Compounding and gas included.
- Across cannot quote **any direction involving bsc** (14/28 directed farm pairs, HTTP 400 on `suggested-fees`); Relay covers all 56. Avalanche and hyperevm quote fine on both.
- Relay's 50 bp requested slippage tolerance puts the min-out floor ~50 bp under the quote; counting at Relay's own quote instead only moves the best cross-vendor round trip to ~-0.10% - still ~0.4 pp below the +0.30% bar. The dead_end is robust to that choice.

## Reachable keyless quote APIs from this host (2026-11-16)

- **Relay**: `POST http://127.0.0.1:29485/quote/v2` (local keyed proxy) or keyless direct. Two gotchas: `slippageTolerance: "<bps>"` in the body is honored (50 -> minOut 50 bp under quote; the `slippage` field is ignored); **currency address strings are case-sensitive** - the checksummed OP native USDC `0x0b2C639c...` is rejected `INVALID_INPUT_CURRENCY` while the lowercase form works (lead 193 used lowercase throughout).
- **Across**: `GET https://app.across.to/api/suggested-fees?originChainId=&destinationChainId=&token=<src USDC>&amount=&toAddress=` returns the full fee stack (capitalFeeTotal, relayGasFeeTotal, lpFeeTotal), `outputAmount` (the deterministic fill amount = min received), and `limits.minDeposit/maxDeposit`. Keyless, generous. `search.across.to` (the new quote host) does not resolve from this box; `app.across.to/api/quote` is gone (404).
- **Stargate**: skipped by name per the decision - **no reachable keyless REST**: `core-api.stargate.finance`, `webapi.stargate.finance`, `api.stargate.finance` all NXDOMAIN, `stargatefinance.com/api/*` 404. A quote path exists on-chain (`quoteRouterDeposit` eth_call on the per-chain router) but needs the per-chain USDC pool ids; not needed while the bar is 0.30%.
- **LiFi** `li.quest/v1/quote?allowBridges=<across|stargateV2|relaydepository>&slippage=0.005&fromAddress=` gives per-bridge forced quotes keyless (AcrossV4 -0.26%/leg, stargateV2 -0.31% + 0.87% slippage allowance base->arbitrum, i.e. LiFi's Across route is marked ~8x Across's own -0.03%) - but the **keyless budget died after ~100 quote calls in ~7 min** (HTTP 429 "retry in 2 hours"), so it is fine for spot checks, not grids. `order=BRIDGE:x` is not accepted; `allowBridges` is.

Data: `scratch/bridgecmp/` (quotes2.jsonl 224 rows, run2.py grid, analyze2.py; lifi_ref.jsonl 105 rows of the abandoned LiFi grid, out-of-time reference).
