# 2026-11-05 reviewer 専用 fork と lease 履歴（inbox/human/2026-11-05-meta-reviewer-fork.md への回答）

両方 phase 6m（2026-11-05 適用）で入れた。

## 1. reviewer 専用の ethereum fork

- `ethereum-review`（127.0.0.1:9013、chain id 1、relay の ethereum を上流にする anvil）を追加。fork CLI で `fork status` / `fork reset ethereum-review <block>` / `fork replay ethereum-review <tx>` / `fork send ethereum-review …` のように、チェーン名の代わりに `ethereum-review` を指定する。
- nftables で earner ユーザーと bot ユーザーからは 9013 に到達できない。使えるのは harness で動く役（paper-reviewer、meta、researcher）だけ。earner の lease と衝突しない。
- paper-reviewer: ethereum の fork 証拠の再現は `ethereum-review` で行うこと。earner の `ethereum` fork を reset / replay してはいけない（読むのは可）。meta は paper-reviewer.md をそう直すこと。
- base / arbitrum は世代番号 0 で衝突が無いので専用 fork は作らない。必要になったら同じ方法で足せる。

## 2. lease の履歴

`scratch/.fork/<chain>.lease.log` に 1 行 1 JSON で `lease`（取得、minutes・note・世代）、`release`、`force_over_lease`（他 run の lease を --force で上書きした）を追記する。期限切れは行にならないので、`lease` の at + minutes と次の `release` の有無から求めてほしい。
