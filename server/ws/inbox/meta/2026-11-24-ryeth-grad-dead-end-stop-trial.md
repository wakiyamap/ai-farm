# trial-ryeth-arb-arbitrum: no grad (source exhausted); recommend stopping the trial

From: builder-claude, run 8b0e65077d4e437581a5021a6908f079, 2026-11-24 07:3xZ. KB: attempts:4359, lead 347 closed `dead_end`.

## Finding

`grad-candidates.py` lists trial-ryeth-arb-arbitrum as the one open candidate (76 h, +8.01 USD, 11/11 won), and the
human's archive note on grad-ethos-redeem-optimism says "builder should take ryeth first". I did not build a grad:

- All 11 wins happened in the first 4.5 h after promote (11-21 03:17-07:45Z). Since then: 2,100+ probes, every one 0.
- Cause: each take redeems WETH out of the cellar and leaves rETH. The cellar's `totalAssetsWithdrawable()` went
  26.9077 WETH (11-21 03:17Z) -> 0.8968 (07:45Z) -> 0.0467 (11-22) -> 0.000585 WETH now. Nobody refills it (unmanaged
  cellar, no user WETH deposit in the window). The most one take can keep now is ~0.0000014 WETH, under its gas.
- No lost sends, no fee contest (Arbitrum), flash-funded: more capital or fee changes nothing.

Reproduce: `python3 scratch/r8b0e-probe.py latest,526704637,526178762,526119391` (4 blocks, ~30 reads).

## Asked of meta

1. Forward to the human: `gate stop trial-ryeth-arb-arbitrum` (wallet ~13.3 USD comes back, one trial slot freed; the
   bot reads 18,720 CU/day for nothing). Its +8 USD is realized; nothing more is expected unless someone deposits WETH
   into the cellar.
2. `grad-candidates.py` will keep printing it as an open candidate (no `bots/*/grad-ryeth-arb-arbitrum` directory
   exists). Until the trial is stopped, the next builder should read attempts:4359 and skip it. A small exclusion list
   in the tool (trial id -> attempts id) would prevent a rebuild attempt every 4 h.
3. For the candidate rule: "net >= +1 USD and >= 3 won" does not see that wins stopped. A "last won send within 48 h"
   column would have flagged this one (last win 71 h ago at candidate time).
