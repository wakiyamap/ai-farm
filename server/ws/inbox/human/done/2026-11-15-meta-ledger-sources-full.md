# ledger の追加ソースが上限 40 に達した: 5 本の削除を提案（meta、2026-11-15）

researcher-claude（run acaba5af）の `ledger add-source` が「sources.d is full (40)」で断られました（inbox/meta/2026-11-15-ledger-sources-full-cleanup.md）。`ledger/` は agent には読み取り専用なので、meta からは消せません。

## お願い

次の 5 本を `ledger/sources.d/` から外してください（取り込み済みのデータは ledger.db に残る前提です）。どれも対応する lead が閉じているか、一度も行が入っていません。

| ソース | 理由 |
|---|---|
| across.filled_relay | lead 168 dead_end（fill は 0〜18 秒の競争）。actor_daily の最後の行が 11-08 で、止まっているか壊れている |
| uniswapx.fill | lead 166 dead_end（bsc・arbitrum・base とも排他的な RFQ fill、attempts 1251） |
| debridge_dln.claimed_unlock | attempts 1252 dead_end（支払先が 2 つだけ） |
| gearbox_v3.liquidate_credit_account | actor_daily に一度も行がない（live の gearbox bot はこのソースを使っていません） |
| horizon_rwa.liquidation | actor_daily に一度も行がない |

1 本空けば、lead 183（Olympus の買い戻し市場、Bond Protocol `Bonded`、ethereum 1 アドレス）のソースを researcher がそのまま入れられます。

上限 40 を増やす方針なら、そう決めてください。その場合は researcher が 1 回あたりの CU を見積もります。
