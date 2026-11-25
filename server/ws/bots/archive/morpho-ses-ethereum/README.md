# morpho-ses-ethereum

Metronome sES pinned market on Morpho Blue (ethereum): atomic liquidation
bot, new id per decision 2026-11-12 item 3.

## Mechanism

Morpho sES market `0xd2630c0e...` (loan sES `0x64351fc9...`, collateral
nETHMAX `0x657d9aba...`, adapter oracle `0xc28f86c8...`, llTV 96.8853% =
seize bonus 6.693%). When the sES/nETHMAX price falls, borrowers go
underwater and anyone can liquidate: the executor flash-loans the sES
(debt repayment amount) free from Morpho, calls `liquidate` (seize capped at
0.04 sES repay per tx = ~150 USD at the measured sES price ≈ 1.0999 sES per
nETHMAX ≈ 3800 USD/sES), sells the seized nETHMAX back to sES through the
two measured Metronome exchange contracts, reverts unless the sES surplus
after the flash repay covers `minProfit`, then sells that surplus back to
WETH, withdraws to native and pays the whole native profit to the bot
wallet in the SAME transaction (worst case = gas only, ≤ 460000 gas ≈ 0.25
USD).

Two-leg swap rate as numbers (measured, no single pool sells nETHMAX or
WETH for sES directly):

* leg 1 — MAX exchange `0xd65ed4bc...`: nETHMAX → WETH at ≈ 1.00 WETH per
  nETHMAX (both ETH-pegged 18-dec; the adapter price 1099888124080827723e18
  = 1.099888 sES per nETHMAX prices the pair against sES);
* leg 2 — sES exchange `0xa4c567c6...`: WETH → sES at ≈ 1.099888 sES per
  WETH (the same adapter price — measured 1e36-scale from `price()` at
  block tags 26353673..26354499, static across the capture blocks);
* end to end value: the whale capture seized 47.7577 nETHMAX and repaid
  51.1887 sES = 1.0718 sES per nETHMAX seized (llTV bonus included,
  measured from the Liquidate events); the executor's exit legs carry
  slippage-bounded minOuts (7/8 of input on leg 1).

## Capture windows (all 10 measured captures, scratch/ses-window/ses-window2.json)

Every capture is CATCHABLE at C-1 (eligible one block before the capture
block — the speed test passes for any poll ≤ the window; decision item 2:
no same-block-race captures count against EV).

| capture block | repaid sES | time-to-capture (window) |
|---|---|---|
| 26342363 | 0.3021 | ≥ 1 block (unhealthy at C-1) |
| 26350419 | 2.1182 | ≥ 8192 blocks (~23 h whale window; binary search back to k=8192 never healthy) |
| 26350420 | 0.6495 | ≥ 1 block |
| 26350420 | 0.4654 | ≥ 1 block |
| 26350422 | 0.4045 | ≥ 1 block |
| 26350423 | 0.0385 | ≥ 1 block |
| 26353519 | 0.0214 | ≥ 1 block |
| 26353520 | 0.1521 | ≥ 1 block |
| 26353674 | 51.1887 | ≥ 8192 blocks (~23 h whale window) |
| 26353682 | 23.0999 | ≥ 1 block (captured 8 blocks after the previous capture of the same whale) |

EV scale: the ledger holds 12 captures 26317645→26353682 (~7d); the two
whale captures 2026-12-15 repaid 51.19 + 23.10 sES in one day ≈ 74 sES
gross repay volume; at the ~2.6% seize margin (measured repaid vs proceeds)
that is ~1.9 sES gross ≈ 7.3k... ≈ **the "≈36 USD/day" figure stays
PROVISIONAL until the fork proof lands the executor's own realized
surplus** — per capture the bot nets ~0.5–2.6% of its own 0.04 sES repay
cap (~0.001 sES ≈ 4 USD gross, gas ~0.25 USD).

## Scan and cost

Heartbeat 60 s: one `eth_getLogs` (Morpho position-changing topics) plus
one multicall aggregate (market totals + adapter price + tracked
borrowers' positions), ~8 reads/min ≈ 120 k CU/day (well under the 1M CU
threshold; ≈ 0.06 USD/day at 100 USD/M CU). Attempt band: tries while
strength/debt < 1.05 — Morpho's debt includes the accrued-interest
component the shares formula omits (the whale capture was liquidatable at
C-1 with shares-formula HF 1.0391, measured at the C-1 state), so a 1.00
band would skip exactly the captures the incumbents took; the executor
itself (Morpho NOT_HEALTHY) is the final authority.

Paper mode simulates `liquidate` via `eth_call` against the executor
address with `executor-runtime.hex` (eth_getCode of the fork deployment,
re-take after every source change) as the code override; live mode sends
the same calldata through the signer to `$EXECUTOR_ADDR`.
