# Phase 16e 対応と codex scout 初日の数字（meta b3c9f352, 2026-11-23 23:2xZ）

## 1. ロールファイル（依頼 1・2）
- paper-reviewer.md: `other-reviewer` / paper-reviewer-claude への振り分けの文を削除し、「11-24 以降はレビュー担当が 1 つだけ。全 bot をレビューし、同じモデル系が作った bot には review.md に `same-model review (codex)` と書く」に置き換えました。
- builder.md: 「builder は 2 インスタンス（Claude と Codex）」を「builder は 1 つだけ」に変更。
- common.md と TOOLS.md には codex や 2 人目のレビュー担当への言及はなく、変更なし（common.md はもともと meta には編集できません）。
- prompt-size: builder 52389、paper-reviewer 55182（上限 56000 以内）、earner 55892、scout 43021（scout.md は変更なし）。
- flatmoney の依頼: builder-claude（run 379d5de6）がすでに担当済みです。lead 436 は 19:50Z に dead_end になり（Hermes なしの経路はありません。空の更新で通るのは 7.6 日間の注文 25 件中 1 件、trial の 13 勝中では 0 件）、grad-flatmoney-arbitrum は archive 済みです。**trial-flatmoney-arbitrum は live のままで、止められるのは human だけです**（Hermes キーの期限 ~12-02 以降は約定できない見込み）。

## 2. codex scout（依頼 3）: 2026-11-23（UTC）
| | セッション | scouted | no_report | KB verdict |
|---|---|---|---|---|
| codex scout (gpt-6-sol) | 126 | 120 | 6 | dead_end 100 / lead 20 |
| qwen scout（切替前） | 264 | 262 | 2 | dead_end 240 / lead 21 |
| paper-reviewer (codex) | 15 | 15 | 0 | — |

- 使用量上限（rate limit / usage error）で終わったセッション: **0**。no_report の 6 件はいずれも 35 分のタイムアウト（ログの最後はツール出力）。notes に「429」などを含む 9 件は、ブロック番号やソースの行番号でした。
- paper-reviewer に上限による失敗はありません。scout を 2 つに減らす必要は今のところありません。毎回の meta で同じ集計を続けます（scratch/meta-b3c9/scout_codex.py）。
- codex 由来の lead が出る割合は 17%（qwen は 8%）。質は builder の結果を見てから判断します。

## 3. 卒業候補（grad-candidates.py, 23:1xZ）
- **trial-ethos-redeem-optimism**: 101 h, net +2.20 USD, 32/42 won。未着手の候補はこれだけで、builder が拾う見込みです。
- trial-peapods-arb-arbitrum (+3.09) と trial-flatmoney-arbitrum (+1.29): grad はどちらも archive 済み（前者は 3 秒未満のレースで却下、後者は上記）。
- trial-ryeth-arb-arbitrum: +8.11, 11/11, 68 h。11-24 04Z 頃に 72 h に達します。

日次損失 0、frozen なし。
