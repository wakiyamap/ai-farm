# trial-fli-arb-polygon: 署名者の Polygon ガス上限 3,000,000 で全送信が拒否されています（meta 2026-11-21, run 831db6a0）

## 事実
- ライブボット `trial-fli-arb-polygon` のログ `bots/live/trial-fli-arb-polygon/logs/bot.jsonl` に `signer_reject`「gas limit above 3,000,000 on polygon」が 312 件（11-21 05:01Z〜07:04Z 頃）。最後の拒否以降は機会なし（`no_gain`）。
- 例：gross 1.41〜6.41 WPOL（約 0.1〜0.6 USD）、`eth_estimateGas` 3.29〜3.41M、ボットの gas_limit 3.94〜4.09M（見積り×1.2）。ガス代上限は 1.35〜1.40 WPOL。
- このルートは 3M ガス以下では実行できないため、現状このボットは一度も送信できません。拒否された送信には費用はかかっていません（残高 9.12 USD、nonce 1）。
- ビルダーからの報告：`inbox/meta/2026-11-21-trial-fli-polygon-gas-limit.md`。同系統のリード 349 の勝率判断もこれで止まっています。

## ご判断のお願い（どちらか）
1. Polygon の署名者ガス上限を 4,500,000 程度に上げる。4.1M ガス × 343 gwei ≈ 1.4 POL ≈ 0.15 USD で、L（50 USD）には遠く及びません。ただし上限はゲート／署名者の設定なので meta では変更できません。
2. 上げない場合は `gate stop trial-fli-arb-polygon` で停止し、資金を回収してください（スロットが 1 つ空きます）。

期待収益は小さい（1 回あたり 0.1〜0.6 USD）ので、meta としては「上限を変えるほどの価値はなく、停止を推奨」します。
