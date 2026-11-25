# meta（run cf4ce30c, 2026-11-21 04:1x-05:0xZ）: Peapods 確認、trial-morpho-eth-base の負け方、uwinddown の入金、one-shot の回収

## 1. Peapods の買い手数料の回避: していません（decision 2026-11-21-ichi-yes-peapods-fee-no 項目 2）

live の 3 本（trial-peapods-arb-arbitrum・trial-peapods-arb-base・trial-peapods-base）は、bot.py にも executor のソース（`scratch/trial-peapods-*/contracts/src/*.sol`、manifest が指す artifact の元）にも Router02 が出てきません。pod を受け取る swap はすべて `pair.swap(..., address(this), "")` で受け取り手は executor 自身、手数料は払う前提で計算しています（PodArbTake.sol 172-180 行のコメント「pod transfer fee: price what actually arrived」）。paper に Peapods の bot はありません。止める必要はありません。

## 2. trial-morpho-eth-base が損をした理由（お願い 2 への 1 段落）

live の送信 25 回はすべて `lost` で、25 回とも 11-20 15:15-19:17Z の約 4 時間、cbETH 市場の oracle 更新の直後に集中しています（`bots/archive/trial-morpho-eth-base/logs/bot.jsonl`）。粗利は 0 ではなく、送る直前の simulation では 1 回 0.08-1.84 USD の利益が出ていました。負けた理由は速さです: 25 回とも、別の清算者が同じ借り手を **1-7 ブロック前（Base は 0.2 秒ブロックなので 0.2-1.4 秒前）** に清算しており（中央値 3 ブロック = 0.6 秒）、farm の tx はその後に着いて revert しました（例 `0xaa32022b...162b`: status 0、98-126k gas）。ガスの合計は 0.000599 ETH（約 1.2 USD、L1 fee 込み）で、人間が見た約 −0.97 USD と合います。つまり oracle 更新で開く Morpho の清算は 1 秒未満の競争で、farm の反応時間（約 3 秒）では取れません。11-24 の判断では「この型は試行を続けても勝てない」と見てよいと考えます。bot のディレクトリはすでに `bots/archive/` にあり（11-20 22:31Z、gate）、wallet の残りは 5e11 wei（ほぼ 0）なので掃き戻しは済んでいます。

## 3. trial-uwinddown-base: Base の中間 wallet に 5 USD の入金のお願い

審査は通過済み（run 294c7efa、fork で成功と guard の revert を再現）。`gate promote` が 00:09Z に「base の中間 wallet が 15.00 USD + ガスに足りない」で止まりました。いま Base は 14.71 USD（04:1xZ の gate status）。**Base に native で約 5 USD** 入れていただければ promote できます。急ぐ理由: Universal Protocol の wind-down vault（11-18 開始）の USDC が尽きると機会が消えます（11-20 22:49Z で 171,845 USDC、先行者 5 者が 2.9 日で約 160 USD）。

## 4. 枠（65 本）の状況

paper-reviewer.md と builder.md の 60 を 65 に直しました（prompt サイズ: earner 55,983 / paper-reviewer 53,831 / builder 52,350 bytes、すべて 56,000 以下）。04:1xZ の live の試行は 64 本で空きは 1。待っているのは trial-uwinddown-base（Base 入金待ち）と trial-lim-bsc（bsc の中間 wallet は 14.11 USD になり、必要額 約 10.03 USD を超えたので次の審査で promote できるはず）の 2 本です。trial-morpho-eth-base の空き（お願い 3）はこの 2 本で使われます。

## 5. one-shot `oneshot-bundles-rebalance-ethereum`: 取れました（methods/oneshot-leftovers.md の「captured」報告）

promote 直後に CORE の rebalance を取り、+34.61 USDC（tx `0x034e1369...c124`、ethereum block 26,459,311、391,156 gas）。bot はすでに停止・archive 済みで、34.61 USDC は ethereum の中間 wallet に戻っています（gate status `ethereum:usdc 34.61`）。追加の対応は不要です。

## 6. 11-24 の締めの材料: live の試行の送信の勝ち負け（全 bot の bot.jsonl から集計、04:2xZ）

- 清算の試行: **67 回送って 9 回勝ち**。負けは勝者の 1-3 ブロック後（中央値）に着いて revert。trial-morpho-eth-base と同じ形で、清算は 1 秒未満の競争です。
- 清算以外（harvest、固定レート / NAV での償還、pod・vault・wrapper の裁定、窓のある keeper）: **90 回送って 68 回勝ち**（予定時刻ちょうどの upkeep を奪い合う mycelium の 0/165 は除く。1 回 約 0.001 USD）。
- builder はすでに 11-19 夜から清算以外の型だけを置いています。prompt の変更はしていません。詳細と再集計の方法: wiki `methods/live-trial-send-census.md`。勝ちの数であって利益の額ではないので、USD は各 bot の send_result を確かめてから使ってください。
