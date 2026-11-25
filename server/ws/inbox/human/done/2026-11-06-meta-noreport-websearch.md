# 2026-11-06 meta（run 0a92961d）: no_report の分類、web_search の鍵、11-06 判断の未実施

## 1. no_report の分類（decisions/human/2026-11-06-kb-json-noreport.md への回答）

`last log:` が付いた no_report は 3 件（11-05 夜〜11-06）。

| run | 役割 | 終了 | last log の内容 |
|---|---|---|---|
| 17b72968 | earner | exit 0 | 作業途中の推論（fork 状態・KB フィールド長の検討）。エラー行なし |
| d8d8d13d | earner | exit 0 | 「残り 24 分、記録する」と書いた直後に終了。時間切れ |
| 8ca392bf | earner | exit 1 | GMX wrapper の fork probe 途中の推論。エラー行なし |

- 3 件ともローカル LLM サーバーのエラー・タイムアウトを示す行はなく、**エージェントが作業途中で止まっている**。exit 0 の 2 件はセッション時間切れまたはターン上限、exit 1 の 1 件は原因不明（journal の行に error が出ていない）。
- 3 件とも `scratch/report-<run_id>.json` の下書きも残っていない（earner.md 手順 4 で「作業前に下書き」と指示済みだが守られていない）。
- 提案（ハーネス側、人間の判断）: セッション終了時に `scratch/report-<run_id>.json` があればハーネスがそれを追記する。なければ今の no_report 行のまま。これで「下書きはあったが追記前に切れた」場合を救える。

## 2. web_search が使えない（earner、qwen 系）

earner の `web_search` が `DeepSeek search has no API key for "DEEPSEEK_API_KEY"` で失敗している（inbox/meta/web-search-deepseek-key.md, b2176d12-websearch-no-apikey.md、11-06 に 3 セッションで発生）。earner は web_fetch と GitHub API で回避中。鍵の登録か、別の検索バックエンドへの切り替えが必要（鍵・有料サービスのため人間の判断）。

## 3. 11-06 判断（no-latency-race）がまだ実施されていない

- paper に aave-watcher-ethereum / -arbitrum / -base、morpho-watcher-base が残っており、判断後に gmx-liquidation-arbitrum（ロール制限、対象外）が新たに置かれた。earner.md と paper-reviewer.md に `decisions/human/` を読む指示がなかったのが原因。
- 対応: 両ロールファイルに「直近 3 日の decisions/human を最初に読む、対象外の bot は demote」を追加。KB の lead 22（GMX）を dead_end、lead 17（Aave Ethereum）を blocked_infra に更新。次回の meta で、対象外の paper bot 数（現在 5）が 0 になったか計測する。

## 4. 参考（対応不要）

GMX の ledger source は ledger-ingest の check_source がタプル型イベントを受け付けず登録できない（inbox/meta/gmx-ledger-source-eventlog2.md）。GMX は対象外になったので変更は不要と判断。
