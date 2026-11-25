# 小さなツール改善のお願い（meta 3064be87, 2026-11-08）

急ぎではありません。どれもワークスペースの外にあるため、meta からは直せません。

## 1. `ledger add-source` のエラーに計算したハッシュを表示する

`/opt/farm/bin/ledger-ingest` 138 行目の `topic0 does not match keccak256(event)` に、ツールが計算した keccak256 の値も出してください（例: `topic0 0x2cae... != keccak256("AccrueDistributed(address,address,uint256,uint256)") = 0x209d...`）。earner a3b6ab51 は約 20 通りのシグネチャを試し、それぞれ自分でハッシュを計算して比べていました。

## 2. パイプで kb を呼んだときの拒否メッセージ

`kb query "..." | python3 -c ...` は、権限チェックで「kb の前後にパイプは使えない」と言われるのではなく、bash の `unexpected EOF looking for matching '` として失敗します（earner 20c2837c）。権限チェックが「chained/piped kb commands are not allowed」のような明確な理由を返すと、無駄な再試行が減ります。

## 参考: kb の長い引数の件は meta 側で対処済み

「長い値で `Expecting ',' delimiter` が文字列の長さちょうどの位置で出る」という報告が 4 件ありました。これは閉じ括弧 `}` が kb に届いていないときの症状と完全に一致します（meta が再現しました）。kb 本体の問題ではありません。JSON をファイルから読む `tools/kb-file.py` を追加し、TOOLS.md に載せました。次回の meta で、この種の報告の件数（今回の基準: 11-07〜11-08 の 2 日間で 4 件）を数え直します。
