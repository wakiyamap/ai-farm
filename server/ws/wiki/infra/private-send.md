---
type: infra
chains: [ethereum]
protocols: [flashbots]
author: meta/opus
updated: 2026-11-15
---
# Private send (`send_route: private`): ethereum only, via Flashbots Protect

**Conclusion.** A bot whose manifest says `send_route: private` has its **ethereum** transactions sent by farm-signer through rpc-relay's private route (Flashbots Protect) straight to block builders, never to the public mempool — not even when the route fails (the tx is dropped). On every other chain the key does nothing (public via Alchemy). Missing or `public` = unchanged behaviour. Any other value: the signer rejects every send (`tools/manifest-check.py` errors). Live since phase 12b, 2026-11-15 04:28Z; signer.log lines carry `route`. Source: `decisions/human/2026-11-15-private-send.md`, common.md "Send route", earner.md section 5.

## What it is for

1. Opportunities that the public mempool gets copied or front-run before they land.
2. Making misses free: a private tx that would revert is not included, so it costs no gas.

## What it does not do

- **It does not win contested liquidations.** Lead 14 (attempts 1244/1245, 2026-11-14): the winner paid the builder 4.014 ETH (~7,570 USD) on a ~7,523 USD gross — essentially all of it. We do not bid, and the executor never pays `block.coinbase`. Use the route only where competition is thin.
- No mempool watching, no placing around others' transactions (S unchanged). X, n, L, 400 USD per bot and the 30 USD live-loss stop are unchanged.

## Rules for a private bot

- **Deadline argument**: the executor entry takes a block number and reverts after it; set 2-3 blocks ahead; prove on the fork that a call past the deadline reverts. Without a deadline a dropped-then-late inclusion could land in a different state.
- **`private_not_included`**: nobody reports a non-inclusion. After sending, poll the receipt until the deadline passes; if none, log `private_not_included`.
- **Nonce replacement**: a second private send before the first is mined uses the same nonce and replaces it; only one lands.
- **Daily spend**: each send counts its worst case against the day's `capital_usd`, included or not.
- README: one line saying why this bot is private.
- Earner rule (earner.md section 1): a lead closed because the public mempool copies it is re-evaluated with a private send on ethereum; on other chains it stays closed with `private-send` in `next_steps`.

## Not yet verified with real funds

Inclusion through the route, blocks until inclusion, and that a reverting tx really is not included. The first bot to use the route checks this on its first send; its earner and reviewer write the result to `inbox/meta/`, meta forwards it to `inbox/human/`.
