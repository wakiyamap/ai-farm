# 試行から「卒業」させて深く磨く、builder を減らして磨く仕事に寄せる（人間の判断 2026-11-24）

11-17 から試行の bot を安く広く試してきました。勝ちの型は見えてきましたが、試行の枠（1 本 20 USD、1 送信の損 1 USD）では手数料で競れず、規模も増やせません。一方、運用費（builder-claude だけで 1 日 100 USD 前後）が live の損益（promote から通算 +12 USD）を大きく上回っています。そこで、探すのは今の仕組み（scout と試行）に任せたまま、当たった bot を「卒業」させて磨きます。

`2026-11-17-cheap-chain-trials.md` と試行の枠の decision はそのままです。卒業した bot は試行ではなく、通常の bot として扱います。

## 1. 卒業の条件（paper-reviewer / meta が確かめる）

試行の bot が次をすべて満たしたら、卒業の候補です。

- live になってから 72 時間以上
- promote からの差し引きが +1 USD 以上（gate status の値）
- 勝った送信が 3 回以上（bot のログの `send_result: won`）。1 回の大当たりだけの bot は外す

meta は毎回、候補の一覧を報告に書いてください（bot、差し引き、勝ち / 送信の数、型）。

## 2. 卒業した bot（builder が作り、paper-reviewer が審査する）

- 新しい ID `grad-<対象>-<chain>` で作り直す（試行の bot はそのまま live に残し、grad が live になったら人間が `gate stop` する）
- 通常の bot の審査を受ける。ただし期待収益の根拠は、試行の live の実績（送信・勝ち・粗利・相手との差）で示してよい
- 上限: `capital_usd` 150 以下、`max_loss_per_tx_usd` 3 以下、手数料は見込みの粗利の 50% まで積んでよい（`max_loss_guarantee` に書く）。ethereum は今までどおり別扱い（卒業の対象にしない）
- 手数料の上限は grad ごとに決める: 試行のログから、勝った相手の手数料（優先手数料・ビルダーへの支払い）が粗利の何割だったかの分布を README に書き、それを見て決める。50% は天井で、根拠のない積み増しはしない
- OP Stack（optimism・base）のように、優先手数料を上げても順番が変わらないチェーンでは手数料を積まない（勝者は毎回 tx index 1、11-20 の観察）
- **資金を増やすなら、増やすと儲けが増える証拠を出す**: 過去の勝ちのブロックの fork で、1 回の量を 2 倍・5 倍にしたときの粗利を示す。増えない型（keeper の報酬のように 1 回の額が決まっているもの）は、資金は最小のまま、手数料の上限だけ上げる
- 試行で負けた送信の理由（相手との差のブロック数、手数料の不足、revert の理由）を README に書き、直したことを示す
- promote からの損 30 USD で止まる仕組み、X・n・L・S はそのまま
- 同時に live の grad は 5 本まで

## 3. builder の仕事の順番

1. paper-reviewer の fix で戻った bot
2. 卒業の候補を grad にする（上の 2）
3. live の grad を磨く（負けた送信の理由を調べて直す、同じ型の別の pool・資産に広げる）
4. scout の measured の lead
5. 1〜4 が無ければ、短い報告を書いてすぐ終わる。長い census や単発の当てのない sweep はしない

## 4. builder の頻度

builder-claude は 4 時間おきにします（timer は人間が変えます）。builder-codex は今のまま（3 時間おき）。scout・paper-reviewer・meta は今のまま。

## meta へ

builder.md に 3 を、paper-reviewer.md に 1 と 2（grad の審査）を反映してください。wiki に `methods/graduation.md` を作り、手順の細かいところはそこに置いてください。プロンプトの大きさの上限は守ってください。
