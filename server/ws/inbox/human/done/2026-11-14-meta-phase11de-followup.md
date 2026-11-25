# phase 11d / 11e のあとに meta がしたことと、決めてほしい 1 点（meta f1ef7ed7、2026-11-14）

## 決めてほしいこと: live-operator.md の `{{IDLE_BEFORE_STOP}}`

live-operator.md の「Wake reasons」に、埋められていないままのプレースホルダがあります。

> Opportunity exhausted: no detections for {{IDLE_BEFORE_STOP}} and the awaited event is gone

この値は monitor が live-operator を起こす条件そのものです。monitor は workspace の外にあるので、meta が文言だけ決めると実際の挙動とずれます。そのため、値を決めてください。

- **提案: 14 日。** 待ち型の bot は、待っているイベントが数日に 1 回しか来ないものが多く、短くすると誤って止めてしまいます。次ブロック試行 bot の「14 日送信 0 なら停止を勧める」という線（decision 2026-11-13-blocked-infra-feed-retriage の 3）とも揃います。
- 値を決めていただければ、meta が live-operator.md を書き換えます。monitor 側の設定も同じ値にしてください。

## 11d（earner.md）: 3 日後の比較の基準値

ご依頼の 4 つの指標について、11-11〜11-14 の基準値を session ログ（`logs/sessions/*.jsonl`）と inbox/meta から数えました。11d の適用は 11-14 02:21Z なので、11-14 は 02:21Z の前と後に分けて比べます。比較は **11-17 に inbox/human に出します**。

| 日 | earner セッション | no_report | paper_placed | fix_submitted | 「壊れている」報告のうち呼び出し側の誤り |
|---|---|---|---|---|---|
| 11-11 | 110 | 42（うち 37 はプロンプトの上限超えで起動しなかったもの） | 5 | 7 | 1（elysium の 65 桁の topic） |
| 11-12 | 89 | 3 | 2 | 2 | 0 |
| 11-13 | 41 | 3 | 7 | 9 | 3（セレクタの手打ち、DAI/USDC のアドレスの誤り、balanceOf の打ち間違い） |
| 11-14（〜08:00Z） | 13 | 2 | 1 | 3 | 0 |

- 「止める線（1 lead 3 セッション）を超えたセッション」は、セッションの記録だけでは数えられません。lead ごとの attempts の履歴で数えます。参考までに、lead 17（aave-pricefeed-ethereum）は 11-13〜11-14 に 9 セッションありました。すべて reviewer の `fix` への対応で、bot は 02:41Z に archive されています。
- 「fork で差し引きプラス、または bot を置いた」セッションは、paper_placed + fix_submitted で近似しています。

## 11e（TOOLS.md、paper-reviewer.md、researcher.md）

- TOOLS.md から削った項目を 1 つずつ確認しました。ほとんどは wiki に既にありました。どこにもなかった 5 つ（add-source の cursor 確認、websearch の癖 2 つ、relay-log-scan の分割と `--keep-trailing-nulls`、manifest-check の `owner` 警告）は、wiki `infra/relay-reference.md` の末尾に移しました。TOOLS.md には戻していません。

## 今日の 3 つの decision を役割ファイルと wiki に反映しました

- 急落の事後検証（`methods/crash-postmortem.md`）、相手の executor の解析（`methods/executor-techniques.md`）、取り手の型 P/B/O/S/T（`methods/taker-types.md`）の 3 ページを作りました。copy-bots と blocked-infra-feed-retriage の 2 ページは、ブロック数の言い方を race-rule-seconds に揃えました。
- 役割ファイルには短い案内だけを足しました。
  - earner: 対象の順番に「急落の事後検証（11-16 まで）」を入れ、相手の executor の解析を no-target の先頭に置きました。測る事例には型を付けます。feed bot は清算価格の表を前もって計算します。
  - researcher: 2 つの手順ページへの案内を足しました。
  - paper-reviewer: イベントのたびに全ポジションを読み直す feed bot は `fix`。O 型（Atlas）は EV から外します。
- プロンプトの大きさ（組み立て後）: earner 48,820 → 49,448、paper-reviewer 42,204 → 42,418、researcher 37,660 → 38,175（すべて 56,000 以下）。
