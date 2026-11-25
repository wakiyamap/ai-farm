# Injective の読み取り経路の依頼（meta の推奨: 今は作らない）

builder（run 9d297292）から inbox/meta/2026-11-22-injective-peggy-read-route.md で依頼がありました。

- 対象: Ethereum 側の Injective Peggy ブリッジ `submitBatch`（誰でも呼べることは fork で確認済み、lead 384、attempts:3599）
- 必要なもの: Injective（Cosmos、EVM ではない）の `OutgoingTxBatches` と `BatchConfirms` をタイムスタンプ付きで読む経路。今の relay は 9 つの EVM チェーンだけで、ノードへの直接接続は禁止なので、farm の外側（relay の設定）の変更になります
- 上限の見積もり: 過去 7 日を全部勝った場合でも差し引き 25.28 USD、1 日 3.61 USD（attempts:3565）。競争相手を引く前の数字です。署名がそろってから Ethereum に出されるまでの時間を測っていないので、反応時間のルールで数えられるかもまだ分かりません

**meta の推奨**: 今は作らないでください。全勝でも 1 日 3.6 USD で、Cosmos の経路を新しく作って保守するほどの価値はありません。作る場合は人間の判断なので、ここに書きました。lead 384 は blocked_infra のままにします。
