# Morpho watcher Ethereum promoted

Run 57418800d9d249e3b547e911e3a47c5f promoted `morpho-watcher-ethereum` at 2026-11-10 06:00 UTC. Gate reported address `0x26B6c9F3ED3a8229B83dD575c71657b271845bCc`, active/running, about 10.42 USD ETH after deployment, zero USDC principal. It is funded for 16 USD native; its own 18 USD wallet preflight should allow sends. Daily loss was zero and gate was not frozen.

Independent fork proof: `scratch/review-57418800/morpho-proof.json` shows `NO_PROFIT` revert with executor USDC 0 to 0 and successful atomic liquidation with USDC 0 to 3.711168. Signed gas cap is 460000 x 17.5 gwei = 0.00805 ETH (about 17.09 USD at the paper price 2123 USD/ETH). The bot's cumulative live loss stop is 30 USD; offline stop test passed. Latest ledger liquidation at Ethereum block 26382023 was outside the two executable markets. Monitor first live sends and executor deployment as part of normal live review.
