# trial-dfm-weekly-optimism: 窓は毎週日曜 12:00 UTC だけで、次は 11-29（11-24 の締めの後）

From: meta, run 03003071, 2026-11-22 16:4xZ。元のメモ: inbox/meta/2026-11-22-dfm-weekly-window-after-trial-close.md（builder 21d6d9c4）。KB: lead 407, attempts:3753, 3754。

1. **お願い（判断は人間）**: 11-24 の締めで試行の bot を止めるとき、この bot だけは **11-29 12:00 UTC の窓を過ぎるまで live に残す**ことを検討してください。live になってから窓が一度も来ていないので、11-24 までに結果は出ません。
2. 何をする bot か: defi.money の `PrimaryFeeAggregator.processWeeklyDistribution()`（OP Mainnet）を呼んだ人に、プロトコルの週（日曜 12:00:00 UTC 始まり）ごとに 1 回 10 MONEY（swap 後 約 9.9 USDC）が払われます。1 回の gas は 0.01 USD 未満（上限 0.031 USD）。
3. builder の測定: 過去 9 週で、取られた週はどれも週の始まりから 12 秒以上後（13 s, 35 s, 41 s, 249 s, 2.7 h, 10.3 h）、3 週は誰も取っていません。同じ tx を各週の最初のブロックで simulate すると 9.80-9.94 USDC（`scratch/trial-dfm-weekly-optimism/weeks-result.json`）。毎週勝てば 約 1.41 USD/日。meta は数字を再測定していません。
4. 状態（gate status 16:4xZ）: live、wallet optimism 3.01 USD、nonce 1、損失なし。残すのに追加の資金はいりません。

## 別件（参考）: Alchemy の月の枠

relay `/health` の `cycle`（16:4xZ）: 使用 61.23M / 枠 95.2M CU、最近のペースで 127.6M の見込み（`projected_share` 1.34、`alert_85` true）。残り 33.97M を 1 日約 8.0M（うち live lane が 43.5M/71% を占める）で使うと、**尽きるのは 11-27 ごろ**です。11-24 より前ではないので、11-20 の決定 5 に従い対応は求めません。11-24 の締めの後も試行の bot を多く残す場合は、11-27〜12-01 の分が足りなくなります。
