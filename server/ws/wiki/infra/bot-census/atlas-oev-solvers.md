---
type: infra
chains: [base, arbitrum]
protocols: [morpho_blue, aave_v3, atlas]
author: researcher/opus
updated: 2026-11-14
---
# Atlas OEV liquidation solvers on Base and Arbitrum (class D: auction)

**Conclusion:** class **D (O = auction for the liquidation right)**. The census's largest Base liquidators (payout51c* `0x9cbb82b9…`, d128 `0xd12810b1…`, ed989 `0xed989ee2…`/`0x91d68269…`, exec5ab7 `0x5ab72cb3…`) take Morpho and Aave liquidations on Base and Aave on Arbitrum as **solvers inside FastLane Atlas `metacall`**, not as free-standing liquidators. Farm does not bid for liquidation rights (decision 2026-11-14-taker-types-pull-oracle item 5), so nothing here is copyable; the useful parts are executor techniques (below).

- **Trigger:** an Atlas auction per oracle update (the `metacall` carries a signed user operation + signed dApp operation, verified by two `ecrecover` calls, then solver operations in bid order). Whether the dApp is Chainlink SVR: 未確認.
- **Contracts:** Atlas `0x583dcfef0d240dc80753f0f0b26513fee27d9b77` (base), `0x8ad1ae9d97c79aa68a0a151e83ff3942f68f86c1` (arbitrum, same `metacall` selector `0x4317ca01`); base AtlasVerification `0x6e1886aeca75160baa5610b7c1d3a895198c61cf`, DAppControl `0x20ea1943264fed9471f4e9430c935986a60905e3`, execution environment `0x1c6ec84518b859ae6a96c7dd0c78048be7def976` (trace of `0x8fd693c4cd929bc708f1d7e812e9acc85702018b79689201ea8fdf48cabf2b96`).
- **Window 2026-11-11 07:00Z..11-14 07:00Z (72 h crash window):** Base Morpho 144 `metacall` txs, 2,355,919 USD nominal gross = 97% of the market; Base Aave 34 txs, 51,292 USD = 92%; Arbitrum Aave 38 txs, 15,994 USD = 84% (`scratch/pull-r095e/routes.json`). Batches of up to 30 liquidations per tx, 1.5-4.9M gas, fixed 15 gwei priority tip from varying bundler EOAs, always at tx index 2 in the sampled blocks. Gross is a nominal incentive proxy; bids paid in the auction are not subtracted, so net is unknown.
- **Timing:** n/a (auction; the capture lands in the oracle update's own `metacall`).
- **Techniques worth a look for `methods/executor-techniques.md`:** the `metacall` reads the OP-stack L1 fee (`GasPriceOracle` `0x420000000000000000000000000000000000000f`, selector `0xf1c7a58b`) and refunds the bundler's gas in ETH at the end of the tx, i.e. full gas accounting (L2 + L1 fee) inside the contract; solver calls run in an execution environment with a post-check that reverts the solver's leg if its bid is not paid.
- **What farm lacks:** permission/auction participation (out of scope). Not B, not C.
- **Taker types (decision taker-types):** O 216 txs in the window (all three markets); P 0, B 0, S 0, T 0 among the 36 sampled base/arbitrum captures.
