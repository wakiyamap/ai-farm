# meta 提案 2026-11-07（run cabdecb4）: ワークスペース外のツールの不具合 4 件

いずれも meta が直せない場所（harness、relay、ledger 本体）にある。件数は inbox/meta とセッションレポートから数えた。

## 1. web_search が使えない（DEEPSEEK_API_KEY 未設定）— 優先度 高

- 11-06〜07 の earner セッションのうち少なくとも 5 件（b2176d12, ef5b7c08, d9e9197b, d9e55b32 ほか）が「web_search に API キーが無い」と報告。web_fetch と DefiLlama は動く。
- 影響: アドレス探索を GitHub やエミッタースキャンで代替しており、1 セッションあたり数ラウンドの読み込みが余計にかかる。
- お願い: qwen/deepseek 系 harness の web_search にキーを設定するか、使えないなら harness からツールを外してほしい（エラーで 1 ラウンド無駄になるため）。

## 2. relay が eth_getTransaction を拒否（-32601）

- run b32cee72。calldata を読むには debug_traceTransaction（高 CU）を使うしかない。読み取り専用で安価なので許可リストに追加してほしい。

## 3. relay eth_getLogs のアドレス配列が 32 個以上で拒否

- run 2620f775（Euler 901 vault）。エラーは serde Variadic。上限が仕様なら TOOLS.md に書くので値を教えてほしい。

## 4. ledger add-source がタプル型のイベントを受け付けない

- run f80dc3ec（Dolomite LogLiquidate）。タプル成分を不透明な word として扱えれば足りる。急ぎではない（Dolomite は blocked_infra で閉じた）。

## 対応済み（参考）

- 11-07 決定 §1: earner.md 3b.2、TOOLS.md、wiki pitfalls/shared-fork-concurrency.md を「コンストラクタ引数を付けて再実行」に書き換えた。
- 11-07 決定 §3: tools/session-report.py が model を FARM_MODEL から埋めるようにした（渡された値が違えば notes に残す）。
- 11-07 決定 §2: 単独コマンドなら kb / wiki / python3 tools / git -C history / date はすべて通った。今回の最初の拒否は `cd … && …` の連結と `git -C /srv/farm/ws`（history ではない）が原因だった。
