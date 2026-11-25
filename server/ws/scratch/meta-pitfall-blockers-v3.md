---
type: pitfall
chains: [any]
protocols: [aave_v3, morpho_blue]
---
# Why paper bots keep getting `fix`: check these before you submit

**Conclusion:** All 6 paper reviews on 2026-11-03 (attempts 2-4 and 10-12;
details in `bots/paper/*/review.md`) were `fix`. Five of the six named the
same first blocker: **nothing in the code caps the loss of a transaction that
succeeds.** Fix that first. Every other item below also came up at least twice.
Read this before you mark a bot `paper_placed` or `fix_submitted`.

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

Patterns a reviewer can accept (name one in `max_loss_guarantee` with file:line):

- **Small enough to be safe by construction:** total principal at risk plus
  every fee (approval tx included) is at most 20 USD, enforced by a check in
  code before sending. A 5% bonus on about $18 is under $1, but on Arbitrum a
  liquidation costs about $0.03 in gas (see
  `mechanisms/aave-v3-arbitrum-measured-abi.md`), so a small bounded run is
  still worth doing. It is the fastest route to a live bot.
- **Atomic:** one transaction liquidates, sells the collateral and reverts
  unless the bot's balance at the end is at least its balance at the start
  minus the gas bound. Then the worst case is gas only. This needs an executor
  contract. **Deploying one is not confirmed possible yet:** the signer's
  `send()` requires a `to` address, so a plain contract-creation tx looks
  unsupported. KB `leads` row "atomic executor contract deployment path for
  live bots" has the possible CREATE2-deployer route and the open question to
  the human; check it and `decisions/human/` first. Until it is resolved, use
  the small bound above.

## 2. Value fees at full price, and keep the price fresh

Reviewers rejected an ETH price halved "for safety" (that understates the
cost, which is the unsafe direction), a price read only at startup, and a
constant L1 data fee assumed with no evidence. Use the current price or a
higher one, fail closed if the price is stale, and include the approval
transaction.

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
