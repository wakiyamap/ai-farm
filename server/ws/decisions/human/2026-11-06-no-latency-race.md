# 2026-11-06 同一ブロック競争の清算は今は追わない（人間 → earner / researcher / paper-reviewer / meta）

## 判断

- **newHead 購読・mempool 監視・プライベートオーダーフローなどの高速インフラは、今は作らない。** 作るのは、ファームが live で**週 1000 USD 程度を安定して稼げる**状態になってから（実現 PnL で判断する）。その時点で人間が改めて判断する。それまでは要求しても用意しない。
- 計測で「大口は取られたブロックの中で HF=1 を越える（直前ブロックでは健全）」と分かったルートは、**待たずに止める**。paper bot は `paper archive <id> "<理由>"` で archive し、KB の lead は `blocked_infra` のまま残して、`next_steps` に「高速インフラ導入後に再開。週 1000 USD 条件を満たすまで手を付けない」と書くこと。計測結果は将来の再開に使うので消さない。
- 11-06 時点の対象: aave-watcher-ethereum、aave-watcher-arbitrum、aave-watcher-base、morpho-watcher-base、Base Morpho cbBTC/USDC のルート。少額だけ窓があるルートも、ガス後に利益が出ないなら同じ扱い。
- 理由: common.md 原則 2（レイテンシ競争を避ける）。オラクル更新の backrun は専業 searcher の領域で、今の資金規模と収益ではインフラ投資に見合わない。

## 続けるもの・優先するもの

- **窓が計測で示されているクラス**: SparkLend（大口が 54 ブロック以上前から清算可能、清算者は一度きりの参加者がほとんど）、Reserve 収益ダッチオークション（予定型、窓は十数時間）、Compound v3 の absorb 残り（cv3）、Morpho Ethereum の CATCHABLE と判定された事象。
- **ロールで制限されているもの（GMX v2 の onlyLiquidationKeeper など）は対象外。** 外部から参加できない仕組みは計測しなくてよい。
- researcher / earner の breadth: 「誰でも呼べる」「予定時刻が分かる、または窓が長い」「競合が少ない」の 3 つを先に確認してから深掘りすること。

## reviewer へ

- 同一ブロック競争と計測されたルートの bot は archive を提案してよい。promote 条件は変えない。
