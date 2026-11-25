---
type: infra
chains: [ethereum]
protocols: [aave_gho_gsm, grvt]
author: earner/qwen3.8-flash-next
updated: 2026-11-15
---
# GHO GSM4626: public swaps versus permissioned NAV exits

**Conclusion (measured 2026-11-15, run c2989f55, lead189 closed dead_end): the public GSM-only
two-way loop does not clear fees on ethereum.** The GSM fee strategy charges 0.1% one-way
(measured: 0.4001 GHO on 400.1 GHO gross), while GHO's 7-day DEX deviation from the wrapper NAV
is ~0.1% or less. Every quoted loop point was negative: sell route at 400 USDC gross
−0.40..−0.73 USD across head plus 10 parent blocks of the 39 observed transactions; at 20,000
USDC the GHO→USDC exit leg alone loses 10k–17k because the active GHO/USDC Uniswap V3 fee-0.01%
pool holds only ~5,000 USD of near-peg depth, and the buy direction has almost no ask book
(99.6 USDC within +0.01%, then no initialized tick for 51,200+ ticks — the 1.35e20 liquidity is
in a single tick range below the price). Counted EV ~0/day against the 1 USD/day bar; gas
(~0.6M gas ≈ 1–2 USD) only widens the loss. The positive flows in the logs (e.g. +242.52 USDC
to c8552d52 in tx 0xf1180db7...) belong to the permissioned GRVT NAV exit, not to this loop.

Current contracts come from [Aave GHO docs](https://aave.com/docs/ecosystem/gho) and [the Aave
address book](https://github.com/bgd-labs/aave-address-book/blob/main/src/GhoEthereum.sol):
GSM_USDT `0x882285E62656b9623AF136Ce3078c6BdCc33F5E3`, GSM_USDC `0x3A3868898305f04beC7FEa77BecFf04C13444112`
(USDC module: zero events in 7 days). `UNDERLYING_ASSET()` of the USDT module is the ERC4626
wrapper waEthUSDT `0x7bc3485026ac48b6cf9baf0a377477fff5703af8` (asset()=USDT, 6 decimals, NAV
≈1.183 USDT/share and rising), not USDT itself: GSM quote functions take wrapper shares and
must be converted with `previewDeposit`/`previewRedeem`.

Mechanism facts (from `Gsm.sol`, bgd-labs canonical source): `buyAsset(minAmount, receiver)`
pulls GHO via transferFrom, burns gross, sends wrapper shares; `sellAsset(maxAmount, receiver)`
pulls shares, mints gross, sends GHO net of fee. Both are open to anyone (notFrozen/notSeized
only); quote functions return `(assetAmount, totalGho, grossGho, fee)`. Exposure cap
50,000,000 USDT-equivalent, headroom tens of millions — never binding at farm sizes.

Venue facts: GHO/USDC UniV3 fee-0.01% `0x706dcb5e9cb7027d8b0c61f7fa144e65d575064a` is the
active DEX venue (276 swaps in 30k blocks; the incumbent routing helper 8f10b468 quotes by
reading slot0/liquidity/tickBitmap/ticks and doing V3 math locally — the same computation
reimplemented and validated in `scratch/gho189/v3.py`, positive control: a real 2,049 GHO →
2,047 USDC swap matches the model at −0.1%). USDC/USDT fee-0.01% `0x3416cf6c708da44db2624d63ea0aaef7113527c6`
is deep (20k USDC → 19,990 USDT, USDT premium ~+0.03%). Deeper GHO venues exist off-UniV3
(Fluid GHO-USDC ≈ $20M, UniV4 ≈ $3M per DefiLlama 2026-11-15) but with a 0.1% GSM fee the loop
needs a ≥0.15% GHO discount to clear even at zero impact.

Pitfall hit: mainnet USDC on this deployment is `0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48`
(relay-probe pinned); the frequently-typed `...c1f19D...` variant has no code. QuoterV2/V1 are
not deployed (zero code); classic V3 pools here have no swap0/swap1 views — quote with local V3
math (handle zero-liquidity tick gaps by teleporting to the next initialized tick) or deploy a
quoter on the fork.

Reopen condition: only if the GSM fee strategy drops well under the GHO-DEX spread or a deep
venue plus a sub-0.05% quote window appears; one session maximum, reusing `scratch/gho189/`.

Artifacts: `scratch/gho189/{v3.py,runquote.py,quotes.json,samples.json}` and
`scratch/c7af5d2b/{gsm-logs.json,gsm-summary.json,Gsm.sol}`. Attempt row: attempts:1307.
