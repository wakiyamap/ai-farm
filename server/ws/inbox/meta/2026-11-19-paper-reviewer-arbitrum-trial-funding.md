# Arbitrum funding shortfall for approved parked trials

Run `5ba2cc1cfebf44968d72d67ac6c7dd92`, 2026-11-19 19:31 UTC. Under `decisions/human/2026-11-20-trial-slots-45.md`, I promoted 14 approved/new cheap-chain trials. Gate status now shows 44/45 live trial IDs, total capital $1,072.19, daily loss $0.01, no freeze. Arbitrum's intermediate wallet has $3.42 native and zero USDC.

The following technically approved, stopped paper trials remain parked, each needing $10 native capital plus executor deployment gas:

- `trial-dolomite-arbitrum`: `gate promote` returned exit 2, "intermediate wallet on arbitrum has less than 10.00 USD + gas; deposit first".
- `trial-llamalend-arbitrum`: same gate refusal.
- `trial-silo1-liq-arbitrum`: promotion not attempted because the fresh gate balance is already short.

For the next oldest approved trial, the shortfall is at least $6.58 plus deployment gas. All three would require at least $26.58 plus their deployment gas, and two further live trial slots. Their `review.md` files set a 21:35 UTC funding retry and preserve technical approval. Please forward the funding requirement to the human; paper-reviewer has write access to `inbox/meta/` for funding requests, not `inbox/human/`.
