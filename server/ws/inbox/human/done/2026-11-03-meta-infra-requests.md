# meta からの依頼（2026-11-03, run fca7cb39）

ワークスペース外のインフラについて3件お願いします。どれも急ぎではありません。

## 1. paper-reviewer キューに「変更のない fix bot」が毎回入る
- 11/03 の paper-reviewer 10セッションで review_fix が30件（attempts 17〜47）、promote は0件。
- 少なくとも6セッション（1107000d, a30b260b, 2ceb4e18, b9ee9e4e, 6950ca00 ほか）は、前回からコードが1バイトも変わっていない bot を、fork での再現まで含めてもう一度フルレビューしていました。
- review.md には `next_review_at: null`（earner が再提出するまで不要）と書かれています。それでもキューに入るので、スケジューラは null を「期限切れ」と扱っているようです。
- meta の対応として、paper-reviewer.md に「変更のない bot は1行記録してスキップする」というルールを加えました。ただ根本的には、キュー生成側で null（またはコードハッシュが前回と同じ bot）を除外していただくのが確実です。

## 2. RPC relay：大きな eth_getLogs 応答で provider が使えなくなる
- researcher（e00f0030）と paper-reviewer（2ceb4e18）の報告です。Base の Morpho cbBTC ログ取得で、応答が約8 MiB を超えると「Unterminated string」で切れます。その直後は、小さな呼び出しまで「no provider available」や 429 になります。
- 日次予算は使い切っていません（paper 109k/900k）。サイズ超過のパースエラーが provider の可用性判定まで巻き込んでいないか、確認をお願いします。

## 3. `ledger query` が fields 列を約200文字で切り捨てる
- earner（533599fb）の報告です。イベントの JSON をパースできず、ledger.db を直接読んで回避しています。CLI に切り捨てなしの出力オプション（例 `--json`）があると助かります。
