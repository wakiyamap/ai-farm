# 2026-11-07 meta（run bc2afbe7）からの依頼 3 件

## 1. earner の `web_search` がまだ使えない（プロバイダ未登録）

- 2026-11-07-websearch の決定のあと、earner のセッション報告で web_search に触れたものは 2 件（run afdb769d、55079588）で、どちらも `configured web provider "rustxng" is not registered` というエラー。成功の報告は 0 件。
- `websearch` CLI そのものは動く（meta が 2026-11-07 に `websearch "aave liquidation" -n 3` で結果 2 件を確認）。したがって、earner のハーネス（dsh）の設定にプロバイダ `rustxng` が登録されていないと思われる。
- 依頼: dsh の web プロバイダ登録を確認してほしい。それまでの回避策として、TOOLS.md の web の行に「web_search がエラーならシェルで `websearch` を実行」と書いた。

## 2. relay の `alchemy_getAssetTransfers` が HTTP 400

- earner run 123bba62 の報告: arbitrum と ethereum で、最小のパラメータでも完全なパラメータでも、すべて `alchemy: HTTP 400` が返る（research lane、予算は残っていた）。
- meta は curl を実行できないので再現していない。relay の Alchemy への転送（ネットワーク設定かパラメータの渡し方）を確認してほしい。直らない場合は、TOOLS.md からこのメソッドを外す。

## 3. KB の protocol 名をアンダースコアに直せない

- 2026-11-07-relay-latest §2 の指示どおり、ハイフン表記の 6 行（protocols 37/38 `radiant-v2`、41 `aave-v4`、46 `liquity-v2`、48 `surge-credit`、49 `gearbox-v3`）を直そうとした。しかし `kb update` は `['protocol'] identify the row and can't be changed; add a new row instead` で拒否した。workspace には `tools/kb/` が無いので、meta はマイグレーションも書けない。
- 新しい行を足すと重複が増えるので、足していない。代わりに TOOLS.md の KB write の行に、命名規約と「両方の表記で query してから add する」を書いた。
- 依頼: (a) 人間がこの 6 行の protocol 列を直接書き換える、または (b) 名前変更を kb に追加する（revisions に記録が残る形で）。どちらかをお願いしたい。leads 42/48 の target にもハイフン表記が入っているが、target も行を識別するキーなので同じ扱いになる。
