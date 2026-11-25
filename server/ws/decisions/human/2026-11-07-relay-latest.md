# 2026-11-07 relay の latest が古い件（inbox/human/2026-11-07-meta-relay-latest-stale.md への回答）

## §1 原因と修正（phase 6w）

- 原因は relay のキャッシュだった。`eth_getBlockByNumber` は、ブロック番号を指定した確定済みのブロックを想定して 600 秒キャッシュしていたが、`"latest"` もそのまま同じキーでキャッシュしていた。`eth_getLogs`（toBlock が latest か省略、120 秒）と、ブロックを省略した `eth_getCode`（3600 秒）も同じ問題を抱えていた。
- phase 6w から、`latest` / `pending` / `safe` / `finalized` を指定したリクエストと、ブロックを省略したリクエストは、キャッシュを最大 1 秒にした。ブロック番号を指定した読み出しは、従来どおりキャッシュする。
- TOOLS.md の暫定対応（`eth_blockNumber` を読んでから番号を指定してブロックを読む）は、そのまま残してよい（害はない）。bot が `latest` で head と baseFee を読むのも、これで正しくなる。

## §2 KB の protocol 名の表記

- kb-write での自動正規化は行わない。規約で揃える: protocol 名は小文字とアンダースコア（`aave_v4`、`gearbox_v3`）。
- 新しい行を入れる前に、ハイフン表記とアンダースコア表記の両方で `kb query` すること。meta は、既存のハイフン表記 5 行をアンダースコア表記に直し（参照している行も一緒に直す）、この規約を TOOLS.md に書くこと。
