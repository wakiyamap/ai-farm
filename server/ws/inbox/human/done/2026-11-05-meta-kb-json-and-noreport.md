# meta 提案（2026-11-05, run eaf9b2e0）

## 1. `kb query --json` の追加（/opt/farm/bin/kb、workspace 外のため meta は変更できません）
- 現状：`kb query` は 400 文字を超えるセルを `...` 付きで切り詰めます。earner（run ae42b633）がこの切り詰められた値に追記して `kb update` し、leads:17 の next_steps を一度壊しました（revisions から復元済み）。
- 暫定対応：TOOLS.md に `substr()` で分割して読むこと、切り詰められた値を書き戻さないことを追記しました。
- 提案：`ledger query --json` と同じように、切り詰めない `--json` 出力を追加していただけませんか。変更は cmd_query に十数行です。

## 2. earner の no_report が増えています
- 11-05 は earner セッション約 38 件のうち 6 件が no_report でした（exit 1 が 4 件、exit 0 が 2 件）。11-04 は約 25 件中 2 件でした。
- meta からはサービスログが見えないため、原因（タイムアウト、モデル API エラー、OOM のどれか）を特定できません。harness の終了理由を session ログの notes に 1 行入れていただければ、次回の meta で分類します。
