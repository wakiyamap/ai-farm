**Decision: promote** — cheap-chain trial; prior technical approval stands. 2026-11-20-trial-slots-45.md opened capacity; 40/45 live before this promote. Gate status: capital $1072.53, daily loss $0.01; not frozen. next_review_at: none.

# Review 2026-11-18T21:25Z — paper-reviewer-claude, run 51c3206828e24dc4a2486bc94da31fe4

**Decision: wait (parked: approved, waiting for a live trial slot) — cheap-chain trial.** `next_review_at: 2026-11-18T23:25:00Z`. Technical approval time: 2026-11-18 21:25 UTC. Promote after the older approved parked trials when a slot opens, subject to a fresh `gate status`. The paper service is stopped under `decisions/human/2026-11-18-park-approved-trials.md`.

Live trial count at review (`gate status`, ids starting `trial-`): **30 of 30**: trial-aave-arbitrum, -aave-avalanche, -aave-base, -aave-bsc, -aave-optimism, -aave-polygon, -aave4-base, -benqi-avalanche, -cv3-buy-arbitrum, -cv3-buy-base, -cv3-buy-optimism, -cv3-buy-polygon, -euler-base, -exactly-optimism, -feusd-redeem-hyperevm, -flatmoney-arbitrum, -fluid-arbitrum, -flux-bsc, -hyperlend-hyperevm, -hypurrfi-hyperevm, -moonwell-base, -moonwell-optimism, -morpho-arbitrum, -morpho-cbbtc-base, -morpho-eth-base, -morpho-khype-hyperevm, -morpho-whype-hyperevm, -revert-lend-arbitrum, -venus-bsc, -xlend-base. Base intermediate wallet holds 22.41 USD native; this bot needs 5.

Hashes reviewed (sha256): bot.py `0407ae20…5b33`, manifest.yaml `61f8912d…72ad`, PeapodsTake.sol `ae4a5a81…1538`.

## Cheap-chain trial checks
- Chain base (≠ ethereum), `capital_usd` 5 ≤ 20, `max_loss_per_tx_usd` 1. Signed worst case: 3.2m gas × 0.05 gwei max fee + 1e11 wei L1 allowance = 1.601e14 wei = 0.64 USD at 4000 USD/ETH. The Base L1/operator fee is bounded by the 5 USD wallet (under the 18 USD cap). `fee_cap()` refuses ≥ 1 USD. ✓
- Reads: waits on feed `/logs` (one low-volume `Liquidate` filter on the pair), 10-min safety scan, code cap 100,000 CU/day. ✓ Re-reads on `gap`, on 429/503 and on loop errors. ✓ No busy event. ✓
- Paid entry in the last 7 days: 78 Liquidate txs on pair 0x23574154 (README table). Example 0x0f197f0b… left +0.001745 WETH vs ~2.34m gas (~1e13 wei). ✓ `liquidate(uint128,uint256,address)` is public. ✓
- Send condition `gross > cap` (bot.py:197), then guard simulation with minProfit = cap+1. Priority fee fixed at 0.001 gwei, as stated. ✓ Each send gets a log line: won/lost, gas, cost, winner_block. On a loss winner_block is the trigger block, not the actual winner's block (minor, see note).
- Paper path: `caller()` returns PAPER_OWNER, eth_call with a code override, no signer. `my_address()['address']`, signer path appended. ✓
- S: public liquidation, confirmed logs only, no mempool. ✓

## Executor (criteria 1-3, 5) — reproduced by me
`scratch/review-51c3/peapods_proof.py` → `peapods-result.json`. Base fork reset 59,166,221, current artifact deployed at 0xb464f731…:
- non-owner call reverts (tx 0x9b24f7bf…, status 0)
- guard: minProfit 1e18 reverts (tx 0x48a774e3…, 2,971,721 gas, owner lost only gas)
- success **at the bot's 3,200,000 gas limit** with bot-style minProfit = 3.2m×0.01 gwei + 1e11 + 1: tx 0xe97974f6…, 2,390,684 gas, owner **+0.001734998 ETH net of gas**
- after success: executor WETH / fWETH / aspPEAS / spPEAS / pPEAS / ETH balances all 0. Allowances WETH→pair, WETH→Morpho, spPEAS→IndexUtils all 0.
- `eth_estimateGas` = 3,056,343 < 3.2m (thin margin; the bot simulates at 3.2m before every send, so a shortfall shows up as a simulation revert, not a loss).
Executor shape: only `{bot}` in the constructor, every target is a call argument, a per-tx Morpho counterparty check is set and cleared, exact approvals are reset to 0, profit returns as native ETH, no setup tx. ✓ manifest-check PASS, `allowed_contracts: []`. ✓

## Paper log (about 1 h)
Detected feed event block 59,222,211 (borrower 0x1108a806). Every candidate reverted `swap quote` (quoted < 80-99% of the scaled source output) and the bot logged `no_profitable_sim`. Nobody else took that borrower's remainder in the following 20 min, which fits "not profitable". No error loops.

## Notes for the builder (non-blocking)
- `send_result.winner_block` on a loss is the trigger block. Look up the actual winning Liquidate for that borrower after the send so the trial measures how far behind we were.
- The gas margin is about 5% over the estimate. If live simulations revert out of gas, take the limit from `eth_estimateGas`.
