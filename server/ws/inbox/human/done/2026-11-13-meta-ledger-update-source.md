# 提案: ledger の source を差し替える手段（meta 6d8f8ade、2026-11-13）

## 提案
`ledger add-source` は同じ id の source があると拒否します（`a source with id ... already exists`）。誤りのある source を直す正規の手段（例: `ledger update-source <spec>`、検証は add-source と同じ）を用意していただけないでしょうか。急ぎではありません。

## 背景
- researcher cf4d9061 が 11-12 に入れた `concentrator.vault_harvest` に、旧型の emitter `0xc8fF37F7d057dF1BB9Ad681b53Fa4726f268E0e8` が混ざっています。この emitter のイベントは `Harvest(address,uint256,uint256,uint256)` で、spec の 6 引数のイベントとは別物なので、この 1 アドレスは何も取り込みません（害はなく、毎回の getLogs の対象が 1 つ余分なだけです）。
- 正しい 4 アドレスの spec: `scratch/concentrator-cf4d/concentrator.vault_harvest.json`（元の spec は同じディレクトリの `-installed.json`）。ledger のファイルを直接書き換えることはしていません。
- 出典: inbox/meta/2026-11-12-concentrator-source-maintenance.md

## 費用
なし。

## 判断のしかた / 元に戻せるか
差し替え後、`tools/ledger-source-coverage.py --source concentrator.vault_harvest` で emitter が 4 つと表示されれば完了です。差し替えは元の spec を入れ直せば戻せます。
