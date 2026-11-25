# 2026-11-07 web_search・getAssetTransfers・KB キー（inbox/human/2026-11-07-meta-websearch-assettransfers-kbkeys.md への回答）

## §1 earner の web_search

- 原因は phase 8 の入れ方の誤りだった。プロバイダのパッケージを dsh 本体の node_modules に置いただけで、dsh はそこから読み込まないので登録されていなかった。
- phase 8a（2026-11-07 21:22 JST）で、正式な dsh バンドルとして headless プロファイルに `dsh plugin add` した。このあとに始まったセッションでは「not registered」のログは出ていない。meta が数えた 2 件は、8a より前に始まったセッションのもの。
- 次回の meta で、21:22 JST（12:22Z）以降の earner セッションに限って、web_search の成功と失敗を数え直すこと。TOOLS.md の回避策（web_search がエラーならシェルで `websearch` を実行）は残してよい。

## §2 relay の alchemy_getAssetTransfers

- relay の転送は正常。人間が relay の research lane から、ethereum で `alchemy_getAssetTransfers` を実行して結果が返ることを確認した（パラメータは `fromBlock`/`toBlock`/`category:["external"]`/`maxCount:"0x1"`/`toAddress`）。HTTP 400 は earner のパラメータの書き方が原因（よくある誤り: `maxCount` を 16 進文字列にしていない、`category` の値の誤り、`fromAddress`/`toAddress` にチェックサムでない値や配列を渡す、`excludeZeroValue` などの型違い）。
- phase 6x から、relay は上流の HTTP エラーに Alchemy の理由文を付けて返す（`alchemy: HTTP 400 <理由>`）。エラーが出たら、まず理由文を読んで直すこと。TOOLS.md からこのメソッドを外す必要はない。上の動いた例を TOOLS.md に載せること。

## §3 KB の protocol 名

- phase 6x で、人間がバックアップを取ってから protocols の 6 行を直接書き換えた: 37/38 `radiant_v2`、41 `aave_v4`、46 `liquity_v2`、48 `surge_credit`、49 `gearbox_v3`。
- leads の target は説明文なので書き換えていない（ハイフンを含んでいてよい）。今後の protocol 名は、小文字とアンダースコアで書くこと。
