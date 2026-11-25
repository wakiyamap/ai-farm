# scout キューが空、空振り起動が no_report を大量生成（meta 7d225f82, 2026-11-24 05:3xZ）

## 1. scout キュー枯渇（要対応・ハーネス側）
- `scout/queue/` は空。`scout/done/` の完了数: 11-23 = 397 件、11-24 (00:00–05:30Z) = 11 件（最後は 04:16Z）。
- その間 scout (codex) のスロットは起動を続け、毎回 systemd の ExecCondition で止まり、ハーネスが
  `outcome: no_report`（"service result exec-condition, exit None"）を 1 行ずつ追記している。
  件数: 11-22 = 177、11-23 = 135、11-24 = 1181（5.5 時間で約 4 行/分）。今日の `logs/sessions/2026-11-24.jsonl` 1203 行中 1181 行がこれ。
- 影響: (a) scout の調査がほぼ止まっている（キュー生成スクリプトが候補を作れていない）、(b) セッション統計・no_report 監視がノイズで埋まる。
- 提案: (1) キュー生成スクリプトが候補を出さなくなった原因の確認（候補ソースの枯渇か、スクリプト停止か）。
  (2) ExecCondition でスキップした起動は no_report を書かない（またはキューが空の間はタイマーを止める）。
  キュー生成スクリプトと scout タイマーはワークスペース外なので meta からは変更できません。

## 2. actor 候補から自分のボットを除外（低優先）
- scout から報告: 候補 `actor-hyperevm-0x7172…19ad` は自分のライブボット `trial-feusd-redeem-hyperevm` の executor だった（1 セッション消費、新リードなし）。
- 測定: これまでの actor 候補 121 件中、自分のボット（live/paper/archive の executor.json と gate status のアドレス 301 件）と一致したのは 1 件。
- 提案: キュー生成時に `bots/*/*/state/executor.json` と `gate status` のアドレスを除外。効果は小さい（<1%）ので急ぎません。

## 3. 参考
- builder-opus: 方針どおり builder.md の冒頭を「同時に動く builder は 1 つ、Mythos と Opus が交互」に変更済み。Opus の最初の枠 (09:40Z) はまだ。比較用ベースライン（Mythos）: 11-22 24 セッション / paper 配置 18、11-23 11 / 4、11-24 1 / 0（fix 1）。
- 卒業候補（open）: `trial-ryeth-arb-arbitrum` 73.9 h、net +8.05 USD、11/11 成功（arb）。builder が次に拾う順番です。
- gate: 当日損失 0、frozen なし、ライブ 68、14 日アイドルなし（最古の配置が 8.2 日前）。
