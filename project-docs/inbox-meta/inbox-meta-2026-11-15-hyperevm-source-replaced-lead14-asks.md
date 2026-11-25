# Answer: morpho_blue.liquidate_hyperevm source replaced; two more measurements on lead 14 (human, 2026-11-15)

## 1. Source fix (answer to inbox/human 2026-11-14-meta-morpho-hyperevm-source-fix.md)

- Done at 2026-11-14 21:19Z: `ledger/sources.d/morpho_blue.liquidate_hyperevm.json` was replaced with `scratch/census-ac40/morpho-source-corrected.json`. The diff was only `indexed`: `["id", "borrower", "receiver"]` -> `["id", "caller", "borrower"]`.
- The human-owned Morpho source in the ledger config already had `["id", "caller", "borrower"]`, and no other file in `ledger/sources.d/morpho*.json` has the wrong names.
- Rows already stored are NOT rewritten (there is no tool for it). meta: add the wiki note in `infra/ledger-agent-sources.md`: for rows of this source ingested before 2026-11-14 21:19Z, read `borrower` as the caller and `receiver` as the borrower; amounts and actor / tx_from are unchanged.
- A third wrong source will get a `ledger update-source` command, as you wrote.

## 2. Lead 14: two things the measurement of the skipped opportunity left open

For the earner, measurement only. Do not change the live bot.

1. Why does the farm path net +16.12 USDC where the taker's gross was about 7,523 USDC on the same borrower and block? State the repay amount the farm path used, what limited it (a cap in the executor or bot, slippage in the exit pool, the seized amount), and what the farm executor would net on the same fork with the full repay and the best exit pool you can find.
2. The taker's transaction in block 26413695: its index in the block, its effective priority fee per gas, any direct payment to the block builder (a transfer to the fee recipient inside the tx), and its type (P / B / O / S / T as in decision 2026-11-14-taker-types-pull-oracle). Also the index and priority fee of the farm's own pool-init tx in that block, as the reference for where a farm liquidation would have landed.

Record both on lead 14 and in the session report. The limits stay as they are: no mempool watching, no bundles, no direct sends to builders, sends through Alchemy only.
