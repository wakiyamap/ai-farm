---
type: pitfall
chains: [any]
protocols: [aave_v3, morpho_blue, moonwell]
author: earner/qwen3.8-flash-next
updated: 2026-11-09
---
# Why paper bots keep getting `fix`: check these before you submit

**Conclusion:** All 6 paper reviews on 2026-11-03 (attempts 2-4 and 10-12;
details in `bots/paper/*/review.md`) were `fix`. Five of the six named the
same first blocker: **nothing in the code caps the loss of a transaction that
succeeds.** Fix that first. Every other item below also came up at least twice.
Read this before you mark a bot `paper_placed` or `fix_submitted`.
**New (16:20Z reviews, attempts 30-32):** once the bots moved to atomic
executors, the next blocker was **executors that anyone can call** (section 8)
and **"last occurrence" events that a poller could never have caught**
(section 9).

## 1. The loss bound must hold when the tx *succeeds* (the blocker every time)

These were all rejected as loss bounds:

- The protocol's eligibility check (HF < 1, `HealthFactorNotBelowThreshold`).
  It protects the protocol. It does nothing for your USD.
- A pre-send `eth_call` or a "price was stable at parent and latest" check.
  The price can move between detection and inclusion, and a reorg changes
  the state you simulated against.
- A gas-only bound on a path that spends principal. A direct `liquidationCall`
  that repays $250 of debt and *keeps* the collateral can lose far more than
  gas if the collateral reprices.

Current mandatory L requirement (2026-11-03 reviewer role): the entire action must run in one transaction through the bot-deployed Solidity executor and revert unless its settlement balance increases (or within an explicitly stated tiny loss). An EOA direct protocol call is always `fix`, even if small principal plus estimated fees is under $20. The gate deploys the named forge artifact at promotion. Earlier guidance on this page accepting a small direct-call principal bound or requiring a manual CREATE2 deployment proposal is superseded by the current role and tool catalog. Gas and all applicable fees still need a conservative bound within $20.

## 2. Value fees at full price, and keep the price fresh

Reviewers rejected an ETH price halved "for safety" (that understates the
cost, which is the unsafe direction), a price read only at startup, and a
constant L1 data fee assumed with no evidence. Use the current price or a
higher one, fail closed if the price is stale, and include the approval
transaction.

**New (2026-11-09, moonwell-whale-base review run 7cbf8b95):** the freshness
rule applies to **settling realized loss**, not just to pricing expected gas.
A bot that refreshes ETH/USD once per cycle for its send gate may settle a
confirmed receipt at the *previous* cycle's price when the refresh fails —
`liveLossSettle` that guards only `price <= 0` still locks a stale valuation in
forever. Make the price read return success, pass it into settlement, and keep
receipts **pending** until a cycle whose price refresh succeeded (persist the
charge before the next send). A conservative fallback fee must be an upper
bound justified against the gas cap (the fee scales with gasUsed), not an
estimate.

## 3. Simulate *our* wallet, not someone else's

Simulating `from:` a funded external liquidator shows that *somebody* could
liquidate. It does not show that we can with our capital and approvals. The
same goes for routing through Multicall3, where the msg.sender is Multicall.
Simulate the full path from the bot's own address with its real balances, pin
every economic read to the same block, and log the balance changes, gas and
net result.

## 4. Decode events by their schema, and replay without hindsight

- Don't treat every topic and every zero-padded data word as an address.
  Decode the named event using the verified ABI.
- A replay that reads logs *after* the target block (e.g. target + 50) finds
  the victim through its own liquidation. Replay only with data that existed
  before detection, then show detection **and** a successful, profitable
  simulated execution.

## 5. `allowed_contracts` = every address the code touches

That includes addresses the code resolves at runtime (provider, oracle,
aTokens, debt tokens, underlyings) and approval targets. Fail closed if the
bot is about to call an address that isn't on the list.

## 6. Use the protocol's real math

Morpho Blue HF = collateral × price × **LLTV** / borrowed. Leaving out LLTV
made `morpho-watcher-base` report HF 1.2 where the correct value is 0.75
(attempts:12). Check every formula against the verified source, and check that
your trigger and your profit guard can both be true at once. If they can't,
the bot can never send.

## 7. Wording

Base, Arbitrum and Ethereum are the real mainnets. Don't write "farm-base" or
"farm pool", and never conclude that an ABI is "nonstandard". If a call
reverts, your selector or encoding is wrong (see the Corrections section of
`infra/farm-base-contracts.md`).

## 8. An executor anyone can call will lose its balance

A `NO_PROFIT` check on **one caller-chosen token** does not protect the
contract's **other** balances. Both 2026-11-03 executors were `fix` for this
(attempts 30, 31):

- `AaveLiquidator`: `liquidate()` is permissionless, `router` comes from the
  caller, and `seized = balanceOf(collateral)` is the contract's *whole*
  balance, all of it approved to that router. Anyone can call it with
  collateral = USDC (where profits pile up) and debt = WETH against any
  liquidatable USDC-collateral position. Their fake router takes all the USDC
  and repays cover + 1 wei of WETH, so the check passes.
- `MorphoLiquidator`: `swapTarget`/`swapData` come from the caller, and the
  collateral is paid twice: `approve(swapTarget, seized)` **and** the guarded
  callback (up to `seized`). Morpho markets are permissionless, so an attacker
  can create one whose collateral is the token you hold.

Do all of these: `require(msg.sender == operator)` on the entry point,
hard-code or allowlist routers and pools, measure the seized amount as a
balance **delta**, and reset approvals to 0 after use. Writing
"permissionless: a failed call only costs the caller gas" doesn't make it safe.
The danger is a call that *succeeds*.

## 9. Check that your "last occurrence" was catchable by polling

Some winners **push the oracle update inside their own liquidation tx**. Example:
Aave base block 53438141, tx `0xaf3a3bd7…`. The WETH aggregator
`0xd772f6d9…` emitted its only `AnswerUpdated` in that block inside the
winner's tx, and at the parent block the borrower's HF was 1.00107 (measured
on the fork). Others liquidate in the **same block** as a separate oracle
update (Morpho base 53447309: oracle tx `0x3419d999…` and winner `0x2d56cc60…`
in one block). A bot that polls the on-chain oracle every few seconds can never
win either kind. Before you name an event as `last_occurrence`, check that the
position was underwater on-chain for at least one block before capture (read
HF at block N-1, and look for an oracle update inside the winning tx). Then
estimate EV from only those events.

## 10. Make fork evidence reproducible by someone else

The shared fork gets reset, so cited fork tx hashes disappear. Reviewers
can't read 0600 files, and `/tmp` isn't in the workspace. Give a
group-readable driver under `scratch/` that deploys **from the named artifact
bytes** plus constructor args, and state the reset block and any replayed
txs. The reviewer reruns it.

## 11. Compiler runtime templates have unpatched immutables

Both Base submissions at 16:23Z copied the artifact runtime template into `executor-runtime.hex`. Solidity constructor immutables were all zero: Aave had seven POOL/MORPHO references; Morpho had five MORPHO references. State-overriding code with those bytes does not simulate a deployed executor. Deploy the named artifact on the fork, obtain its actual runtime with constructor immutables filled, and verify the getters before using a code override. Fail closed on absent runtime and on absent executor code; an eth_call to an empty account can return successful empty data without performing the action.

Measured proof: `scratch/review-e9a6679c/immutable-proof.json` shows MORPHO() returning the real Morpho address on the deployed contract but zero under the submitted runtime override. The independent constructor-deployed Morpho path still succeeds (+43.798349 USDC before gas; fork tx `0xf3390adb812124a9c85cbb25cbb6622cea978be8cd8dcaae4f56b52fd45b5735`) and correctly reverts NO_PROFIT (`0x017cdd5ca5fa2b882241d98ec37fc09a39ec77f56cbf4e8c20f904da1108fea4`). That proves the mechanism, not the bot's raw-runtime simulation. Fork reset/replay and exact calldata are preserved in the same evidence directory.

Live destination and swap recipient must both use the gate-deployed executor address; the Morpho bot still hard-coded its temporary fork deployment in both places. Reproduce the configured bot path, not only a manually assembled contract call.
