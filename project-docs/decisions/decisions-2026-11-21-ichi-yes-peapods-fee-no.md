# ICHI vault の預け入れ→引き出しは試してよい、Peapods の買い手数料の回避は絶対にしない（人間の判断 2026-11-21）

inbox/human の 2 件（`2026-11-20-ichi-vault-flash-deposit-withdraw.md`、`2026-11-20-peapods-buy-fee-bypass.md`）への答えです。

## 1. ICHI vault（HyperEVM の Nest の IV-NEST vault）: やってよい

1. 人間の判断: これは典型的な vault の会計への攻撃ではなく、vault の預け入れ・引き出しの値段とプールの値段の差を使う裁定です。S（迷ったら不可）には当たりません。
2. attempts:2964 の「真似しない」は取り消します。builder は通常の試行の bot として作ってかまいません。`2026-11-17-cheap-chain-trials.md` の条件（1 本 20 USD 以下、1 送信の損 1 USD 以下、7 日で締める）、fork の証明、作り手と逆のモデルの審査はそのままです。
3. 1 回の額は小さい（読んだ tx で 0.0066 USDC）ので、ガスを引いて残るかを先に測ってください。残らなければ dead_end で閉じてかまいません。

## 2. Peapods の pod の買い手数料を Uniswap V2 Router02 の例外で回避する経路: 絶対にしない

1. 人間の判断: Sherlock で報告済みの問題であることを人間が確認しました。farm はこの経路を mainnet でも fork でも使いません。測り直しもしません。ほかのチェーンの pod や、同じ形の手数料の例外（転送先をルーターにして手数料を外すもの）も同じ扱いです。
2. **確認のお願い（meta、次の回で）**: live の `trial-peapods-arb-arbitrum`・`trial-peapods-arb-base`・`trial-peapods-base` と、paper にある Peapods の bot が、pod を買うときに Router02 を受け取り手にして手数料を外していないかを、bot.py と executor のソースで確かめてください。
   - 外していれば、その bot はすぐに `gate stop` して、inbox/human に書いてください。
   - 外していなければ、確かめたことを inbox/human に 1 行で書いてください。
3. Peapods への連絡は人間が判断します。farm からはしません。
