# decision 2026-11-12-morpho-stop-researcher-runs の反映（meta、run fb969927、2026-11-11 22:2xZ）

## 反映したもの（ロールファイルと TOOLS.md）

- earner.md: 2（取れる状態から取られるまでのブロック数・秒数を事例ごとに README へ、中央値・最小値、ポーリング間隔 + 送信〜取り込みより短い事例は期待収益に数えない、残らなければ blocked_infra で終了）、6（README に CU/日 と 1M CU ≈ 0.53 USD での金額、期待収益がそれを下回れば promote 不可）、5（急ぎでない報告は inbox/live ではなく inbox/meta）。あわせて gate の executor デプロイ上限 3,000,000 gas（morpho-watcher2 の部分 promote の原因）を 1 文追加
- paper-reviewer.md: 2 と 6 を promote 前のチェックに（欠けていれば fix、残る事例がなければ demote）、部分 promote の報告先から inbox/live を外し、その他の報告は inbox/meta
- researcher.md: 6 の CU の値段（0.53 USD/1M CU、月 95.2M CU = 50 USD、日次は名目）と 2 の対象外
- meta.md: inbox/live も meta が読み、人間の判断が要るものを inbox/human に回す
- TOOLS.md の gate 行: earner / paper-reviewer の資金依頼先を inbox/live → inbox/meta
- 4（researcher の回数）は timer の変更のみなのでプロンプトは変えていません

プロンプトの大きさ（組み立て後）: earner 54,270、paper-reviewer 43,285、live-operator 37,803、meta 37,172、researcher 37,886（すべて 56,000 以下）。

## common.md（meta は変更できないので、人間にお願いします）

次の 2 か所の変更を提案します。

1. Workspace の表の `inbox/live/` の行: 「Messages to the live-operator」→「Messages to the live-operator (read only when the watchdog wakes it; non-urgent reports go to `inbox/meta/`)」
2. 「Hard constraints」直前の chains 説明にある「a shortfall is the usual gate refusal (ask the human through `inbox/human/`)」はそのままで問題ありません。Principles 2 に「Something taken in the price-update block or within seconds to 1-2 blocks of becoming eligible counts as a latency race (decision 2026-11-12).」を足すと、ロールファイルの規則と揃います

## 測るもの（次回の meta）

- 指標: この後に paper に出た bot の README のうち、事例ごとの取られるまでの時間と CU の USD（0.53/1M）が両方あるものの割合。変更前: 現在の paper bot 3 件中、0.53 USD/1M CU を使っているのは 1 件（morpho-ses-ethereum は「100 USD/M CU」と書いている）
- reviewer がこの 2 点で fix にした回数
