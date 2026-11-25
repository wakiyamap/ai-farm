# meta 2026-11-18 22時台 (run 096358ac): 判断をお願いしたい4点

## 1. farmbot_signer の priority fee 0 が maxFee/10 になる(ライブラリ修正の提案)
`/opt/farm/lib/farmbot_signer.py` の `send()` は `max_priority_fee_per_gas or max_fee_per_gas // 10` で tip を決めています。明示的な `0` は偽と扱われ、tip が maxFee の 1/10 になります(paper-reviewer-claude run 51c32068 が trial-bim-harvest-base で発見。manifest は「priority fee 0%」と記載)。損失上限 L は変わりません(署名する maxFee × gasLimit は同じ)が、bot や manifest の記載と実際の入札が食い違います。
- 提案: ライブラリ側を `if max_priority_fee_per_gas is None` に修正(ワークスペース外なので meta では変更できません)。
- それまでの対応: wiki `pitfalls/signer-zero-priority-fee.md` を作成し、TOOLS.md の signer 行に「0 ではなく 1 を渡す」と追記しました。

## 2. no_report になった run の claim を自動で失効させる(ハーネスの提案)
builder run a28ea6d9 が異常終了(no_report)した後も、その claim(18:40Z 期限)が残っていたため、次の builder(b5adb628)は作りかけの trial-llamalend-arbitrum に手を付けられず、1セッションが無駄になりました。
- builder.md に「`logs/sessions/` に行がある run(no_report 含む)の claim は無効、引き継いでよい」と追記済みです。
- 提案: ハーネスが no_report 行を書く時に、その run の `claims/` ファイルの `expires_at` を現在時刻に書き換える。プロンプトに頼るより確実です。

## 3. bsc: 15f の後も public node は eth_getLogs を拒否
15f(bsc-dataseed.binance.org 追加)の後、scout レーン予算超過時(11-18 20:40Z、305,900/300,000 CU)に scout run 9a729ceb が試したところ、bsc の `eth_getLogs` は対照クエリ(RDNT Transfer)も含めて毎回 `all providers failed: public: limit exceeded` でした。`eth_call` 等も約3回に1回 `no provider available`。予算が切れた後の bsc ではイベント集計が一切できません。
- 選択肢: (a) bsc の getLogs だけは scout レーン予算超過後も Alchemy に回す、(b) getLogs を返す別の public bsc ノードを追加、(c) 現状維持(wiki に「状態 getter で判定」と記載済み)。meta の推奨は (a) を小さい上限付きで。

## 4. HyperEVM 中間ウォレットの HYPE 不足(trial-felix-liq-hyperevm)
gate status(21:3xZ): hyperevm 中間ウォレット 8.24 USD、elysium 4.93 USD。承認済みで待機中の trial-felix-liq-hyperevm は capital 10 USD を要求しており、枠が空いても promote は資金不足で拒否されます。HyperEVM に約 20 USD 分の HYPE 補充をご検討ください(他の待機 trial の分も含め)。

参考: live 33 本、本日の損失 0、capital 1017.99 USD。14日間検知も送信もない live bot はありません(最古の gearbox-v3-watcher-ethereum は 11-09 promote)。
