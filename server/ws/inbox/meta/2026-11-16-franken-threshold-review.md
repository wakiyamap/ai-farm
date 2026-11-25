# Franken threshold review outcome (run e3db9ef7)

Paper reviewer archived `franken-threshold-ethereum` and set lead 74 to `blocked_infra` (attempts:1390). The earner's proof reset to winner-1, then mined deployment and bid, so the bid landed at winner+1. Corrected fork replay at the historical timestamps mined bids one full block before each winner: challenge 8 (block 26293523), 9 (26311562), and 10 (26327480) all reverted `FlashShort`; counted 30-day EV is $0. The same-block controls do not count under the 2026-11-16 human decision. See `bots/archive/franken-threshold-ethereum/review.md`, `scratch/reviewer-franken-result.json`, and `wiki/pitfalls/fork-deploy-off-by-one.md`.

For the human's question in `decisions/human/2026-11-16-franken-threshold-bid.md`: challenge 11, which began at block 26403144, was taken at block 26410802 on 2026-11-14 04:22:47 UTC, about 1.59 h after expiry, by `0x2ff82bd2`. The bot was not promoted, so there is no first private-send result to report.
