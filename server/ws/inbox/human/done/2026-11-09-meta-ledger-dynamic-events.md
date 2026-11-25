# ledger add-source: 動的型・タプル型を含むイベントの追跡（meta b07502ea, 2026-11-09）

2026-11-07 の決定 §4「タプル型のイベントが必要な bot 候補が実際に出てきたら、もう一度挙げること」に従い、再提案します。現在、該当する候補は 2 件あります。

1. **reserve-folio-dtf-ethereum（paper bot、レビュー中）**: 待っているイベントは Folio の `AuctionOpened`（タプル型を含む）。ledger で追跡できないので、earner が毎回 relay で手動スキャンしている（run d05d4be0、inbox/meta/ledger-addsource-no-tuples.md）。
2. **lead 105（Uniswap fee-releaser、3 チェーン）**: `Released(uint256 indexed nonce, address indexed recipient, address[] assets)`。必要なフィールドはすべて indexed で、動的なのは data 部の `address[]` だけ（inbox/meta/2026-11-09-researcher-claude-ledger-dynamic-event.md）。

## 提案（最小の変更）

source の定義で `"data": []`（または先頭の静的ワードだけ）を宣言できるようにする。topic0 はこれまでどおり完全なシグネチャの keccak で検証し、daemon は data の残りを読まない。デコードの変更は不要で、CU は増えない（Released は 3 チェーン合計で 1 日約 5 件、アドレスで絞り込み）。

## 判断してほしいこと

- この変更を入れるかどうか（ledger-ingest はワークスペースの外にあるため、meta には変更できない）。
- 入れない場合は、そのまま relay-log-scan で手動追跡を続ける（現状どおり）。
