# 2026-11-09 promote の基準を緩める（live で試す）

## 理由

実際の機会を paper で、利益の出る形で捉えるまで promote しない、という今の基準では、機会が週 1 回〜1 日 1 回未満の bot がいつまでも live に出られない。仕組みの審査をすべて通った bot が 5 本、待ちのままになっている。1 回あたりの損失はコードで上限が決まっているので、少額で live に出して実際に試し、外れたら止める方が早く学べる。

## 新しい promote の基準（すべて満たせば promote してよい）

1. **仕組みの再現**: reviewer が、現在の artifact と bot コードで、fork 上の成功（利益が出る）と、ガードによる revert（元本が戻る）の両方を自分で再現した。
2. **配備できる**: `tools/manifest-check.py` が PASS（executor が artifact のパスだけを持ち、executor_args がコンストラクタと一致している）。
3. **損失の上限**: 1 tx の最悪損失（署名する手数料上限、送る value、元本を使う場合の executor のガード）が L（50 USD）以下で、コードで保証されている（従来どおり）。
4. **検知の妥当性**: paper のログで、待っているイベントを正しく監視していることが確認できる。直近に対象のイベントが起きていた場合は、それを検知できていた、または検知できなかった理由が説明済み（同一ブロックの速度競争など）であること。**実際の機会を paper で利益の出る形で捉えたことは、もう必須ではない。**
5. **live 試行の損切り**: bot 自身が、live での累積損失（gas と、元本を使う場合はその損失の合計）が **30 USD** に達したら送信を止め、`state/` に停止理由を書くこと。reviewer は、この停止処理がコードにあることを確かめる。

## promote 時の資金

- 最初の promote では、gas 用のネイティブ資産を、manifest の想定の範囲で最小限だけ渡す（Base は従来どおり 18 USD が上限）。USDC の元本（principal_usdc）を使う bot は、元本のガードを reviewer が fork で再現した場合に限り渡す。
- gate が資金不足で promote を拒否したら、それを最終判断として扱い、必要額を書いて inbox/human に出すこと（入金するかどうかは人間が決める）。

## live になった後

- live-operator は、毎日 live bot の送信・成功・損失を確認する。累積損失が 30 USD に達した bot、または想定と違う動き（送るべきでない場面で送っている、など）をした bot は demote して sweep する。
- 送信がなくても、それだけでは demote しない（送信しなければ損失は出ない）。
- システム全体の上限（X = 2000 USD、1 日の損失 200 USD、watchdog による停止）は変えない。

## 対象

- 現時点で基準に近いもの: gearbox-v3-watcher-ethereum、moonwell-whale-base、morpho-watcher-ethereum、franken-dutch-ethereum、reserve-dutch-ethereum。manifest-check で FAIL が出ているものは、まずそれを直すこと。earner はあわせて、5 の累積損失による停止処理を各 bot に入れること。
- reserve-folio-dtf-ethereum は対象外（在庫トークンの減少に上限がなく、見積りの経路もない。2026-11-09-relay-1inch-paperctl を参照）。

## meta への指示

- paper-reviewer.md の promote の基準を、上の 1〜5 に書き換えること。earner.md には、5 の停止処理を bot の雛形に入れることを書くこと。
- 次回以降の報告で、live bot ごとの送信数、成功数、累積の損益を数えること。2 週間後に、この基準を続けるか、締め直すかを提案すること。
