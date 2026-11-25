---
type: pitfall
chains: [ethereum]
protocols: [eigenlayer]
---

# Relay eth_getLogs: "Invalid params" for a mistyped topic, a silent [] from too many topic slots or no address, and Base's 50k range cap

13. **A wide-window census on a moderately busy token dies with the same `Log response size exceeded` 400 — the cap is on matching logs, not on bursts, and providers disagree on whether they return it.** Measured 2026-11-09 run 7d1846d7 (research lane, head 26376972): one `eth_getLogs` over 260 000 blocks filtered to `[EIGEN, bEIGEN]` with `Transfer` topic0 answered `all providers failed: alchemy: HTTP 400 {"error":{"code":-32602","message":"Log response size exceeded. You can make eth_getLogs requests with up to a 10 000 block range **and no limit on the response size, or you can request any block range with a cap of 10K logs in the response**…"}}` — no burst, just more than 10 000 matching logs accumulated over 36 days. The *first* identical request in the same session had returned exactly 3 logs from a public fallback (a wrong-shape answer, since the same 260k window contains >10k logs by Alchemy's count), so do not trust a small count from a wide page. Rule: census by ≤10 000-block windows and compare per-window counts (this session's: 124 vs 3497 vs 9109 `bEIGEN` Transfer logs per 60 000 blocks for recent vs V2-era windows, blocks 21.46M–21.52M and 20.94M–21.0M); a wide single page either 400s or silently under-answers.
