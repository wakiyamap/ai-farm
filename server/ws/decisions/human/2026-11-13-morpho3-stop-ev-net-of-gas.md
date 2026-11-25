# morpho-watcher3 の停止、期待収益の数え方、lead を閉じたときの live bot（人間、2026-11-13）

11-13 01:52 JST のブリーフと、morpho-watcher3-ethereum の review.md を読んで決めました。

## 1. morpho-watcher3-ethereum は人間が止めた

2026-11-13 に `gate stop` で停止し、資金は中間ウォレットに戻しました。

reviewer の審査（run f43c9353）は、その時点の規則どおりでした。fork での再現、1 ブロックの事例の除外、CU との比較のどれも行っています。問題は期待収益の数字です。review.md は README の「1 日約 1.8 USD」をそのまま使いましたが、earner はその後、同じ事例を数え直して「1 日 0 USD」とし、lead 14 を閉じました。作った本人の最新の測定が 0 なので、live に置く根拠がなくなりました。

## 2. 期待収益は事例ごとに「粗利 − ガス代」で数える

- earner: README の期待収益は、数えた事例ごとに **粗利、その tx のガス代（ガス量 × そのブロックの base fee + 優先手数料、USD）、差し引き** を 1 行ずつ書いてください。差し引きが 0 以下の事例は数えません。合計を観測日数で割ったものが 1 日の期待収益です
- paper-reviewer: README の合計をそのまま使わず、この表から自分で計算し直してください。review.md に計算結果を書く。表がなければ fix、計算し直した期待収益が CU の費用（100 万 CU ≒ 0.53 USD）以下なら promote しない
- executor の利益ガードがトークンの残高だけを見ている場合（ガス代はネイティブで別に払う）、bot の送信条件は「見込みの粗利 > ガス代の上限」になっていること。なっていなければ fix

## 3. lead を閉じたら、その lead の live bot を確かめる

- earner: lead を `dead_end` か `blocked_infra` にするとき、その lead から作った bot が bots/live にあるかを確かめてください。あれば、同じセッションで inbox/meta に「停止を勧める」と根拠（attempts の番号）を書く
- meta: それを読んだら、次の実行で inbox/human に回してください。止めるのは人間がやります
- 待っているイベントが単に来ていないだけの bot（franken-dutch-ethereum、gearbox-v3-watcher-ethereum）は対象外です。lead が measured のままなら、そのまま待たせます

## 4. 当面の方針

researcher を 1 日 4 回にした体制のまま、数日様子を見ます。条件（速度勝負をしない、1 本 400 USD まで）は変えません。

- earner: 作るものがないときに、閉じた lead の再確認にセッションを使わないでください（lead 16 の next_steps に書いたとおり）。新しい lead が出るまでは、短いセッションで終えて構いません
- researcher: 「資金 400 USD では小さすぎるが、仕組みとしては成立した」クラス（reserve の作り直しなど）を見つけたら、**必要な資金と、その資金での 1 日の期待収益** を数字で inbox/human に出してください。上限を変えるかどうかの材料にします

## meta へ

2 と 3 を earner.md、paper-reviewer.md、meta.md に、4 を earner.md と researcher.md に反映してください。プロンプトの大きさ（56,000 バイト以下）は守ってください。
