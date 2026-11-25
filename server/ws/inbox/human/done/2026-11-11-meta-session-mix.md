# 提案: earner と researcher のセッション配分の見直し（meta bebb64cc, 2026-11-11 17:0xZ）

## 測定結果（logs/sessions/2026-11-11.jsonl と KB から）

- 本日のセッション数: earner 88（うち no_report 41。39 件は 10:5xZ に修正したプロンプトのサイズ超過が原因で、修正後の no_report は 2 件のみ）、researcher 1、live-operator 1、paper-reviewer は数回。
- 本日報告のあった earner セッション約 45 件のうち paper_placed は 1 件（moonwell-whale2-base）。残りはすべて lead_recorded か dead_end_recorded。
- `leads` に status=unmeasured の行は **0 件**（blocked_infra 29、dead_end 107、measured 9）。earner はリードがないため、自分でチェーンごとの「poke census」を立ててはその日のうちに閉じています。本日は 9 チェーンすべてで dead_end になりました。
- researcher のリード funnel（11-09 以降）: opus が 5 件、gpt-6.1-sol が 2 件追加。

## 提案

1. earner の起動枠の一部（例: 1 日 10 枠程度）を researcher に回すことを検討してください。earner の枠は空のパイプラインを手作業の census で埋めているだけで、成果になっていません。モデル割り当てと起動スケジュールは meta の権限外なので、ご判断をお願いします。
2. inbox/live/ に、live-operator が未処理のメモが 3 件あります（morpho-watcher-ethereum の再ピン 2 件、reserve-dutch の見送り報告 1 件）。live-operator の起動が本日 09:4xZ の 1 回だけでした。インシデント時以外にも、1 日 1〜2 回の定期起動があると対応が早くなります。

## meta が本日行ったこと（参考）

- earner.md: リードの最初のセッションで、エントリ関数を新しいアドレスから呼ぶ（ロールで制限されていないかの確認）ことを必須にしました。lead 145 は 6 セッション、lead 142 は 3 セッション目でようやくロール制限が判明していたためです。並行して走ったセッションも 3 セッションの停止ルールに数えるようにしました。効果は次回の meta 実行で、新しいリードがクローズまでに要したセッション数を見て測定します。
