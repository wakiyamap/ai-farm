# 清算型の試行をやめ、単発の bot の本数の上限を外す（人間の判断 2026-11-22）

`2026-11-22-trial-slots-75.md`、`2026-11-20-trial-slots-45.md`、`2026-11-17-cheap-chain-trials.md`、`2026-11-14-oneshot-leftovers-idle-pull-oracle.md` に次の 2 つを足します。ほかの条件はそのままです。

## 1. 清算型の試行の bot は、新しく作らず、promote しない

理由: 試行の送信は、清算が 67 回で 9 勝、清算以外が 90 回で 68 勝です（wiki `methods/live-trial-send-census.md`）。大きい清算は、粗利のほぼ全額をビルダーに払う入札で決まっています（lead 14）。farm の送り方（公開の送信と Flashbots Protect）では勝てません。

- builder: 清算（liquidate、liquidation call、absorb、清算ボーナスを取る型）の試行の bot を新しく作らないでください。清算型の lead から試行を起こすこともやめます
- paper-reviewer / paper-reviewer-claude: paper にある清算型の試行の bot は promote しないでください。review.md に「清算型（2026-11-22 の判断）」と書いて park にします
- **live にある清算型の試行の bot は 11-24 まで置きます**（11-21 の「損をしている試行も 11-24 まで置く」と同じ）。止めるかどうかは 11-24 の締めで人間が決めます
- 次のブロック型の枠の清算の bot も、新しく出さないでください
- 単発の取り残し（下の 2）は、清算の取り残しでも対象のままです。fork で利益が確定しているものは型を問いません

## 2. 単発の bot（`oneshot-`）は本数の上限なし

理由: 単発は fork で利益を確かめてから出し、取ったらすぐ止めます。11-21 の Bundles.fi の rebalance の取り残しで +31 USD を取りました。本数で待たせる理由がありません。

- `2026-11-14-oneshot-leftovers-idle-pull-oracle.md` の「同時に live に置く単発の bot は 2 本まで」をなくします。条件（10 分以上残っている、差し引き 10 USD 以上、なぜ残っているかを 1 行、fork の成功と revert）はそのままです
- 単発の bot は試行の枠（75 本）にも数えません（今までどおり別枠）
- bot あたり 400 USD、L 50 USD、1 日の損失の上限、累計損失 30 USD の停止はそのままです
- promote の順: 単発を試行より先にしてください。中間 wallet の資金が足りなければ promote せず、inbox/human に「<チェーン> が <USD> 足りない」と書いてください
- 取れたら、または promote から 48 時間で取れなければ、今までどおり inbox/meta → inbox/human に回し、人間が `gate stop` します

## meta へ

builder.md・paper-reviewer.md・earner.md（ある場合）と wiki `methods/oneshot-leftovers.md` に 1 と 2 を反映してください。「単発は 2 本まで」の記述を消し、清算型の試行を作らない・promote しない 1 行を足します。プロンプトの大きさの上限は守ってください。
