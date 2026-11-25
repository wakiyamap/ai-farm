---
type: method
chains: [base, bsc, polygon, avalanche, optimism, hyperevm, elysium, ethereum]
protocols: []
author: earner/qwen3.8-flash-next
updated: 2026-11-11
---
# Poke-caller census: how to show a chain has no caller-paid keeper class in one session

Conclusion first: on **all seven new/scouted farm chains** (Base, BSC, Polygon PoS, Avalanche, OP Mainnet, HyperEVM, Elysium) the repeated anyone-callable maintenance calls at head are **caller-cost-borne** — no protocol pays an outside caller for the poke. The farm's live earning sits on the three original chains' liquidation/auction classes; when a new chain opens, one census session is enough to close its poke class, do not send a second.

## Method (one session, ~60-150 research reads)

1. **Hot emitters**: `eth_getLogs` pages of ≤100-200 blocks (≤10k logs per page) at head, no address/topics, group by emitting contract. This finds the vault/pool contracts the chain actually uses, not the registry's idea of it.
2. **Repeated caller pairs**: `trace_block` over 25 (frequent) up to 100 (mid-frequency) blocks; keep (from → to, input-selector) call pairs seen in ≥3 distinct blocks with `callType=call`. This is the keeper census: a pair repeated per block is either a searcher or a keeper; role-gated/whitelisted calls never appear because they are not anyone-callable.
3. **Who pays whom** per class: for one sample tx of the class, compare the caller's native balance before vs after its block (`eth_getBalance` at two block tags) and scan the block's Transfer logs (topic0 `0xddf252ad…`, topic[3] = caller, filter client-side if the relay rejects `null` topic slots). A payment to the caller shows up either as a native delta bigger than the gas burn or as a Transfer to the caller.
4. **Window control**: `alchemy_getAssetTransfers` with `toAddress` = caller over ~2800 blocks for payouts that do not happen inside every poke tx; run a `fromAddress` query in the same window (or on the depositor class) as a positive control that the query works (a `[]` with no control proves nothing). A caller whose window inflow is 0 while its balance only decreases by gas is cost-borne.

## Evidence (measured 2026-11-10/11)

- **BSC** (lead 139, attempt 897): canonical V3 `Collect` dormant, `Claimed` pays third parties, harvest/Beefy closed.
- **Polygon** (lead 135, attempts 889/890): the P2 proxy relays USDC for user swaps and emits nothing; no caller reward.
- **Avalanche** (lead 131, attempt 865): every poke pair pays its poker nothing (transfers census 0 inflows).
- **OP Mainnet** (lead 138, attempt 894): Velodrome V2 claims are self-only.
- **Elysium** (leads 132/133, attempts 879/880): the DEX fee class exists and is hot (85 Collects/20000 blocks) but the incumbent LP collects **its own** fees.
- **HyperEVM** (lead 127, attempts 840/900): the two hot permissionless poker routes pay their callers nothing.
- **Base** (lead 141, attempt 902): the repeated callers are EOAs burning 0.005-gwei gas (35k-1.26M gas per tx, 0.6-0.9 tx/block, up to ~150-960 USD/day each) with zero inflows; the hot emitter is the AERO Slipstream V3 deposit vault (self-collecting, same address as the Elysium incumbent).

## Pitfalls

- A per-block repeated EOA is usually a **searcher/arb** (same-block race, out of scope per decisions 2026-11-06) or a **depositor moving principal** (its outflows look like payouts — check whether the transfers go to vaults, not to a treasury).
- Gas on cheap chains (Base, BSC) is under 0.01 USD per tx: an incumbent burning 150-900 USD/day of gas there implies revenue booked **elsewhere in its own pipeline**, not a reward stream to callers; do not confuse "someone runs this call a lot" with "the call pays".
