# meta 提案（2026-11-04 run bfec56e0）

## 1. 資金：最初の promote 候補が gate の残高不足で止まった（判断をお願いします）

- `cv3-buy-watcher-ethereum`（Compound v3 buyCollateral、ethereum）は reviewer a41d9200 が executor の仕組みを独立に再現しました（fork で成功 +17.27 USDC、NO_PROFIT のときは revert して元本は戻る、署名上限 450000 gas × 1.5 gwei）。`gate promote` は `intermediate wallet on ethereum has less than 400.00 USD + gas; deposit first` で拒否されました（reviewer はこれを最終判断として扱い、回避はしていません）。
- `gate status` の capital は 77.28 USD です。この bot は 1 回あたり元本 398 USDC を使う設計なので、入金されない限り ethereum で live にできる bot はありません。
- ただし入金されても、すぐに promote できるわけではありません。reviewer の残りのブロッカーは「自然発生した機会で、署名する手数料上限で取り込めること」です。過去の absorb ブロックの basefee は 14〜16 gwei で、bot の上限 1.5 gwei を上回っていました。
- お願い：ethereum の intermediate wallet に約 420 USD（USDC 400 と gas 用 ETH）を入れるかどうかの判断。入れない場合は、earner に「ethereum の元本 bot は資金が付くまで作らず、flash loan で元本を調達する設計にする」と指示するため、その旨を decisions に書いてください。X（2000 USD）の範囲内です。

## 2. 共有 fork を予約できる仕組み（lease）か、リセットごとの世代 ID

- 今日は、別のセッションが共有 fork を reset したため測定が無効になった、あるいは fork がタイムアウトした、という報告が inbox/meta に 3 件来ました（b44cbd98, 9328b6b6, 154fb2fe）。`fork replay` も内部で re-fork するので、ほかのセッションの状態を消します。
- meta 側の対応：手順と既知の症状を wiki `pitfalls/shared-fork-concurrency.md` にまとめ、TOOLS.md の fork の行からリンクしました。
- 提案：`fork status` / `fork send` が reset の世代 ID を返し、send 時に期待する世代と違えば失敗する仕組み。または、チェーンごとの短時間の advisory lease。fork ツールは workspace の外にあるため、meta からは変更できません。

## 3. meta の git について（11-05 の決定 §2 への報告）

- コマンドは denied にはなりませんでした。ただし `git -C /srv/farm/ws log --since="3 days ago" ...` は `fatal: not a git repository` で終わります。/srv/farm/ws 自体が git 管理されておらず、git 管理されているのは wiki/ だけのようです。
- そのため、tools/ や prompts/roles/ の変更履歴は meta から確認できず、session context の「commits」欄も空でした。tools/ と prompts/roles/ を git 管理にする（またはそのコミット一覧を session context に入れる）ことを提案します。
