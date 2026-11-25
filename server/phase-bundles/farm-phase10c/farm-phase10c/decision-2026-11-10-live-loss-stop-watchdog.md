# 累計損失 30 USD の停止は watchdog が行う（人間の判断 2026-11-10）

- 11-10 の phase 10c から、watchdog（コード）が live bot ごとに「promote 以降の損失」を毎周回計算し、30 USD（gate.json `max_live_loss_usd`）を超えたら `gate stop` する（sweep して archive、live-operator を起こす）。
  - 損失 = gate が送った資金（pnl.json の baseline。後の `gate fund` や sweep 時のガス補充を含む。ネイティブと USDC）− いまの bot wallet の残高（現在の Chainlink 価格で評価）
  - bot の wallet の外（executor、vault など）に置いた利益や元本は、損失として数える（安全側）。executor は利益を bot の wallet に返す作りにすること
- promote 基準 5（live 試行の累計損失 30 USD で止まる）は、これで満たされたものとする。
  - paper-reviewer は、bot 自身の損失記録のクラッシュ耐性（state.json の破損、送信と記録のあいだのクラッシュ、署名応答の曖昧さなど）を promote の阻害要因にしない
  - bot 側の自己停止はあってよいが必須ではなく、簡単なもので足りる
  - reserve-dutch-ethereum は、残っている fix 項目が基準 5 のクラッシュ耐性だけなら、それを理由に fix にしない。他の基準（仕組みの再現、配備、L、検知）で判断する
- 1 tx の最悪損失（L）、日次損失（n）、1 周回の急減（L 超）での停止は、これまでどおり gate / signer / watchdog が強制する。
- meta: paper-reviewer.md と earner.md の基準 5 の記述を、この判断に合わせて改訂すること。
