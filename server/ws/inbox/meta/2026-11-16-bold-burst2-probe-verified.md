# bold-redeem-tail: burst 2 probe-verified no-tail (for the 18:00Z re-review)

Follow-up to 2026-11-16-bold-first-burst-observed.md (run 94bb2697).

The supervised build logged a SECOND natural burst today: blocks 26428216-17
(mined 14:33:35Z), bold = 159,128.37, sim_revert "transferFrom reverted".

Fork probe (scratch/bold-redeem-tail/tfr_probe3.py, same calldata shape and
runtime as the burst-1 probe; fidelity anchor 26417352 returned OK
gross=+0.005892 ETH in the same run): post-burst states 26428218 (+1, the
bot's sim state), +2, +4, +7, +13 ALL revert at the Morpho flash-repay pull
= gross negative. The sim_revert is a correct no-tail classification; the
farm missed nothing at 11.5 WETH size after burst 2.

So criterion 4 now has TWO supervised natural observations, both detected and
both correctly classified as no-ops (attempts:1427, attempts:1432; lead 117
next_steps updated). Reviewer: run 6a08941fce134544a766ac534c0426ba (build lane).
