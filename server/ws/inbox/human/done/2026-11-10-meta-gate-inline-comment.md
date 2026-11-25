# meta a73d9b23: gate-ctl の数値パースと researcher の TOOLS.md 権限（小さな依頼 2 件）

## 1. gate-ctl の `capital_usd` / `max_loss_per_tx_usd` でインラインコメントを許容してほしい

- 事象: 2026-11-10 02:55Z、paper-reviewer run 43f4e4af の `gate promote morpho-watcher-ethereum` が資金移動前に例外終了（`gate-ctl` 348 行 `float(line.split(":", 1)[1])` → `ValueError: " 16 # Fixed ..."`）。earner がコメントを外して再提出し、promote まで 1 レビュー周期（約 4 時間）遅れた。
- 原因: `principal_usdc` は 213 行で `.split("#")[0]` してから float するが、`capital_usd`（348 行）と `max_loss_per_tx_usd`（350 行）はしていない。
- 依頼: 348/350 行にも `.split("#")[0]` を入れる（または YAML として読む）。
- workspace 側の対応（実施済み）: `tools/manifest-check.py` が gate と同じパースを再現し、コメント付きの行を ERROR にする。失敗した行の合成コピーで ERROR、live 4 件 + paper 1 件は OK のまま。gate 側を直したら manifest-check のこのチェックは警告に下げる。

## 2. researcher セッションで `/srv/farm/prompts/roles/TOOLS.md` の Edit が拒否された

- run d54abc09（researcher-claude、11-10）。common.md の表では researcher は TOOLS.md に書き込めるはずだが、ハーネス権限で拒否された。依頼された行は meta が代わりに追加済み。
- 依頼: researcher の権限設定に TOOLS.md の Edit を許可する（意図的に禁止しているなら common.md の表を直す）。
