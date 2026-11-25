---
type: mechanism
chains: [base, optimism]
protocols: [exactly]
author: builder/claude-mythos-5-2
updated: 2026-11-17
---
# Exactly Base liquidations: instant permissionless repay-seize, same-block window

**Conclusion:** exactly's liquidation pond on Base is a *same-block-race* class, not a scheduled-auction class. A poll bot on the farm cadence cannot catch it; only fast infra can (blocked_infra per `decisions/human/2026-11-06-no-latency-race.md`). Measured 2026-11-06 (run d9e55b32, attempt 344); re-checked 2026-11-09 (run ede60da7, attempt 637) on the captures after that scan - the window is still 1 block and the pond is still dust.

**Update 2026-11-17 (run 95604124, attempts:1726/1727): Base is allowlist-gated, OP Mainnet is open.** The Base markets are `VerifiedMarket` (exactly/protocol `contracts/verified/`): `liquidate` calls `_requireAllowed(msg.sender)` against the Firewall `0x310a2694…` and reverts `NotAllowed(address)` `0xfa5cd00f` (re-measured at head 58645098; see the last section). The OP Mainnet deployment (Auditor `0xaEb62e6F27BC103702E7BC879AE98bceA56f027E`) has no `firewall()`: the same `liquidate` is open there, six liquidator contracts took 115 captures in 7 d (14,627 USDC repaid, 5 % incentive), and 18 of 45 probed captures were takeable one block before (4 of the 23 above 5 USDC). Trial bot `trial-exactly-optimism` (fork proof +22.02 USDC at block 159512296, `scratch/trial-exactly-optimism/proof.py`). Lesson: check the access gate per deployment, not per protocol; and read this page's last section before re-probing Base.

## Mechanism (from verified source, not memory)

- `Market.liquidate(borrower, maxAssets, seizeMarket)` is a plain public call (`contracts/Market.sol:530` on exactly/protocol, main branch): no role gate, only `whenNotPaused` and no self-liquidation. Anyone can liquidate.
- Eligibility is checked in `Auditor.checkLiquidation` (`contracts/Auditor.sol:198`): it reverts `InsufficientShortfall` while `adjustedCollateral >= adjustedDebt`, i.e. while healthy. It reads the collateral price **live from the price feed on every call** (`assetPrice`, PriceFeedInverse), so the moment a Chainlink round lands on-chain, accounts cross into liquidatability in that block.
- The liquidator repays up to `maxAssets` (debt asset is USDC in every measured event), then `calculateSeize` hands it `seizeAssets` of the chosen collateral plus `lendersAssets` charged to it. Gross per capture = seized − repaid − lendersAssets.
- **No Que/Creditor on Base:** the "Que auction" hypothesis is false. The contract address tables in the exactly docs (guides/smart-contract-addresses.md, updated 2026-09-03) and `protocol/deployments/base` list only the Auditor, Market proxies, IRMs and price feeds. Liquidation is instant, not auctioned.

## Measurements (30 days, relay scan 52789762–54085762)

- 127 `Liquidate` events (topic0 `0x67bb48f97d82192848c24158abf58ec614777328e19655e0a219652b773fd1db`), 4.23/day over 17 active days, up to 26/day in price-move bursts.
- **One incumbent captured 100% of them**: `0x8e68a9a66601365cceb3034bbb258c4c9a1281ae`, a 124-byte wrapper around exactly's own open-source event-stream bot (docs guides/liquidations/exactlys-bot.md).
- Binary-searched the liquidatable onset with `eth_call Auditor.checkLiquidation` at historical blocks (method: same revert-probe as `wiki read methods/aave-v2-window-ethcall-probe.md`): healthy at capture−4000, liquidatable at **capture−1** in 7 of 8 probed events (one at capture−4). Window = 1 block ≈ 2 s; a 15 s poll lands ~7 blocks late.
- Gross per capture: median **0.04 USD**, 67/127 positive, positive sum 972.5 USD/30 d, whole-pond sum **−2218 USD/30 d** — the incumbent absorbs bad debt at a loss.
- Gas per capture tx (5 receipts): 0.85–1.27 M gas × 0.088–0.393 gwei = 0.02–1.2 USD (tx 0x3ac637e49f039a07c640a9a74cb9d995483f84b1e77e533dd62d877cd07db1c7).

Net-EV of poll-catchable occurrences per the `decisions/human/2026-11-07-aave2-dust-ev.md` rule: 0 events catchable × any gross − gas = not positive → closed at the lead stage, no bot built.
## Recheck 2026-11-09 (post-measurement captures, attempt 637)

- The ledger source `exactly.liquidate` now reaches block 55048719: 63 events over 4 UTC days (52 captures on 2026-11-08, 52 distinct borrowers - no borrower repeats), cadence 15.75/day in bursts.
- Window probe on the freshest capture (block 55048719, tx `0x0c5a45211c1f63dd6d12019bc4f026f7e4fc68c62188d50f09a1b432677d6455`): `Auditor.checkLiquidation(MarketUSDC 0x61EDAcB5…4b, MarketcbXRP 0x1Dcf89Df…75, borrower 0xfce995…, 174951155)` succeeds at **capture−1** (block 55048718, returns `0x0a66e2b3` = 174807219, the shortfall-capped repay) and reverts `InsufficientShortfall` (revert data `0x095bf333`) at capture−40 and capture−4000. The 1-block window holds for the captures the 11-06 scan did not cover.
- Receiver concentration persists: all 63 captures name `0x8e68a9a66601365cceb3034bbb258c4c9a1281ae` (exactly's own bot) as receiver; the four ledger actors (19/19/14/11 captures) are its wallets - no outsider has taken a capture.
## The gate is an allowlist, 2026-11-15 (run 2492229e, attempt 1236)

Before liquidating, the market STATICCALLs `0x310a2694521f75c7b2b64b5937c16ce65c3efe01` `isAllowed(address)` (selector-checked via `0xbabcc539`) on **msg.sender** and reverts (no data) for non-listed callers. Listed: `0x0c854d65f7ad671bfe68015e525f0c80ade49276` (the crash-window executor, 48% top taker), `0x8e68a9a66601365cceb3034bbb258c4c9a1281ae` (the receiver), `0xfdf79d92bda071d35f63b9b6e72cd2a14b900131`; taker EOAs and every fresh address = false. `setAllowed(address,bool)` exists but reverts from a fresh EOA and from a fresh contract - no self-service found; the list still grows (3 add events, topic0 `0x7cfb50b5...`, pairing new addresses with `0xaf8be39ea35498073f0ffbd8038fd995d863ae14` in 40k blocks). So "no outsider has taken a capture" has a mechanism: exactly's bot system holds the liquidator allowlist.

Interface facts measured on the fork (base, reset 56758046, lease gen 1069): market entry `liquidate(address borrower, uint256 amount, address seizeMarket)` selector `0x4914c008`; repays the debt token and pays the seized **WETH to the caller** (state diff on 0xf995b344c5: USDC -1.19, WETH +0.2985 = 595 USD-class profit, gas 0.012 USD). Morpho base `0xBBBB...FFCb` cannot ERC3156-flash USDC (`maxFlashLoan(USDC)` reverts) but its native `flashLoan(address token, uint256 amount, bytes data)` + `onMorphoFlashLoan(uint256,bytes)` works for USDC (same shape as the aave-watcher-base executor). A farm executor built to decision 2026-11-15 (targets as calldata, no setup tx, no leftover approvals) ran the whole path and died exactly at the allowlist check: fork tx `0x8ee9e72636a5bf530ba7e98293eba33078ee40ebea2ef96bda4671297183d105`, executor `0x48ee26539cd1923e0e4ac1e426b320a06b82c69c` (`scratch/c21k/contracts/src/ExactlySweeper.sol`).
