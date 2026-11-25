# meta 26f8b1fd（2026-11-17 15:1xZ）: HAI の記録、Base のエクスプローラ、トライアル枠

## 1. HAI の知見を wiki に記録しました（ご依頼 2026-11-17-human-hai-stop-usdc.md 1 項）

- 新ページ `pitfalls/opstack-first-block-index.md`：base / optimism で「最初の取得可能ブロックの tx index 1 に既存勝者がいる」ジョブは、手数料を上げても前に出られない（HAI 100 送信 0 勝、56 件の同一ブロック負けで勝者は常に index 1、43 件中 11 件はこちらの手数料が勝者以上）。過去 20 件の取得 index が 1-2 なら作らず `blocked_infra` にする、と書きました。
- builder.md のトライアル節に 1 文追加（「base / optimism で index 1-2 に取得が集中する first-block ジョブはトライアル対象外」）。builder の組み立てサイズ 49929 → 50070 バイト（上限 56000 以内）。
- 計測指標：今後 base / optimism で HAI 型（first-block, index 1 勝者）のトライアルが置かれた件数。目標 0。

## 2. Base のコントラクトソース取得経路がありません（判断をお願いします）

- scout 4a91a6a4 の計測（11-17）：Routescan は Base 非対応になり（`chain not supported`）、Etherscan V2 はキーなしで拒否、`explorer` ツールでは base は `not_on_plan`。
- base.blockscout.com の API は Cloudflare のボット判定で 403。特定の Safari の User-Agent を名乗ると通ったそうですが、**UA 偽装でボット判定を抜けるのは CAPTCHA / 429 回避と同類と判断し、wiki（`infra/explorer.md`）で使用禁止と明記しました**。
- 代替（GitHub、DefiLlama アダプタ、relay の `eth_getCode` / selector probe / `debug_traceCall`、`eth_getLogs`）で今のところ scout は判定できています。
- 提案：Base（と optimism / bsc / avalanche）のソースが頻繁に必要なら、Etherscan の有料プランか Blockscout の API キーを検討してください（費用はそちらの判断）。不要なら現状のままで構いません。

## 3. トライアル枠と live の状況（gate status 15:07Z）

- live 11 本（うちトライアル 8 本：aave-arbitrum, aave4-base, cv3-buy-base, flux-bsc, morpho-cbbtc-base, morpho-eth-base, morpho-whype-hyperevm, revert-lend-arbitrum）。上限 10 まで残り 2 枠。本日損失 0.62 USD、資本 959.86 USD。
- HAI 停止後、live 全ボットのログに送信イベント 0 件（nonce もすべて 1 = executor デプロイのみ、morpho-nextblock のみ 2）。
- 待機中のトライアル（reviewer 09:18Z メモ）：cv3-buy-arbitrum, cv3-buy-optimism, cv3-buy-polygon, feusd-redeem-hyperevm, morpho-khype-hyperevm。ご指示どおり cv3-buy-optimism を先頭にするのは reviewer の判断に任せています。
- trial-cv3-buy-polygon は USDC.e で受けた余剰を同じ tx 内で native USDC（0x3c49…3359）に売る作りになっていることを確認しました（ご依頼 2 項は対応済み）。

## 4. Aave トライアルの「103 % cover が複数担保の借り手で revert」報告（builder 6e7cdbee）

- live の trial-aave-arbitrum はこの方式ではなく固定の小さい cover（WETH 0.1 / USDC 300）を使っており、live ログに `simulate_revert` は 0 件。live 側の修正は現時点で不要と判断しました。paper の trial-aave-base / -polygon への移植は builder の fix 対象です。

## 5. 前回の変更の計測

- paper-reviewer.md「gate promote の前に review.md を書く」：変更後の昇格 1 件（trial-flux-bsc）は review.md に promote 記録あり（変更前は live トライアル 10 本中 6 本が記録なし）。維持します。

## 6. 研究者 8 回/日の件

- 2026-11-17-human-researcher-8-runs.md の計測依頼は、その後の phase 14a で researcher タイマーが停止されたため対象外としました（研究者の最終 KB 書き込み 11-16 19:16Z）。代わりに 11-17 の新規 leads は builder 13 件、scout 11 件です。phase 13a（earner-claude）の 8 セッション報告も同じ理由で対象外としています。違う意図でしたらお知らせください。
