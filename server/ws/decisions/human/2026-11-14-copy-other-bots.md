# Copy what other bots already do, including capital-heavy and cross-chain ones (human, 2026-11-14)

Direction from the human: farm should copy existing bots much more aggressively, and keep
researching them continuously. Bots that need more capital than farm gives one bot today, or that
work across chains, are in scope for the research. Extends 2026-11-13-follow-slow-liquidators and
2026-11-13-liquidator-clusters; nothing in them is withdrawn.

## 1. The census covers every kind of bot, not only liquidators

- Start from who is paid, not from a protocol: addresses that repeatedly end a transaction with
  more native token or stablecoin than they started with, or that repeatedly receive a reward or
  fee paid by a protocol.
- Classes to look for (not a closed list): liquidations, auction and order filling (Dutch
  auctions, intents, RFQ), arbitrage on one chain, arbitrage between chains, keeper / harvest /
  rebalance bounties, redemptions and peg trades, reward claiming that pays the caller.
- Operators are grouped as in liquidator-clusters (2 hops, stop at shared gateways). Never try to
  find out who owns an address.

## 2. One card per operator: wiki `infra/bot-census/<operator>.md`

Each card says, with transaction hashes as evidence:
- what it does, and the trigger it reacts to
- chains and protocols, and the contracts it calls
- capital: the largest amount it held or moved in one transaction, whether it uses flash loans,
  whether it keeps inventory on more than one chain
- timing: seconds from "takeable" to its transaction (median and minimum, up to 10 cases)
- result over the measured window: count, gross, gas, net. Write the window next to every number
- what farm lacks to do the same (capital, a bridge, inventory on a second chain, a permission,
  speed, a tool)

## 3. Do not drop a bot because it needs capital or more than one chain. Sort it

- A: copyable now. One chain, capital within one farm bot (capital_usd <= 400), and not a speed
  race by the existing rules. This becomes a lead and goes the normal way (fork proof, paper,
  review).
- B: needs capital. Give net per day at 400 USD, at 2000 USD and at the size the operator uses,
  and say why it scales (or does not).
- C: needs infrastructure farm does not have (moving funds between chains, inventory on two
  chains, something else). Name exactly what is missing and what the operator earns with it.
- D: not copyable: permissioned entry, same-block race, private order flow. One line and the
  reason.
- B and C are not built as bots yet. The limits (X 2000, 400 per bot, funds are native and USDC,
  no bridging) stay as they are until the human changes them.

## 4. Report to the human

- Researcher: once a week, a list in inbox/meta of the best B and C entries (at most 5 each),
  ordered by net per day against what is needed. Meta forwards it to inbox/human in Japanese.
- The human decides from that list whether to raise a limit or build a piece of infrastructure.
- An A entry needs no report; it is a lead.

## 5. This is continuous work

- Every researcher run spends part of its time on the census: new operators first, then
  operators whose card is older than 14 days.
- Earner measures timing for cards the researcher marks "timing wanted", and builds A entries.
  Building comes before measuring when an A entry is waiting.
- When an operator stops or changes what it does, update the card; do not delete it.

## 6. Prompt size

- Meta: put the method into the wiki (`methods/copy-bots.md`) and keep only a short pointer in the
  role files. The earner prompt was 55,319 bytes on 2026-11-14 and must stay under 56,000: remove
  or move text of equal size before adding any.
