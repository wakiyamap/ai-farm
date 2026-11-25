# 2026-11-06 L を 50 USD に引き上げ、USD 換算は署名時点の価格（人間 → paper-reviewer / earner / meta）

## 判断

1. **L（1 tx の最悪損失の上限）を 20 USD から 50 USD に引き上げる。** phase 6r で gate.json の `max_loss_per_tx_usd` を 50 にし、signer の署名チェックと watchdog の停止条件もこの値になった。X（2000 USD）、日次損失上限（200 USD）、Base のガスウォレット上限（18 USD）は変えない。
   - 理由: Ethereum mainnet で 20 USD に収めると、手数料上限を 1〜2 gwei 台にするしかなく、ガスが跳ねた局面（機会が集中する局面）で tx がブロックに入らない。
   - 各 bot の manifest の `max_loss_per_tx_usd` は自動では変わらない。上げたい bot は manifest を書き直して再提出し、reviewer がその値（≤ 50）で判断すること。
2. **L の USD 換算は署名時点の価格で行う。** tx が保証するのはネイティブ単位の上限（`gasLimit × maxFeePerGas + value`、Base は加えてガスウォレット残高の上限）で、それを USD にするのは signer が署名直前に読む ETH/USD 価格でよい。signer は既にこの計算で L を超える署名を拒否している。
   - reviewer は「inclusion 時点で ETH 価格が急騰したら USD 換算で L を超えうる」ことを理由に fix にしないこと。署名から inclusion までの価格変動は L の対象外。bot 側の価格フィルタや余裕を持たせた上限は歓迎するが、promote の必須条件ではない。
   - reviewer が確認するのは (1) 署名される `gasLimit × maxFeePerGas + value` がネイティブ単位で固定されていること、(2) 署名時点の価格でそれが manifest の `max_loss_per_tx_usd`（≤ 50）以下になること、の 2 点で十分。
