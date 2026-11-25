# grad-flatmoney-arbitrum: please archive (lead 436 answered: no route without Hermes)

From builder-claude, run 379d5de6, 2026-11-23 19:50Z. Human request `2026-11-23-human-flatmoney-without-hermes.md`.

**Action needed:** `paper archive grad-flatmoney-arbitrum` (it has no review.md). My session's permission check refused
`paper archive` twice, so I could not do step 3 of the request myself. Suggested reason: "lead 436: without the Hermes
key an empty Pyth update executed 1 of 25 orders in 7.6 d and 0 of the trial's 13 wins". Please also tell the human
(their request): the grad is closed; trial-flatmoney-arbitrum stays live until the key expires and only the human stops it.

**Result (details in the attempts row for lead 436, scripts in scratch/fm-nohermes/):**

1. executeOrder with an empty update passes only when the newer of the stored Pyth WBTC/USD price and the Chainlink
   price is at or after the order's executable time (announce + 5 s). Stranger eth_call at the parent block of each
   real take: 1 of 25 orders in 7.6 d, 0 of the trial's 13 wins.
2. No other farm chain carries a WBTC/USD Pyth update to reuse (last stored price 916 h to 15,198 h old on the other
   7 chains). The one scheduled pusher on arbitrum (0x80b1e818..., every 21-912 s, median 343 s) or another third party hit 1 of 25 windows
   before the take. Arbitrum has no public mempool.
3. Free alternatives: public Hermes 401 (known), public Pythnet RPC (pythnet.rpcpool.com) 403 from this host. A
   self-hosted Hermes needs a Pythnet RPC and a Wormhole spy; I found no keyless source for the first. No other price
   API helps: executeOrder accepts only Pyth-signed update data (or the Chainlink price that is already on chain).
4. Order flow has stopped for now: no order executed since 2026-11-20 09:40Z (25 executed in 7.6 d, 0 in the last 3.4 d).
