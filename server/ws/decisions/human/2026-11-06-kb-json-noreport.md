# 2026-11-06 kb --json と no_report の理由（inbox/human/2026-11-05-meta-kb-json-and-noreport.md への回答）

phase 6n（2026-11-06 適用）。

1. `kb query --json "<SQL>"` を追加した。1 行 1 JSON、切り詰めなし（行数上限 50 は同じ）。`kb query` の 400 文字カットはそのまま。TOOLS.md の「substr で分割」の案内は `--json` に差し替えてよい。長いフィールドを `kb update` する前は必ず `--json` で読むこと。
2. `no_report` 行の notes に、その run の journal から失敗らしい行（error / timeout / killed / 429 / flagged など）の末尾 3 行を `last log:` として入れるようにした。次回の meta はこれで分類できる。earner の exit 1 の多くはローカル LLM サーバー側（応答エラー・タイムアウト）だと思うが、分類結果を inbox/human に書いてほしい。
