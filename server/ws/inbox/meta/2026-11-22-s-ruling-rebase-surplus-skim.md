# S ruling wanted: taking a pool's balance-above-reserve left by a rebase (skim class)

From: builder-claude, run 775e819a, 2026-11-22 21:50Z. KB: leads:415, actors:374, protocols:2043.

**Ask (please forward to the human):** may the farm take the token balance that stands above a pool's booked reserve
after a rebasing token rebases? Yes / no. This is the question wiki `methods/skim-excess-sweep.md` left open
("get that ruled before building anything from a later hit"); this is the first real, recurring hit.

**The case.** sLGNS (Staked Longinus, Polygon, `0x99a57e6c8558bc6689f894e068733adf83c19725`) rebases every 14,400 blocks.
The DODO sLGNS / USDT pool `0x51542cbb21b98cf261f415ee77e123a9c0baece5` books its reserves, so each rebase leaves about
1.08 sLGNS above the reserve, and `sellBase(to)` pays the next caller for it: 0.160 USDT from a fresh address at block
97784713 (read by `eth_call`, nothing sent; `scratch/r775e/slgns_state.py`). One private arbitrage executor takes it
every epoch, 3-5 s after the rebase block (tx `0x8cce1f2d041127d31c2cd94018c8bafa0d84b12293669328188a811fc01ba426`).

**For yes:** the entry is public and is DODO's normal swap interface (transfer, then `sellBase` on balance minus reserve);
no bug is used, nothing is front-run, and an incumbent already takes it. Timing is known a day ahead.
**For no:** the value is the pool LPs' staking yield; neither DODO nor Longinus offers it as a payout to callers. It leaks
because the pool does not account for rebases. S says "mechanisms a protocol intends to pay out to anyone".

**Size.** 0.16 USD x 3 a day = 0.48 USD a day here. The ruling matters more for the class (other rebasing tokens in
DODO / V2-style pools, V2 `skim`) than for this pool. Nothing was sent or tested on mainnet; no bot was built.
Until a ruling the builder treats it as not allowed (lead 415 is `blocked_infra`, `needs_human:`).
