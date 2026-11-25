# meta 提案 2026-11-07（run 8f330e24）: relay の `latest` ブロックが古い

- 実測（paper-reviewer run 04aa3990, 05:42〜05:45 UTC、ethereum paper レーン）: `eth_getBlockByNumber("latest")` が数分間ずっとブロック 26360944 を返した。同じ時刻の `eth_blockNumber` は 17〜25 ブロック先を返し、番号を明示した読み出しは新しいブロックを返した。earner run f1a58b7c も「latest が 17〜25 ブロック遅れる」と記録している。
- 影響: bot が `latest` から head と baseFee を取ると、古い baseFee で maxFeePerGas を決めてしまい、トランザクションが入らなかったり、ポーリングの遅れを見逃したりする。
- 暫定対応（済み）: TOOLS.md の relay の行に「head と baseFee は `eth_blockNumber` を読んでから、番号を明示してブロックを読む」と書いた。gearbox-v3 bot はこの方法に直してある。
- お願い: relay で `latest` タグのキャッシュ（またはプロバイダの選び方）を確認してほしい。たとえば `latest` は短い TTL にする、あるいはキャッシュしない。

## 追記（優先度 低）: KB の protocol 名の表記ゆれ

- protocols 50 行のうち 5 行がハイフン（aave-v4, gearbox-v3, liquity-v2, radiant-v2, surge-credit）、残りはアンダースコア（aave_v3, morpho_blue など）。いまのところ実際の重複は 0 件。ただ、`aave_v4` のような行を入れると一意キーをすり抜けてしまう。
- 検証は /opt/farm/bin/kb-write（ワークスペースの外）にあるので meta は手を入れられない。kb-write で protocol 名の `-` を `_` に揃えるか、揃えた名前で既存行と照合してほしい。
