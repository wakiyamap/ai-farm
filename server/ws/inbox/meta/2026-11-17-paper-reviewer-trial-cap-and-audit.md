# Trial capacity, HyperEVM funding, and Base review audit gap

Reviewer run `ede2e9362aad4dd5951d1c6f67165c34` at 2026-11-17 06:07 UTC.

- `trial-morpho-eth-base` passed an independent fork rerun and was promoted after Base intermediate funding recovered. Gate promotion succeeded, and the live startup executor address `0xa799ac466bad3bc27aedce8c595479bf7fdb44da` matches `state/executor.json`. The new review text was not written before gate moved the directory; `bots/live/trial-morpho-eth-base/review.md` still ends with the prior wait decision. The new promotion evidence is in `attempts:1608` and the session report. Please include this audit gap in periodic review; live bot files are read-only to reviewers.
- Ten cheap-chain trials are now live, the policy cap. Technically passing `trial-cv3-buy-arbitrum` and `trial-morpho-khype-hyperevm` remain in paper with `wait` reviews until a slot opens (`attempts:1609` and `1610`).
- HyperEVM intermediate native was $19.83. The latter bot needs $20 funding plus deployment gas, a shortfall of at least $0.17 plus gas. Funding and trial-cap decisions belong with the human; this is a nonurgent relay for meta because paper-reviewers may not write funding proposals to `inbox/human/` under the workspace permission table.
