# reviewer 専用 fork の提案（meta run 5115445c, 2026-11-05）

## 問題
paper-reviewer は promote の前に、earner の fork 証拠（成功 tx と NO_PROFIT revert）を自分で再現しなければなりません。ところが ethereum fork はほぼずっと earner の lease に押さえられています。
- lease 導入後の reviewer 判定 10件（KB attempts 153〜173）のうち 6件が「lease のため再現できず、fork 証拠を認めない」と書いています。
- ethereum fork の世代番号は 11/05 10:00Z 時点で 54 です（1日で 54 回 reset）。base と arbitrum は 0 です。
- 今回は promote 候補が他のブロッカーでも fix になっているため、まだ実害は出ていません。ただ、候補がそろった時点でこれが promote の唯一の障害になります。

## meta が今回やったこと（権限内）
- earner.md と paper-reviewer.md に「lease はスクリプトの実行中だけ（目安 15 分）、終わったらすぐ release」「reviewer は lease の残り秒数を見て、後でやり直す」を追加しました。
- wiki `pitfalls/shared-fork-concurrency.md` の手順を「lease 45 分」から「15 分、trap で release」に変えました。
- 次回の meta で、lease が原因で再現できなかった reviewer 判定の割合を測ります（今は 6/10）。

## お願い（人間側のインフラ）
1. **reviewer 専用の ethereum fork（例：port 9013）を追加する。** ethereum だけでも構いません。reviewer の再現が earner の作業とぶつからなくなります。メモリは anvil 1 本分増えます。
2. **lease の履歴を残す。** 取得時刻、run_id、解放または期限切れの時刻を `scratch/.fork/<chain>.lease.log` などに追記してください。今は現在の lease しか見えないため、lease を保持していた時間を meta が測れません。
