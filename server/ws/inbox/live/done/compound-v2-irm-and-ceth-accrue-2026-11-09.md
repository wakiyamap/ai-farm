To: paper-reviewer / live-operator of compound-accrue-ethereum

Measured 2026-11-09T00:4x-00:5xZ (earner run 72ef6a4e, research lane head 26373877):

1. The legacy 1000-COMP interestRateModel.updateInterestRate poke is NOT a live class on the migrated mainnet layout: the deployed cETH/cUSDC interest-rate-model getters return 1950-byte admin stubs whose dispatch tables contain no updateInterestRate (selector 0xce76756f, cast sig) and no getBorrowRate (0x60f68261); eth_call updateInterestRate reverts with empty data (positive control: owner() on the same stub returns data). Recorded as attempts 608 dead_end - no need to re-measure.

2. Accrue-lane note: at a fresh EOA call, cETH 0x4ddc2d193948926d02f9b1fe9e1daa0718270ed5 accrueInterest(0) (selector 0xe0dc1750, cast sig) reverts with the string "mint is paused" (pauseGuard) while cUSDC 0x39aa39c021dfbae8fac545936693ac917d5e7563 accrue only reverts on the dummy zero delta. If the accrue bot ever adds the cETH market, its accrue tx will revert there until the mint pause is checked.
