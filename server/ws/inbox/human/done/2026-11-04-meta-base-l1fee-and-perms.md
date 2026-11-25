# meta からの提案（2026-11-04, run bc2c984a）

## 1. Base（OP Stack）での L の「手数料上限」の扱いを決めてほしい（リスク制限の解釈なので人間判断）

- 状況：paper-reviewer は morpho-watcher-base を 021de292 / 511fc3e7 / 2d13ac44 / 99cc9216 / 54ffa8cc の 5 回連続で fix にしています。毎回のブロッカー 1 は同じで、「Base の L1 data fee と operator fee は署名済み tx のフィールド（maxFeePerGas × gasLimit）で上限が決まらない。だから L の『最悪損失 = gas、上限は tx 自体が保証』が成り立たない」というものです。根拠は OP Stack の仕様（exec-engine / isthmus）です。
- 帰結：この解釈のままだと、**Base 上の bot はどれも L を満たせません**。現在の推定は約 $0.67/tx で、$20 よりずっと小さいです。earner は live 送信を無効にして回避しました（3c4a3b75, LIVE_FEE_CAP_ENFORCED=false）。Arbitrum は L1 コストが L2 gas に含まれるので、この問題はありません。
- 提案（いずれかを選んでください）：
  - (a) **gate が Base bot のネイティブ ETH 残高の上限を強制する**（例：$18 相当まで）。1 tx の手数料はウォレット残高を超えられないので、これで上限がコードで保証されます。reviewer は「gate の不変条件として示されていない」と退けていたので、gate 側の強制として明文化してください。
  - (b) common.md の L に「OP Stack の L1/operator fee は、送信直前に推定した値の N 倍以内であれば可」といった許容範囲を書く。
  - (c) 現状を維持する（Base は live 不可）。その場合は earner の Base 向け作業を止めたいので、そう明記してください。

## 2. meta の許可リストがまだ効いていない

`decisions/human/2026-11-04-session-logs.md` では、meta に `python3 /srv/farm/ws/tools/*` と `git -C /srv/farm/ws log/show/diff/status` を許可したとあります。しかし今回の run では、`git -C /srv/farm/ws log --oneline -40` も `python3 /srv/farm/ws/tools/session-report.py coverage --date 2026-11-04` も denied でした。動くのは `kb` と `ledger` だけです。そのため commit 単位のレビューができず、今回もファイルを直接読んでレビューしました。

## 3. scratch のファイルが 0600 で作られる件（2 回目）

511fc3e7 では scratch/morpho-econ/fork-verify.js が、54ffa8cc では scratch/cv3-eth/contracts/src/Cv3Sniper.sol が、mode 0600 earner:earner で reviewer から読めませんでした。default ACL を設定しても、earner 側の umask か chmod で mask が落ちているようです。earner ユーザーの umask を 0027 に固定する方法を検討してください。
