---
type: pitfall
chains: [ethereum]
protocols: [frankencoin]
---
# A fork deployment can move the bid past the historical window

When testing whether a bot could bid **one block before** a historical winner at block `W`, a reset to `W-1` followed by a deployment transaction and a bid transaction tests the bid at `W+1`. The fork does not replay the historical winner after the reset, so that late bid may still succeed and falsely appear to prove an earlier capture. For timestamp-sensitive Dutch auctions, also set the candidate block's historical timestamp before mining the bid.

In paper review run `e3db9ef7d75d483f83afb03ad2cd0fde` on 2026-11-16, the franken-threshold proof used the late sequence and reported challenge 8 as a counted win. The reviewer placed the already compiled runtime with `anvil_setCode` (no mined setup block), reset to `W-2`, set the historical `W-1` timestamp, and mined the bid at `W-1`: challenges 8, 9 and 10 all reverted `FlashShort`. A same-block control at `W` succeeded for 8 (+788.043617 USDC before gas) and 10 (+24.646863 USDC before gas), but those are not counted under the human race decision. The route was archived (attempts:1390).

Evidence: `scratch/reviewer-franken-proof.py`, `scratch/reviewer-franken-result.json`, `bots/archive/franken-threshold-ethereum/review.md`; the earlier related timestamp pitfall is `pitfalls/fork-reset-fetch-and-block-time.md`.
