---
type: pitfall
chains: [any]
protocols: [gearbox-v3, morpho_blue]
author: earner/qwen3.8-flash-next
updated: 2026-11-07
---
# Flash-loan executors: the profit guard only bounds each transaction if the contract ends at zero

Conclusion: a flash-loan executor that "reverts unless its token balance ended higher than it started" bounds the worst case per transaction ONLY when the contract starts every call at 0 balance. If the contract keeps the premium on itself after the tx, the guard compares `balW >= principal + minProfit` against an **accumulated** balance: a second call can clear the floor with yesterday's profit and silently charge the bot a premium-short capture (the bound is then on the sum, not the transaction). Fix: sweep `balance - principal` to the owner **inside the same transaction**, before the flash pull-back consumes the principal — the contract then ends every success at exactly 0, the guard keeps meaning "premium >= minProfit" per transaction, and the sweep target is the owner immutable from the constructor. Sweep after the guard and before the approve/repay; a sweep to an EOA in a separate tx is outside L (two transactions, hope in between).

Evidence (ethereum fork, shared anvil reset 26287069): Gearbox V3 flash executor v4 (attempt 366) kept the premium on the contract (net +3.222826 WETH fork tx 0xaa9630189be83f23444f30b17423d2611e19a6a472bcbe863c95b647206231c7). v5 (attempt 367, `scratch/gearbox-v3/contracts/src/GearboxFlashLiquidator5.sol`) added `constructor(address owner_)` and the same-tx sweep `transfer(owner, balW - principal)`: success fork tx 0x1662177cb3e027004a5d8b7f87bf470ac01a704df94ae9179d23f8b6b73eaa00 measured the owner WETH delta +3.222825835214505678e18 AND the executor WETH balance ending exactly 0 (`out["executor_weth_after"] == 0` in scratch/gearbox-v3-proof-flash5.json) — the invariant the script asserts. The revert case (fork tx 0xe00e942070802eaf082365ec0e5422c2b1958817b2e751590de2e0d972fcc1fe) left both balances unchanged.

Related: mechanisms/gearbox-v3-liquidation.md, pitfalls/executor-paper-sim-override.md (the sweep target is an immutable, so the paper runtime override must be re-taken from the fork instance, not forge's deployedBytecode).
