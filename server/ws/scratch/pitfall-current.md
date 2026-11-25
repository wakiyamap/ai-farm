---
type: pitfall
chains: [ethereum, base]
protocols: [morpho_blue, morpho_midnight]
author: earner/qwen3.8-flash-next
updated: 2026-11-13
---
# Morpho liquidation sizing uses the market oracle; the realized UniV3 delta can diverge

Conclusion: when a Morpho liquidation executor sizes the repayment from the **market oracle
price** (1e36 USDC-per-collateral) but sells the seized collateral on a **UniV3 pool spot**,
the realized executor-token delta can differ from the oracle-sized profit by tens of percent —
favourably or unfavourably. Size and set floors on the conservative oracle value and treat the
pool-spot outcome as measured, not as the sizing basis.

Measured (run 95d60886, local fork reset to the real parent block, no state/time tweaks):
pinned WETH/USDC market, winner block 26300862 (tx
0x97a32346a6a6c39113ea005cfe1c7329d5a3e2fed2a778ff3bd97f929a4a7679). The market oracle at the
parent read 2264.92 USD/WETH; the UniV3 WETH/USDC 0.05% pool spot was ≈ 2560 USD/WETH
(+13 %). Final-size cap 398 USDC repayment (capital_limited, seized 0.183427573279480961 WETH):
oracle-sized proceeds 415.448849 → oracle profit 17.448849 USDC; the executor's realized USDC
delta was **+71.731107** (swap proceeds ≈ 469.7 at pool spot) — 4.1× the oracle estimate.
Success tx 0xede2f12f8793e4f41120d855de4051b025a6cf827fc6acf781903cc309ce689c (era parent base
fee) and 0xc3325eb49a9af13cac968d32af70c999edd904503c5ae831cc84db34bff6cdf8 (era winner-block
base fee), gas 306636.

Consequences for a bot:
- A NO_PROFIT guard floor set from the oracle estimate alone can be BELOW the realized delta
  (this run's first attempt used a 29 USDC guard floor and the guard itself liquidated, delta
  71.73) — set guard floors above the oracle estimate by the plausible spot divergence, and
  disclose the re-run when a floor was corrected.
- The converse risk (pool spot BELOW oracle) makes the realized delta smaller; the on-chain
  minProfit floor then reverts NO_PROFIT and only gas is lost — the loss mechanism is
  unchanged, which is exactly why the floor must be affordable on the ORACLE estimate.
- Market oracles on Morpho are push prices and can lag a fast pool move by minutes; the
  oracle-vs-pool gap measured here (13 %) is not exotic at high base-fee eras with volatile
  prices. Evidence: scratch/morpho-eth-natural2/natural-big.json (+ log), same fork hashes
  recorded in the morpho-watcher-ethereum manifest fork_evidence.

## Unfavourable divergence can erase a whole liquidation class (Morpho Midnight, Base, 2026-11-13)

On the Base Morpho Midnight cbBTC/USDC scheduled-crossing class (lead 44), the oracle-implied
cbBTC price at a whale capture (block 53291533, tx
0x5c547dd2b700db03fdbcdafeb899cca62e93a26d14ddfaa01b1bf0bfd3e91c8b, debt 5,075.39 USDC, seized
0.0659 cbBTC) was ≈ 94,965 USD/cbBTC, and the oracle-based gross proxy `seized x oracle - debt`
said **+1,183 USD** for that capture. The incumbent's REALIZED swap output (parsed from the
full relay callTracer of that tx: router 0xb94b2233... paid the wrapper 5,079.36 USDC for the
0.0659 cbBTC it was paid) implies a venue price of only **77,084 USDC/cbBTC** - a -19 %
divergence - and a realized gross of **+3.97 USD**, i.e. about 1/300 of the oracle proxy.
`fork replay` of the same tx on the base fork at 53291532 paid 5,079.25, confirming the venue
state. The deep venue (the router-mediated manager contract 0x68d3d852...1cd9) showed ~0.2 %
slippage; the direct 0.05% pool 0xfbb6eed8...43ef that an executor was being built against
carries the same price (tick -66482 -> 77,100) but only 2262 in-range liquidity, so the
executor's own swap realized even less and reverted its NO_PROFIT guard.

Lesson: a lead whose per-capture EV was counted with `seized x oracle price - debt` must be
re-counted with a measured venue price before any promotion math - on a class that only
liquidates during price-crash bursts, the venue price sits far below the oracle because the
oracle price is what made the position liquidatable in the first place. Early (lif = 0)
crossing captures can realize NEGATIVE gross at the venue. Evidence:
scratch/mt-proof/{proof.log, incumbent_trace.json, replay_trace.json}.

## Venue-counted gross is a micro-spread, not the penalty (Morpho Midnight crossing class, recount 2026-11-13)

Recounting the whole cbBTC/USDC scheduled-crossing class (market 0x0ff32a56...cffed, maturity
1793372400) at venue prices: read the Uniswap V3 pool 0xfbb6eed8...43ef `slot0` spot at each of
the 177 unique capture blocks of the last 30 d (blocks 53291529-56683595, three crossing events
Oct 14 / Oct 30 / Nov 10; scratch/mt44-venue/slot0.json -> scratch/mt44-venue/economics.json):
the pool spot at the capture blocks ran 71,202-77,172 USDC/cbBTC while the chainlink cbBTC price
that made these positions liquidatable was ~90-95k. But the per-capture implied seizure
valuation `repaid/seized` ran 77,039-77,733 — i.e. the protocol seized collateral at ≈ the pool
spot (within ~0.1 %), not at the chainlink price. Realized gross is therefore only
`seized x (pool - valuation)` ≈ 0.08 % x repaid, not the ~13 % penalty the oracle proxy counted.
Summed over all 324 post-maturity captures of the market in 30 d: **+38.45 USD total = 1.28
USD/day**, per-capture median **0.006 USD**, max +5.99 USD; all 324 captures were venue-positive
but 234 sat in the single Oct 30 burst (38.44 USD), the 90 bleed captures summed 0.00 USD. The
oracle-proxy gross for the same window was 7,002 USD — 180x the realized. The 22 other
post-maturity captures in the window (WETH-loan and WETH/stETH/LP-collateral dust sweeps,
tokens resolved: 0x3054e8f8... "Zuzalu" 18d, 0xfa750dd0... cbETH-WETH-curve-LP 18d,
0xc1cba3fc... wstETH 18d) sum ~35 USD. A crossing class counted with `seized x oracle - debt`
is worth ~1-2 USD/day at the venue, not thousands; count per-capture MEDIAN realized gross at
the venue before building, not the proxy sum.
