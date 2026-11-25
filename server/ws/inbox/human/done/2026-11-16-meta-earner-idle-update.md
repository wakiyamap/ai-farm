# meta 92357deb（2026-11-16 14:5xZ）: earner の空回りの続報（提案の再掲）、earner プロンプトの残り容量

## 1. earner の空回りは続いています（03:0xZ の提案 §1 の続報、判断をお願いします）

出典: logs/sessions/2026-11-16.jsonl（00:00〜14:4xZ、grep で数えたもの）、KB attempts 1391〜1424。

- earner は 73 回起動しました。そのうち 34 回が `no_target` です。34 回すべてが待ち行列（手順 1〜5）を最初から確認し直していて、23 回は数時間前と同じ one-shot の一斉確認もやり直しています。
- 残りの約 36 回は新しい区画を測りましたが、結果はすべて dead_end か、bot にならない lead でした（lead 197〜207）。今日 paper に置かれたのは franken-threshold-ethereum の 1 本だけで、同日に demote されました。
- DefiLlama の TVL 帯の総当たり（attempts 1375 / 1409 / 1417 / 1420）は、earner 自身が「帯はこれで全部」と書いて終わりました。この先、earner が自分で探す余地はさらに減ります。
- 新しい lead の主な出どころは researcher の 2 インスタンスです（11-13 以降で計 14 件。bot まで行ったものは 0 件）。
- **提案（再掲）**: unmeasured の lead がない、`decision: fix` の paper bot がない、新しい review も decision もない。この 3 つがそろっている間は、harness が earner の起動を間引く（例: lane ごとに 1 時間 1 回）。浮いた分を researcher の回数に回す案も合わせてご検討ください。起動の頻度は meta には変えられません。
- meta の変更（今回）: earner.md の「No target left」の項に 1 文を足しました。「同じ lane の直前の報告が `no_target` で 60 分以内、その後に decision・review・lead・paper bot の変化がなければ、手順 1〜4 を確認し直さない」。次の meta で、`no_target` のうち確認し直しを書いている報告の割合（今は 34/34）を数えます。

## 2. earner プロンプトが上限近くまで来ています（確認のみ）

組み立て後の earner は 55,873 bytes です（社内の目安 56,000、起動できなくなる上限 60,000）。researcher の TOOLS.md 1 行と今回の 1 文で増えました。次に earner.md へ何か足すときは、同じだけ wiki へ移します。

## 3. その他

- `ledger/sources.d` の 4 件の移動、ありがとうございました。今は 38 件です（Carbon Vortex の 2 件を researcher が追加。2 件とも head まで verified）。
- live 2 本（gearbox-v3-watcher、morpho-nextblock）は稼働中です。今日の損失 0、capital 689.04 USD。どちらも清算可能な口座は今のところありません。14 日間検知も送信もない bot の確認は 11-23 からです。
- researcher b299b167 が `tools/ledger-source-coverage.py` に足した `--spec-file`（読むだけ）を確認して、残しました。
