# pull-oracle-markets（第 1 版・暫定）— meta f1ef7ed7、2026-11-14

decision 2026-11-14-taker-types-pull-oracle の 2 の一覧です。researcher（opus, run 095e4f2d）の第 1 版を訳して要約しました。本体は wiki `infra/pull-oracle-markets.md`（attempts 1187, 1188）。Dolomite（arbitrum）と Fluid（ethereum/arbitrum/base）はまだ見ていません。researcher は「大きな貸付市場の結論は変わらない見込み」としているので、先に出します。残りの行が埋まったら第 2 版を出します。

## 結論

**「取られるまでの秒数が R（3 秒）を超え、粗利が 30 日で 300 USD 以上」に当たる市場は 1 つもありません。** 誰でも使える P 型（Pull 型）の取り手で、意味のある額を取っているものは見つかりませんでした。

- Base と Arbitrum の大口の清算は P 型ではなく **O 型（オークション）** です。急落の 72 時間で、Base Morpho の粗利の 97%、Base Aave の 92%、Arbitrum Aave の 84% が FastLane Atlas の `metacall`（清算の権利を売るオークション）を通っていました。farm は入札しないので D です。
- HyperEVM には P 型の取り手がいます（RedStone の署名つき価格を calldata に付ける形）。ただし Morpho の取り手も、Aave の fork（HyperLend 規模）の取り手も、入口が `NOT_AUCTIONEER` で revert します。権限のある auctioneer しか使えないので、取れません（fork で確認済み）。
- 誰でも使える P 型の取り手は 1 つだけ見つかりました。HyperEVM の小さな Aave fork のプール `0xcecce0eb…` で、Pyth の更新を tx の中で出しています。ただしそのプールの粗利は 7 日で約 14 USD、1 日約 2 USD です。
- Euler v2（Base 16 件・Ethereum 8 件 / 7 日）では、Pull 型の価格更新は 0 件でした。Ethereum の深い位置の送信元は不良債権の後始末で、利益は出ていません。Avalanche の Euler と Ethereum の Gearbox v3 は、急落の週でも清算が 0 件でした（同じ形の対照で確認済み）。Avalanche の Compound fork（Benqi 規模）は 46 件中 0 件が Pull 型でした。
- Ethereum の Aave と Morpho は Pull 型ではありません。取られた事例の半分以上は、`AnswerUpdated` の tx の 1〜3 つ後ろに並んでいます（B か O）。フィードが SVR か Standard かはまだ確認していませんが、どちらにしても D です。

## 判断をお願いしたいこと

- **価格配信を受ける仕組み（Pull 型 bot のための C の基盤）は、今は作らなくてよいと考えます。** 理由は、上の基準に当たる市場が 0 で、取れそうな唯一の市場が 1 日 2 USD だからです。第 2 版で Dolomite と Fluid に基準を満たす市場が出たら、改めて提案します。

## 関連

- 急落の事後検証（crash-postmortem）は、earner の 1-2 の残りの行が測れてから出します（researcher の依頼）。今のところ、「数える」に入り差し引き 1 USD を超える事例は 0 件です。測った範囲は、Ethereum Aave の 20 件と、Base Morpho の farm 向けの帯（attempts 1178/1179/1185）です。
- 相手の executor の解析で拾えそうな作りが 1 つあります。Atlas の solver は、OP Stack の L1 手数料（`GasPriceOracle` 0x42..0f）を tx の中で読み、ガス代を ETH で払い戻しています。「ガスの計算をコントラクトの中に入れる」という話に当たります。これは wiki `methods/executor-techniques.md` の表の 1 行目に入れました（効果は未測定）。上位 5 つがそろったら `executor-techniques` として出します。
