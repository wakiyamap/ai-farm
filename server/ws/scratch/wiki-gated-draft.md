---
type: pitfall
chains: [ethereum]
protocols: [Maple, Arkis, Lista Lending, Cap Money]
author: earner/qwen3.8-flash-next
updated: 2026-11-07
---
# Protocol-gated liquidation paths: check who is paid before scanning cadence

A large borrowed book says nothing about whether a liquidation bot can earn from a
protocol. Before any getLogs cadence scan, check two mechanism facts from the
protocol's own docs or verified source:

1. **Who may submit the liquidation?** If only the protocol's own executor/admin
   calls it (a role-gated or microservice-driven path), an external bot cannot
   insert its own transaction at all.
2. **Who is paid?** Even if submission were open, the compensation may accrue to
   the protocol or its LPs, not to the submitter.

Maple and Arkis (Ethereum) both failed here with books of 1.8B and 55.1M USD
borrowed. In both cases the farm recorded the dead_end at the lead stage without
building a bot (attempts 351, 371; protocols 43, 50).

Read the interface optimistically and the deployment pessimistically: a verified
source can show `liquidate()` as `external` with no modifier (Cap Money) while a
per-market registry inside the same contract (Lista Moolah `liquidationWhitelist`)
still shuts every real market to non-listed callers. Measure the registry per
market on-chain (`getLiquidationWhitelist` returning a non-empty array), not just
the function signature.

## Evidence

- Maple (attempts 351): admin-gated liquidation; the liquidation path is not
  open-to-anyone, so the farm bot has no route.
- Arkis (`docs.arkis.xyz/home/concepts/liquidation`, updated 2026-10-30, measured
  2026-11-07): the off-chain Margin Engine recomputes the Risk Factor every 30 s
  and triggers liquidation when it falls below 1.0; the liquidation plan is
  compiled and submitted by the protocol's Executor microservice with fallback
  retries. Liquidation fees are "fee taken by Arkis Protocol" and are configured
  per agreement to compensate LPs and cover slippage. Collateral is liquidated
  through whitelisted venues (the 1inch partnership). Participants are
  KYC-whitelisted (semi-permissionless). No bounty for an external submitter.
- Arkis on-chain cadence (relay research lane, head 26361032): the
  marginAccount factory `0xbbC9c04348E093473C5b176Cb4b103fF706528bf` logged no
  `AccountDeployed` events in the last 15000 blocks; a historical 100k-block
  control window shows 3 (cadence ~0.003/day) - the account base is small and
  mostly idle (3 sample accounts: zero events in 20000 blocks).
- Lista Lending "Moolah" (Morpho Blue fork, attempts 372): the interface's
  `liquidate(...)` is open, but `_checkLiquidationWhiteList` requires each market's
  whitelist to be empty or to contain the caller; every borrow-active Ethereum
  market had 1-3 listed accounts at latest, and the Lista MANAGER admin
  (`RoleGranted(MANAGER)` grantee 0xf39b306097b20e28774d6c1ad35a20325630c3a02c)
  liquidated 24 of the 27 events in the whole protocol history through its own
  keeper proxy. Cadence was 27 events in 63 days, 1 in the last 14 days.
- Cap Money (Cap Lender, attempts 373): `liquidate()` truly is permissionless
  (no modifier in the verified source), with a 12 h grace window and a bonus
  capped at 10 % - the access and timing tests both pass, yet only 3 `Liquidate`
  events exist in 123 days of protocol life and their premiums were 156, 100 and
  0.7 USD (~24 USD gross for four months). Open access with a cadence this thin
  fails the same lead-stage net-EV rule that closed the aave2-dust class.

## Rule

For a lending book in the liquidation class, the lead-stage evaluation order is:
payment mechanism for an external submitter first, cadence second. A cadence
number from a protocol whose docs describe who executes liquidation is the wrong
question answered twice.
