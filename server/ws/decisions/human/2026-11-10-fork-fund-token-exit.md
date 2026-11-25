# 2026-11-10 fork fund-token の終了コード（inbox/human/2026-11-09-meta-fork-fund-token-exit-code.md への回答）

phase 9h で入れた。

- `fork fund-token` は、なりすましの transfer が失敗した（status が 0x1 でない）とき、`FAILED ...` を表示したあと、理由を stderr に出して **終了コード 2** で終わる。レシートが来ない場合は、従来どおり die（終了コード 1）。成功時は従来どおり 0。
- スクリプトから使う場合は、終了コードで判定してよい。失敗したら、holder の残高を `balanceOf(holder)` で確かめて別の holder を選ぶこと。
- あわせて `ledger` のヘルプを、phase 9d の動的型・タプル型のルールに更新した（「Only static ABI types」の記述は削除）。

## 指示

- **meta**: この inbox 項目を RESOLVED.md に入れること。TOOLS.md の fork の行に「失敗時は終了コード 2」を書き足すこと。
- ethereum-review の fork（9013）の停止（inbox/meta/2026-11-09-ethereum-review-fork-down.md）は、人間が再起動した。再起動後も止まるようなら、`journalctl -u fork@ethereum-review` の末尾を添えて inbox/human に出すこと。
