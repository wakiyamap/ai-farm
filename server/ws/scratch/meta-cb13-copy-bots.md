---
type: method
chains: [base, arbitrum, ethereum, bsc, polygon, avalanche, optimism, hyperevm, elysium]
protocols: [any]
---
# Copy other bots: the bot census (decision 2026-11-14-copy-other-bots)

**Conclusion first:** copy what existing bots already earn from, whatever the class, and keep doing it. Start from **who is paid**, not from a protocol. Group addresses into operators, write one card per operator, and sort each into A (copy now), B (needs capital), C (needs infrastructure) or D (not copyable). A entries become leads; B and C go to the human once a week as a short list; nothing is dropped because it needs capital or a second chain. Source: `decisions/human/2026-11-14-copy-other-bots.md` (it wins if this page disagrees). It extends `methods/follow-slow-liquidators.md` (liquidator census, operator grouping) and withdraws nothing from it.

## 1. Who to look at (researcher)

- Addresses that **repeatedly end a transaction with more native token or stablecoin than they started with**, or that **repeatedly receive a reward or fee paid by a protocol**.
- Any class, not a closed list: liquidations; auction and order filling (Dutch auctions, intents, RFQ); single-chain arbitrage; cross-chain arbitrage; keeper / harvest / rebalance bounties; redemptions and peg trades; reward claims that pay the caller.
- Group addresses into operators exactly as in `methods/follow-slow-liquidators.md` step 1b: funder and payout 2 hops each way, siblings, shared executors; stop at any address that funded more than 200 addresses (shared gateway); a tx hash for every link. **Never try to find out who owns an address.**

## 2. One card per operator: wiki `infra/bot-census/<operator>.md`

Each card, with transaction hashes as evidence:

- what it does, and the trigger it reacts to
- chains and protocols, and the contracts it calls
- capital: the largest amount held or moved in one transaction; flash loans or not; inventory on more than one chain or not
- timing: seconds from "takeable" to its transaction, median and minimum over up to 10 cases (mark the card **timing wanted** if not measured yet; earners measure it)
- result over the measured window: count, gross, gas, net, **with the window next to every number** (no scaling to 30 days)
- what farm lacks to do the same: capital, a bridge, inventory on a second chain, a permission, speed, a tool
- its class: A / B / C / D (below)

When an operator stops or changes what it does, update the card; never delete it.

## 3. Sort, do not drop

- **A, copyable now:** one chain, capital within one farm bot (`capital_usd` <= 400), not a speed race by the existing rules (same block out; next block feed-only and not counted in EV). Becomes a KB lead and goes the normal way (fork proof, paper, review). No report needed.
- **B, needs capital:** net per day at 400 USD, at 2000 USD and at the size the operator uses, and why it scales or does not.
- **C, needs infrastructure farm lacks** (moving funds between chains, inventory on two chains, something else): name exactly what is missing and what the operator earns with it.
- **D, not copyable:** permissioned entry, same-block race, private order flow. One line with the reason.

B and C are **not built** as bots. The limits (X 2000, 400 per bot, funds only native and USDC, no bridging) stay until the human changes them.

## 4. Cadence and reporting

- **Researcher:** every run spends part of its time on the census: new operators first, then cards older than 14 days. Once a week, a list in `inbox/meta/` of the best B and C entries (at most 5 each), ordered by net per day against what is needed. Meta forwards it to `inbox/human/` in Japanese; the human decides whether to raise a limit or build infrastructure.
- **Earner:** builds A entries (building comes before measuring when an A entry is waiting), and measures timing for cards marked "timing wanted" (same counting as `methods/blocked-infra-feed-retriage.md` step 2).
