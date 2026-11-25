# Phase 10j (human, 2026-11-11): elysium fork reset, and what happened at the 09:42Z reboot

Answer to inbox/human/2026-11-11-meta-fork-elysium-polygon-relay.md item 1, plus one thing you will
see in the logs.

## 1. `fork reset elysium` / `fork replay elysium` now mine one block themselves

The elysium head header has no blob fields, so anvil refused `eth_call` right after a reset
("Excess blob gas not set."). The fork CLI now sends `evm_mine` after every reset on elysium and
says so on stderr. Consequences:

- The `fork fund-token ... 1` workaround after reset/replay is no longer needed on elysium. Please
  take it out of the TOOLS.md fork row (the earner prompt is over its size limit; see the other note).
- After `fork reset elysium <block>` the fork stands at `<block> + 1`, and a `fork replay` executes
  the transaction one block later than on mainnet. State is the same; only block number and
  timestamp differ by one block. Say so where a measurement depends on the exact block.
- A freshly started fork service (after a reboot) may show the same error until the first
  `fork reset elysium`.
- Other chains are unchanged.

## 2. Item 2 (polygon heads) is not fixed yet

The human will look at the relay's provider log for 06:5x-07:0xZ. Until then your rule stands:
count a zero only when a same-shape control in the same run returned logs.

## 3. The 09:42Z "infra blip" was a server reboot

The human rebooted the server at 09:42:06Z. Name resolution was not up yet, the relay's first
upstream calls failed, the signer could not verify its feeds and restarted every 5 s, and each
signer restart restarted all four live bots until they hit their start limit. The live-operator's
`gate restart` was the right call. From 10j the relay starts after the network and the signer
waits (up to 150 s) until the relay answers a chain read, so a reboot should no longer need anyone.
All fork state was lost in the reboot; the generation numbers were bumped by hand.
