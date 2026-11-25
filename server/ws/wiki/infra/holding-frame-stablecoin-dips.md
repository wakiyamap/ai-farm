---
type: infra
chains: [any, hyperevm, ethereum]
protocols: [felix_cdp, openeden, usdd, falcon_finance]
author: researcher/opus
updated: 2026-11-16
---
# Holding frame: buying stablecoin dips pays under 0.25 USD/day at the 100 USD cap

**Conclusion (2026-11-16, researcher run 0399ba8d, attempts:1435).** Buy a stablecoin with USDC when it trades at or below 0.995, then sell it back at 0.999 or after 7 days. Over 30 to 67 days this earned at most **6.75 USD per 100 USD** in 30 days (feUSD), that is **~0.22 USD/day at the frame's 100 USD cap**. That figure comes before two pool fees and before checking that a pool exit exists at that price. Every other stablecoin earned less, or never dipped. The type is not worth building inside the holding frame (`decisions/human/2026-11-15-holding-frame.md`). Look elsewhere for holding candidates.

## Numbers

Source: DefiLlama `coins.llama.fi/chart` (market aggregate, not a pool quote). Script `scratch/r0399-stables.py`, series in `scratch/r0399-stables-series.json`. Arguments: coingecko ids, start ts, entry, exit, period.

| Stablecoin (chain where farm could hold it) | 30 d @2 h: trades, gross per 100 USD | ~67 d @6 h | Pattern |
|---|---|---|---|
| feUSD (hyperevm, Felix) | 7, +6.75 | 3, +4.67 | dips to 0.993-0.995, back to 0.9995 in 2-38 h |
| USDO (OpenEden, ethereum) | 3, +1.48 | 7, +3.55 | 0.977-0.991 dips, multi-day |
| USDD | 1, +2.61 | 0 | single 0.9737 print on 10-27 |
| rUSD (Reservoir) | 1, +1.07 | 1, +0.47 | single dip |
| USDf (Falcon) | 4, -0.02 | 5, +0.31 | standing 0.990-0.995 discount, not a dip (lead 188) |
| bUSD0 (Usual) | 4, +0.24 | n/a | standing 0.976 discount |
| USDe, GHO, frxUSD, USD0, PYUSD, RLUSD, USDai, USDtb, USDS, USD1, USDG, mUSD, fxUSD, AUSD, FDUSD, crvUSD | 0 | 0 | never at or below 0.995 (minimum 0.9945-0.9997) |

USR (0.03) and USDX (0.007) collapsed for good during the window. Those are the losses the frame's stop has to cut.

## Why the edge is small

Redemption or PSM paths pin the floor: Felix redemptions (attempts 961/1253) and GHO GSM (lead 189). A dip deeper than the redemption fee is closed by redeemers, so a holder only gets the 0.3-0.6% band. That is 0.3-0.6 USD per trade on 100 USD.

## Reopen if

A farm-chain stablecoin with a deep USDC pool shows repeated dips of at least 1% that recover within 7 days. Re-run the script with entry 0.99 and check a real pool exit quote at the dip time before anything else.
