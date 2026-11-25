# 設計書（案）: USDC で持つ型のための 200 USD の枠（phase 12d の候補）

2026-11-15 作成。**まだ何も実装していない**。

**人間の判断（11-15 13:45 JST）**: 末尾の 5 点はすべて案のとおり。(1) 停止の線は「30 USD + holding_usd」でよい (2) 1 本あたりの上限はとりあえず 100 USD (3) すぐに USDC に戻せる型だけに限る（待ち時間のあるものは、ほかの要因でロックされる可能性があるため）(4) `exitAll()` が失敗したら「未完の stop」で人間に回す (5) 持つ時間の上限は最長 7 日。

人間の見立て: この類は、ブリッジをまたぐところまでやらないと儲からないと思っている。ただ、一部のチェーンで大きく安くなることはあるので、まずこの枠で始める。**ブリッジをまたぐ型はこの設計の対象外**（ブリッジの待ち時間は (3) の「すぐに戻せる」に当たらない）。同じチェーンの中で安く買って売り戻す型が対象。チェーンをまたぐ型は、両方のチェーンに USDC を置いて、それぞれのチェーンの中で完結させる形なら、この枠のまま扱える。

## 1. 何のために作るか

今の farm は「1 tx の中で利益が出なければ revert」（11-03 の選択 A、common.md の L）に当てはまるものしか live に出せない。在庫も保有リスクも持たない型で、いちばん競争の激しい区画にあたる。

11-15 の判断で、次の型に合計 200 USD までの枠を作ることになった。

> USDC を持って待つ → 機会が来たら USDC で別の資産を買う → しばらく持つ → USDC に戻す

例: 割引で売られるもの（Dutch オークション、手数料や収益の入札）を買って、市場で売り戻す。買う tx と売る tx が別なので、その間は値下がりの危険を持つ。

## 2. 今のコードで何が邪魔をするか

サーバーのコード（11-15 に受け取った gate-ctl・farm-signer・farm-watchdog）を読んだ結果。

| 場所 | 今の動き | この型で起きること |
|---|---|---|
| signer | 1 tx の最悪額は「送る value + ガス」だけを L と比べる。USDC の transfer は executor か中間ウォレット宛てなら通し、額を 1 日の枠（`capital_usd`）に足す | **邪魔をしない**。bot は今でも USDC を自分の executor に送れる |
| watchdog | promote 以降の損失 = gate が入れた額 − bot の wallet のネイティブと USDC。30 USD を超えたら `gate stop` | **邪魔をする**。別の資産に換えた分は「なくなった」と数えるので、30 USD を超える持ち高を作った瞬間に止められる |
| gate の stop / sweep | wallet のネイティブと USDC だけを中間ウォレットに戻す | **邪魔をする**。止めたときに持っている別の資産は、executor か wallet に置き去りになる |
| gate の X | wallet のネイティブと USDC だけを数える | 持ち高のぶんだけ X が小さく見える（最大 200 USD。許容できる） |
| プロンプト（common.md の L、promote の基準 1・3） | 「end 残高 > start 残高でなければ revert」が必須 | **邪魔をする**。買う tx はこれを満たせない |

つまり、変える必要があるのは watchdog、gate の stop、プロンプトの 3 つ。signer と鍵は変えない。

## 3. 案

### 3-1. manifest に枠を書く

```yaml
holding_usd: 100        # この bot が別の資産で持ってよい上限（USD）。書かなければ 0 = 今までどおり
principal_usdc: 100     # 今までどおり。holding_usd 以上であること
```

### 3-2. gate（promote）

- live の bot の `holding_usd` の合計 + 新しい bot の `holding_usd` が、gate.json の `max_holding_usd_total`（200）を超えたら、資金を動かす前に拒否する
- `holding_usd` が 0 でない bot は executor が必須（wallet が直接プロトコルを呼ぶ形は今までどおり不可）

### 3-3. watchdog

- `holding_usd` のある bot は、停止の線を **30 USD + `holding_usd`** にする。持ち高の上限までは「なくなった」のではなく「別の資産になっている」とみなす
- 正直に言うと、これは「この bot では、30 + holding_usd まで失うまで止まらない」という意味になる。枠の合計が 200 USD なので、全部の bot を合わせた追加の最悪損失は 200 USD
- 持ち高の時価は見ない。任意のトークンの値付けを watchdog に持たせると、その値付け自体が誤りや操作の入口になるため

### 3-4. gate（stop）

- `holding_usd` のある bot を止めるとき、sweep の前に、bot の鍵で executor の `exitAll()` を 1 回呼ぶ。executor は、持っている資産を全部 USDC（かネイティブ）に戻して bot の wallet に返す。gate.log に nonce つきで記録し（watchdog が既知の nonce として扱う）、レシートを待ってから sweep する
- `exitAll()` が revert した・載らなかったときは、今ある「未完の stop」と同じ扱いにする（サービスは止まるが bot は live に残り、終了コード 3）。人間が状況を見て、もう一度 `gate stop` するか、手で回収する
- 持ち高は **executor に置く**（wallet に置かない）。こうすると出口は `exitAll()` の 1 つにまとまる。「tx の終わりに executor に何も残さない」という規則（decision 2026-11-15-executor-no-baked-targets の 3）は、`holding_usd` のある bot では「持ち高だけは残してよい」に変える

### 3-5. プロンプト（common.md・earner.md・paper-reviewer.md）

`holding_usd` のある bot の promote の条件（「end 残高 > start 残高」の代わり）:

1. 買う tx の中で、払う USDC の上限と、受け取る資産の下限（その場のプールの値で USDC に戻したときに元が取れる水準）を確かめ、満たさなければ revert する
2. `exitAll()` は owner だけが呼べ、**いつ呼んでも** 1 tx で全部を USDC に戻して wallet に返す。reviewer は fork で、買った直後と、時間を進めた後の両方で再現する
3. 持つ時間の上限を manifest に書き、過ぎたら bot が自分で `exitAll()` を呼ぶ
4. 最悪の損失（額と、何が起きたらそうなるか）を README に書く。上限は `holding_usd`
5. executor が持つ資産は、出口のプールの厚みが持ち高の 10 倍以上あるものに限る（売れなくなる資産を持たない）

## 4. この案でできないこと

- **すぐに USDC に戻せない型**（償還に待ち時間がある、ロックがある）は対象外。`exitAll()` が「いつ呼んでも」戻せることを条件にしたため。これを外すと、止めたいときに止められない bot ができる
- **利回りを取りに預ける型**（貸し出し、流動性の提供）も、仕組みの上では同じ枠で動くが、200 USD では 1 日数セントにしかならない。枠は「割引で買って売る」型に使うのがよい
- 持ち高の時価の監視はしない。値下がりで止めるのは bot 自身の仕事になる

## 5. 変える場所と大きさの見込み

| 場所 | 変更 |
|---|---|
| farm-watchdog | 停止の線を bot ごとに（manifest の `holding_usd` を読む）、`exit_sent` を既知の nonce に |
| gate-ctl | promote の合計の検査、stop で `exitAll()` を呼ぶ、gate.log の記録 |
| gate.json | `max_holding_usd_total: 200` |
| common.md・earner.md・paper-reviewer.md | L の例外と promote の条件 |
| manifest-check（meta） | `holding_usd` を受け付ける |

gate-ctl と watchdog は資金の境界なので、今までどおり文字列照合のパッチ、オフラインテスト、失敗時の自動復元で作る。USDC を持つ bot の sweep は実資金ではまだ一度も通っていない（仕様書の記載どおり）ので、最初の 1 本は小さい額（`holding_usd` 20 程度）で通す。

## 6. 決めてほしいこと

1. **停止の線を「30 USD + holding_usd」にしてよいか**。枠の合計 200 USD が、そのまま追加の最悪損失になる
2. **1 本あたりの上限**。合計 200 USD のうち、1 本で使ってよい額（案: 100 USD。2 本以上に分けて試せる）
3. **すぐに USDC に戻せる型だけ**に限ってよいか（待ち時間やロックのある型は対象外）
4. **`exitAll()` が失敗したら「未完の stop」で人間に回す**形でよいか
5. **持つ時間の上限の目安**（案: 最長 7 日。manifest に書かせ、reviewer が確かめる）
