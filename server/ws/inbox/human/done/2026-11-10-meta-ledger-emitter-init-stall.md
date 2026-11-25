# ledger: エージェント追加ソースの emitter 初期化が spec の順番どおりに途中で止まっている（meta 421c68f0、2026-11-10 20:3xZ）

判断のお願いではなく、ledger デーモン（ワークスペース外）の不具合報告です。研究者 run 3da38c54 の報告（inbox/meta/2026-11-10-ledger-emitter-initialization-coverage.md、tools/ledger-source-coverage.py）を meta が確認しました。

## 測定（`ledger query` の cursors、`python3 tools/ledger-source-coverage.py`）

- `beefy.charged_fees`（11-09 19:13 追加、ethereum 20 + arbitrum 20）: cursor があるのは **ethereum の spec 先頭 9 件だけ、ちょうど順番どおり**（0x4f94…, 0x0D3f…, 0xEA1C…, 0xDEF1…, 0x0C80…, 0xeE9B…, 0x3f08…, 0xAd4e…, 0xE577…）。9 件目 0xE577… だけ next_block 26382675 で遅れ、他 8 件は 26386714（先端）。10 件目以降と arbitrum の 20 件は約 25 時間 cursor なし。
- `reserve_folio.auction_opened`（11-09 08:10 追加、ethereum 20）: cursor があるのは **spec 先頭 11 件だけ、順番どおり**。11 件目 0x9f45… だけ 26378040 で遅れ、他 10 件は 26386714。12 件目以降の 9 件は cursor なし。
- 研究者の確認では、未初期化の 40 件はすべて eth_getCode が空でない（配備は存在）。

## 推定

emitter を spec の順に 1 件ずつ初期化しており、最後に初期化した emitter のバックフィル（遅れている 1 件）が終わるまで次へ進まない、または 10 件目/12 件目の初期化で毎 tick 失敗して列挙が止まっている。どちらも phase 9e の「ソースごと 600 CU/tick」の中で起きていると思われます。CU 予算を増やす提案ではありません。

## お願い

ledger デーモンのログで beefy.charged_fees の ethereum 10 件目 `0x175f5061F5eb2a2f30A2dACEFEdDd3EFd3a0911F` と reserve_folio.auction_opened の 12 件目 `0x5039ece83dc4e0621ebec391128339bd859a84d0` の扱いを確認してください。直れば `python3 tools/ledger-source-coverage.py` で initialized = configured になるはずです（meta が次回測ります）。それまで、この 2 ソースのイベント数ゼロはその emitter について「イベントなし」の証拠になりません。
