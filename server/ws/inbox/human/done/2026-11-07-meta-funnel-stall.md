# 2026-11-07 meta: ファネルの停滞（提案・判断のお願い）

## 現状（数値の出典: logs/sessions/2026-11-07.jsonl 55-87 行、kb protocols、gate status の reviewer 報告）

- live bot 0、paper bot 4（gearbox / moonwell-whale / morpho-watcher / reserve-dutch）。すべて「自然発生のキャプチャ待ち」で、reviewer は 4 回連続 promote=0 fix=0（skipped のみ）。cv3 は earner が blocked_infra で archive。
- 12:58Z 以降の earner レポート約 25 件のうち、paper 配置 0、結果は dead_end_recorded / lead_recorded / blocked_infra のみ。KB protocols は 120 行を超え、3 チェーンの DefiLlama Lending（借入 10 万 USD 以上）はすべて調査済みと earner が報告。
- 利益が測れた候補（Gains 約 1,400 USD/日、Venus の大口など）は、同一ブロックの速度競争で blocked_infra（2026-11-06-no-latency-race の方針どおり）。

## 提案（どれか一つを選んでください）

1. earner の探索対象を清算以外（keeper 報酬、オークション、公開の報酬 claim）に明示的に広げる。meta が earner.md に「清算の新規調査は lead がある場合のみ」と書き足す。
2. 待機中の paper bot に期限（例: 14 日間キャプチャ 0 なら archive）を設けて、reviewer のセッションを減らす。
3. 現状維持（自然発生を待つ）。

返答が無い間は、meta は何も変えません。次回の meta で、earner の結果の内訳を数え直します。
