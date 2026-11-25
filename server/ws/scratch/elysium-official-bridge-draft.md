---
type: infra
chains: [elysium, hyperevm]
protocols: []
---

# The official Elysium <-> HyperEVM bridge: 1:1, ~5.6 d exit, gas-only cost, anyone can claim

**Conclusion first.** Moving USDC from Elysium back to HyperEVM through the official bridge costs
nothing but gas (~0.0001-0.0004 HYPE = cents at any gas price we saw; ~$0.02 total both sides) and
is exactly 1:1, but takes the challenge period of 483,840 HyperEVM blocks (~5.6 days; the bridge UI
says ~7 days). The HyperEVM-side claim can be executed **by anyone** and pays out to the original
recipient, so the recipient never needs HyperEVM gas. This is the number that makes Relay's ~2.5-3.9%
exit ask from elysium a pure price-of-time quote (attempts:1342), not an unavoidable cost.

## Where the docs live (pitfall)

The new chain's docs are **https://elysium.kinetiq.xyz/docs** (Kinetiq's Arbitrum Orbit chain, 99901),
pages: *Token bridging*, *Bridging HyperEVM tokens to Elysium*, *Bridging Elysium tokens to HyperEVM*,
*Token bridging architecture*, *Contract addresses*. `docs.elysiumchain.tech` is the OLD Vulcan Forged
Elysium (chain ids 1338/1339) and `bridge.elysiumchain.tech` is a JS SPA - do not read them for this
chain (lead 191, run 8badb96dc).

## The USDC route (canonical bridge, run in reverse for the exit)

USDC on Elysium (`0xb47c4C8F73F009CC0C0d3f92B388d13E293F0B65`, 6 dec) is the StandardArbERC20
representation of HyperEVM USDC (`0xb88339CB7199b77E23DB6E890353E22632Ba630f`); the escrow sits in the
ERC-20 gateway on HyperEVM (`0xd97B30dE0bA0C2eAeE942afce77530e06c5F122c`). All addresses pinned from
the docs *Contract addresses* page and verified live on 2026-11-15: the Elysium router's
`calculateL2TokenAddress(0xb883..630f)` = `0xb47c..0b65` and `getGateway(0xb883..630f)` =
`0x5DC84e4Cb0F9082246E92a5585C5395592B1aF1f` (the Elysium ERC-20 gateway). The router keys every
route on the **HyperEVM** (parent-chain) token address in both directions.

**Elysium -> HyperEVM (withdraw).** One transaction on Elysium: `outboundTransfer(USDC_hyp, to, amt,
0, 0, "")` at the Elysium router `0x61EbbC3A29f1970aF2Ce862bA9c5364832E14d17` - "No approval, no
value" (docs quote). The representation burns immediately; the withdrawal message finalizes after the
challenge period (483,840 HyperEVM blocks ~ 5.6 d at 1 s blocks) and the original is then claimable
on the Outbox `0xeC6B106DfA14428FE5Eec2a4065a7be599f02728`. Docs (mirror guide, same Outbox):
"Claiming it through the Outbox on HyperEVM mints amount ... to the recipient. **Anyone can claim
it**"; for stuck messages "the message stays claimable, **anyone can re-execute it** ... Funds are
delayed, not lost" (but "Messages left unredeemed for several days can expire, so re-execute
promptly").

**HyperEVM -> Elysium (deposit).** Two transactions on HyperEVM (approve gateway + `outboundTransfer`
with `msg.value = maxSubmissionCost + maxGas x gasPriceBid`, excess refunds); the representation is
minted on Elysium "typically within a minute" because the delivery retryable auto-executes. There is
no challenge wait entering.

There is also a **mirror bridge** (Elysium-native tokens: lock on Elysium, mint mirror on HyperEVM
after the same 483,840-block challenge; factories `ElysiumBridgeFactory` 0x209B0476ec33841c661f41C0C260A3b8aF94164A
and `ElysiumMirrorFactory` 0x473D61817Da6ce1a97aDC010FF1e96048504643B). Not needed for USDC/WHYPE.

## Measured costs (2026-11-15 22:2xZ, relay research lane, HYPE ~67.2-67.8 USD from the live relay191 pool series)

- Elysium leg: `eth_estimateGas` of `outboundTransfer` (50 USDC from a funded holder) = **175,487
  gas**; Elysium base fee 0.5 gwei (the docs minimum; batch posting ~15 min, priority fees kept by
  the network, not burned) -> ~0.00009 HYPE at base, ~0.0002 HYPE even with 1 gwei priority =
  **~0.006-0.013 USD**.
- HyperEVM claim leg: three real claims measured from receipts (gateway payouts 0x53cfcfc5..,
  0xdb1e4b72.., 0xd7503b0e..): gasUsed **158,908-175,994**, effectiveGasPrice 0.1-1.2564 gwei ->
  **0.000016-0.0002 HYPE = ~0.001-0.013 USD**. The route is live: 13 gateway->recipient payouts in
  the ~10k-block (2.7 h) window I scanned.
- Deposit direction (for completeness): sender prepays the Elysium delivery bid in msg.value, docs
  sample 4e14 + 300,000 x 0.1 gwei = 0.00046 HYPE ~ 0.03 USD, excess refunded.

## What this means for the elysium USDC gap (lead 191)

The 0.6-1.0% Elysium WHYPE-vs-HYPE pool gap (and the +0.14% median relay entry quote) sit against an
exit that costs ~1-3 cents in gas and 5.6-7 days of locked capital. The Relay exit (~-2.5% USDC
direct, ~-3.9% WHYPE->HYPE, attempts:1342) is the market price of skipping that wait at 20-200 USD
size. Whether the gap survives 7 days of lock and price risk is item (b) of the lead-191 analysis.
