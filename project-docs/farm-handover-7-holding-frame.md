> Farm の仕様書の一部（持ち高の枠、phase 12d）。1 つ目の文書と一覧は `farm/farm-handover.md`。
> 2026-11-15 に足した 7 つ目の文書。`farm/farm-handover.md` の「文書の一覧」と各節、`farm/farm-handover-6-phases.md` の表には 11-15 に反映済みで、そちらには要点だけがある。12d の細目はこの文書が正本。

# Farm 仕様書（続き）: 持ち高の枠（phase 12d）

2026-11-15 作成 · **状態: 11-15 14:05 JST（05:05Z）にサーバーへ適用済み**。枠を使う bot はまだない（`gate status` の `holding_usd` は合計 0 / 200）

## 何のための仕組みか

今までの Farm は「1 つの tx の中で残高が増えなければ revert」（11-03 の選択 A、common.md の L）に当てはまる bot しか live に出せなかった。11-15 の人間の判断で、次の型に合計 200 USD までの枠を作った。

> USDC を持って待つ → USDC で別の資産を買う → しばらく持つ → 売って USDC に戻す

買う tx と売る tx が別なので、その間は値下がりの危険を持つ。設計書は `farm/design/design-2026-11-15-holding-frame.md`、エージェント向けの文面は `farm/decisions/decisions-2026-11-15-holding-frame.md`（サーバーでは `decisions/human/2026-11-15-holding-frame.md`）。

## 上限（コードが強制するもの）

| 項目 | 値 | どこで強制 |
|---|---|---|
| 枠の合計 | 200 USD（gate.json `max_holding_usd_total`） | gate（promote。live の bot の `holding_usd` の合計 + 新しい bot の分。止めかけで live に残っている bot も数える） |
| 1 本あたり | 100 USD（gate.json `max_holding_usd_per_bot`） | gate（promote）、watchdog（manifest の値がこれより大きくても、これを上限として扱う） |
| 元手 | `holding_usd` ≤ `principal_usdc` | gate（promote） |
| 持つ時間 | `holding_max_hours` が 0 より大きく 168 以下（7 日。gate.json に `max_holding_hours` があればその値） | gate（promote。値があることだけを確かめる。**時間が過ぎたかどうかはコードは見ない**。売るのは bot、確かめるのは reviewer） |
| 出口 | executor の artifact の ABI に、引数なしの `exitAll()` があること | gate（promote。中身は見ない。確かめるのは reviewer） |
| 累計損失の停止 | 30 USD + `holding_usd`（`holding_usd` 100 なら 130 USD） | watchdog |
| 1 回の読み取りの間の減少 | L（50 USD）+ `holding_usd` | watchdog |

- gate.json に 2 つのキーがなければ枠は無効: gate は `holding_usd` のある promote を断り、watchdog は `holding_usd` を 0 として扱う（今までの 30 USD / 50 USD の線のまま）
- `holding_usd` を書かない bot（0 や空欄も同じ）は、gate も watchdog も今までと同じ動き
- 枠の合計 200 USD が、そのまま追加の最悪損失になる（人間の判断 1）。**持ち高の時価は誰も見ない**。値下がりで売るのは bot 自身の仕事で、bot が何もしなければ `holding_usd` の全額を失うまで止まらない
- X（2,000 USD）には executor の中の持ち高は数えられない（最大 200 USD ぶん小さく見える）
- signer は変えていない。bot が USDC を自分の executor に送る tx は今までも通り、その額は 1 日の枠（`capital_usd`）に足される。1 日に何往復もする bot は `capital_usd` を大きくするか、executor に使う額だけ承認して引き出させる形にする

## manifest

```yaml
holding_usd: 20          # 別の資産で持ってよい上限（USD）。書かない・0・空欄なら今までどおり
holding_max_hours: 24    # 持つ時間の上限。168 以下
principal_usdc: 20       # holding_usd 以上
executor: ...            # 必須。ABI に引数なしの exitAll()
```

live の manifest は gate しか書けないので、watchdog と gate はこの値をそのまま読む。数字として読めない値は、promote では拒否、watchdog では 0 扱い、stop では「持ち高がある」扱い（`exitAll()` を試す）。

## gate promote

`holding_usd` が 0 より大きい manifest では、資金を動かす前に次を確かめ、どれかに当てはまれば断る（メッセージの末尾は `nothing was moved or funded`）。

1. gate.json に `max_holding_usd_total` と `max_holding_usd_per_bot` がない
2. `holding_usd` が 1 本あたりの上限を超える
3. `holding_usd` が `principal_usdc` を超える
4. `executor:` がない
5. artifact の ABI に、引数なしの `exitAll` がない
6. `holding_max_hours` がない、0 以下、168 を超える
7. live の合計 + この bot の分が枠の合計を超える

通ったら、gate.log の `promote` の記録に `holding_usd` が入る。

## gate stop（`exitAll()` を呼んでから sweep）

`holding_usd` のある bot では、サービスを止めて未確定の tx を取り消した後、sweep の前に次をする。

1. executor のアドレスを **gate.log の `deploy_executor` の記録**から取る（その bot が最後に archive された後のもの）。`state/executor.json` は bot が書ける場所なので、そこのアドレスは「bot の鍵と記録の nonce から導いたアドレスと一致するもの」だけを補助に使う。executor が一度も配備されていなければ `exit_skipped` を記録して普通の sweep に進む
2. チェーンごとに、bot の鍵から executor へ `exitAll()` の見積もり（`eth_estimateGas`）を取る。**見積もれない（revert する）ときは tx を送らない**ので、ガスはかからない
3. ガスの上限は見積もりの 1.5 倍（チェーンの 1 tx の上限まで）。最悪額（ガス上限 × maxFee）が L（50 USD）を超えるなら送らない
4. bot の wallet のガスが足りなければ、中間ウォレットから足す（`exit_gas_topup`。baseline に足す。sweep のガス補充と同じ扱い）
5. 送る。送信の直後に nonce つきで `exit_sent` を gate.log に書き、レシートを最大 180 秒待つ
6. 載って成功したら、executor に USDC が残っていないこと、ネイティブが 1 USD 相当を超えて残っていないことを確かめ、`exit`（nonce、`usdc_back` = wallet の USDC の増分）を記録する
7. 全チェーンで済んだら、今までどおり sweep して archive する

**失敗したとき**（見積もれない、送信の呼び出しが失敗、180 秒で載らない、載って revert、executor に USDC かネイティブが残っている、最悪額が L を超える）: `exit_failed` を記録し（tx を送った場合は nonce と txHash つき）、**何も sweep せず**、bot は bots/live に残り、`stop_incomplete` を記録して終了コード 3（メッセージは `its holdings are NOT back`）。X にも数えられ、watchdog も見続ける。sweep しない理由: wallet に残っている分だけを戻すと、戻っていない分が実現損失として記帳され、やり直しのためのガスもなくなるため。

- ここから先は人間が決める（人間の判断 4）。原因を gate.log の `exit_failed` で見て、`gate stop <id>` をやり直すか、手で回収する
- 2 つのチェーンのうち片方だけ失敗した場合も、もう片方の `exitAll()` は試す。sweep はどちらもしない
- **`exitAll()` の tx が 3 本失敗したら、gate はそれ以上送らない**（載って revert、載らない、残高が残った、のどれも 1 本と数える。見積もりで止まったものは数えない）。watchdog は終わらなかった停止を 10 分ごとにやり直すので、そのたびにガスを使わないための歯止め。続けるときは人間が `--exit-again` をつける（下のコマンド）。数は成功した `exit` か archive で 0 に戻る
- `exitAll()` は公開の mempool に、最低受取額なしで出る（gate は最低受取額を計算できない）。`send_route: private` の bot でも同じ
- `gate sweep <id>` は今までどおり wallet の中だけを戻す（`exitAll()` は呼ばない）
- `gate stop --all` でも同じ流れ。出口が失敗した bot は live に残り、ほかの bot は止まる

## gate status

`holding_usd` の欄が増えた: `{"live": {<bot>: <USD>}, "total": <合計>, "max_total": 200, "max_per_bot": 100}`。

## watchdog

- live の manifest から `holding_usd` を読み（1 本あたりの上限まで）、その bot の 2 つの線を上げる: 累計損失の停止が 30 + `holding_usd`、1 回の読み取りの間の減少が L + `holding_usd`
- 後者は設計書になかった変更。今までの「読み取りの間に L（50 USD）を超えて減ったら止める」のままだと、50 USD を超える買いをした瞬間に止められるため。累計の線のほうが先に効くので、最悪の損失は増えない
- 起こすときの文面に線の内訳が出る（`limit 130 USD = 30 + holding_usd 100`）
- gate.log の `exit_sent` / `exit` / `exit_failed`（nonce つき）は既知の nonce として扱う（鍵の漏洩と見なさない）

## プロンプト

- common.md: L の項に Holding frame の段落（例外の内容、同じチェーンでいつでも 1 tx で USDC に戻せること、持ち高は executor に置き `exitAll()` で戻すこと、時価は誰も見ないこと）。Live-loss stop に「枠の bot は 30 + `holding_usd`」
- roles/earner.md: 1 節の保有型の規則を「枠の中なら作ってよい、外なら lead に記録して止める」に、3 節の 2 を合わせて直し、5 節に Holding frame の項、manifest のひな形に 2 つのキー
- roles/paper-reviewer.md: Holding frame の段落（promote の条件。下の「審査」）
- roles/live-operator.md: 終了コード 3 の `its holdings are NOT back` は `gate stop` をやり直さず inbox/human に書く
- 組み立て後の大きさ: earner 54,952、paper-reviewer 47,948、researcher 39,380、live-operator 36,443、meta 35,846 バイト。**earner は 56,000 まで 1,048 バイト**。meta に、細目を wiki `methods/holding-frame.md` に移して earner の項を短くするよう頼んである

審査（プロンプト側の規則。コードは強制しない）: 買う tx の成功と、値段が合わないときの revert を fork で再現。`exitAll()` を「買った直後」と「時間を `holding_max_hours` より先に進めた後」の両方で呼び、1 tx で USDC が wallet に戻り executor に何も残らないこと、owner 以外からは revert すること。出口のプールの厚みが持ち高の 10 倍以上。README に最悪の損失。期待収益は 1 往復ごと（売って戻った額 − 買った額 − 2 本ぶんのガス）で、損の往復もマイナスで数える。出口に待ち時間のあるものは demote。最初の 1 本は `holding_usd` 20 程度。

## できないこと、確かめていないこと

- すぐに USDC に戻せない型（ブリッジ、ロック、償還の待ち）は対象外
- 持ち高の時価の監視、持つ時間の強制はしない
- **実資金では何も確かめていない**。USDC を持つ bot の sweep 自体が実資金でまだ一度も通っておらず、`exitAll()` の流れも同じ。オフラインテスト 37 件は、適用時にサーバーの本物の farmkeys で全部通った（作業環境では代用品を使っていた）
- manifest-check はまだ `holding_usd` を見ない（未知のキーは通す。meta に頼んである）
- TOOLS.md の gate の行は直していない（meta に頼んである）

## コマンド

| やりたいこと | コマンド |
|---|---|
| 枠の使用量を見る | `sudo -u harness /opt/farm/bin/gate status` の `holding_usd` |
| 枠の bot を止める | 今までどおり `sudo -u harness /opt/farm/bin/gate stop <id>`。「its holdings are NOT back」（終了コード 3）で終わったら、gate.log の `exit_failed` を見る: `sudo grep '"exit' /var/lib/farmgate/gate.log \| tail` |
| 失敗が 3 本たまった後にもう一度 `exitAll()` を送る | `sudo -u farmgate /opt/farm/bin/gate-ctl stop <id> --exit-again`（`gate` のラッパーがこの引数を通すかは未確認なので、gate-ctl を直接呼ぶ） |
| 枠の大きさを変える | `/etc/farm/gate.json` の `max_holding_usd_total` / `max_holding_usd_per_bot` を直し、`sudo systemctl restart farm-watchdog`（gate-ctl は毎回読む） |
| 12d を戻す | `/opt/farm/bin/.gate-ctl.bak-12d`・`.farm-watchdog.bak-12d`・`/etc/farm/gate.json.bak-12d` を戻して farm-watchdog を再起動、プロンプトの `.bak-12d`（common.md は `/srv/farm/prompts/.common.md.bak-12d`）を戻し、decision と meta 宛てメモを消す |

## 設計書との違い

設計書（案）から、実装で足した・変えたもの。

1. watchdog の「1 回の読み取りの間の減少」の線も L + `holding_usd` にした（設計書は累計の線だけ）
2. executor のアドレスは `state/executor.json` ではなく gate.log から取る（bot が書ける場所を信用しない）
3. `exitAll()` が失敗したら、wallet にある分の sweep もしない
4. 失敗した `exitAll()` の tx は 3 本まで、その先は `--exit-again`
5. `holding_max_hours`（168 以下）と、ABI の `exitAll()` を promote で確かめる
6. gate.json に `max_holding_usd_per_bot`（100）も足した（設計書の表は合計だけ）
7. `gate status` に枠の欄

## フェーズ履歴の行（`farm/farm-handover-6-phases.md` の表にも同じ行がある）

| phase | 内容 | sha256（先頭 16） |
|---|---|---|
| 12d | 持ち高の枠（USDC → 別の資産 → USDC、合計 200 USD）。gate-ctl（文字列照合 11 箇所）: promote で `holding_usd` の検査（1 本 100・合計 200・`principal_usdc` 以下・executor の `exitAll()`・`holding_max_hours` 168 以下）、stop で sweep の前に `exitAll()`、失敗したら何も sweep せず終了コード 3、失敗 3 本で `--exit-again` 待ち、status に枠の欄。farm-watchdog（7 箇所）: 枠の bot の線を 30 + `holding_usd` と L + `holding_usd` に、`exit_sent` / `exit` / `exit_failed` を既知の nonce に。gate.json に `max_holding_usd_total: 200`・`max_holding_usd_per_bot: 100`。プロンプト 4 つ（common.md 16,638 → 17,358、earner.md 22,002 → 22,942、paper-reviewer.md 13,684 → 15,938、live-operator.md 3,977 → 4,433 バイト）、decision 2026-11-15-holding-frame、meta 宛てメモ。オフラインテスト 37 件（適用前のファイルで 7 件、パッチ後 37 件）。インストール済みのファイルが想定の sha256 と同じときだけ進み、farm-watchdog を再起動、戻らないか `gate status` が失敗すれば gate-ctl・farm-watchdog・gate.json を復元。farm-signer・rpc-relay・unit は変更なし（11-15 14:05 JST = 05:05Z 適用。バンドルの sha256 一致、プロンプト 4 つと gate-ctl・farm-watchdog は「as expected」、パッチ 11 + 7 箇所一致、本物の farmkeys で適用前 7 / 37 → 適用後 37 / 37 ALL PASS、適用後の sha256 は 2 つとも想定どおり、farm-watchdog と farm-signer は active、`gate status` は総資金 880.03 USD・`holding_usd` 合計 0 / 200、live 3 本は active / running のまま、組み立て後は見込みどおり earner 2 本 54,952・paper-reviewer 47,948・researcher 2 本 39,380・live-operator 36,443・meta 35,846 バイト、decision とメモは配置済み） | 513f1be375f43b98 |

バンドル `farm-phase12d.tgz` の sha256: `513f1be375f43b984a1f4c87b3b39230924f948f7a24adc02a7176370929cbea`。中身は Project の `farm/phase12d/`。

| ファイル | 適用前の sha256 | 適用後の sha256 |
|---|---|---|
| `/opt/farm/bin/gate-ctl` | `833c03537d3c28b6de9fda13d11d34eee9309a418fd547b48000e63364714351` | `dc0d8d5a64d2b70b874576d1c2b0d9b1fad95285fa9681127dca7853d9430828` |
| `/opt/farm/bin/farm-watchdog` | `5b1a3d24a97a847e63fc442dee0fd3b8f2260aa560377461a4a6d497a8df6a33` | `4f692e414c9825168d879e15e4455725536038d48946d02bce5e8fcbe5ea13f9` |
| `/srv/farm/prompts/common.md` | `8b5f9671cbcd15ea320a6015bc102c24ba6c712980b7011f4298a9af7b4daf2e` | `279993efca599b1ac413a0909c0fc895d48f0a71b5e8535cd5dc9097dcb712a7` |
| `roles/earner.md` | `474b6640e4de9e35acb3d66305e5f5e0a2b859b6139c667762d14da4f94a5fa9` | `0b42f773353981c86eefd80904d37c1a84f5c278650adaef996675b7812dfcac` |
| `roles/paper-reviewer.md` | `881c9a9af356b375cef315f631b6bca1f290e8bc65819326ed97341e5fae2fe4` | `414ce6dea2460441c9fe2e2c6e4164c003e957e69f4229692e27603980d7f870` |
| `roles/live-operator.md` | `ba530f631cf3706cdb1e4c107688f61a4b2c4a93369c1c5ca1287da5e7838ef9` | `c40c8c682bafb31fe98d9e6c66c99738092d5221e7b7da140cfe2f22489a528f` |
| `/opt/farm/bin/farm-signer`（変更なし） | `3a55bfbc379c570a85c3896416864f4ca94c57fe67e0810ccbed32157469ec32` | 同じ |
