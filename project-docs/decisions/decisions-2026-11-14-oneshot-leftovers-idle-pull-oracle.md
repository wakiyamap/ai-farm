# 単発の取り残し、IDLE_BEFORE_STOP、Pull 型の基盤（人間、2026-11-14）

inbox/human の 2 件（2026-11-14-meta-phase11de-followup、2026-11-14-meta-pull-oracle-markets）と、earner の取り残しの測定（attempts 1210、Base の Morpho の wbCOIN）を読んで決めました。

## 1. 単発でも、取れる取り残しは取る

earner は wbCOIN の取り残し（担保 1,504 USD、名目の利益 57 USD、1.8 時間以上だれも取っていない）を、「1 日 1 USD の床の下の単発」として記録だけで終えました。規則どおりの動きですが、規則のほうを変えます。**繰り返さない機会でも、今そこにあって取れるものは取ります。**

### 対象

清算できる状態（または同じように誰でも取れる状態）のまま 10 分以上残っていて、今の head でもまだ残っているもの。同じ形がまた起きるかどうかは問いません。

### 単発に適用しない規則

- 「1 日 1 USD の床」
- 「期待収益が CU の費用を上回ること」（decision 2026-11-12-morpho-stop-researcher-runs の 6）

代わりに、1 回の差し引きで見ます。

### 条件（全部そろったら出す）

- head の fork で、farm の executor が実際に取り、**bot の wallet の残高が増える**成功の tx。利益なしで revert する tx も示す
- 差し引き = wallet の増分 −（executor の配備ガス + 実行のガス + sweep のガス。今の base fee で計算）。これが **10 USD 以上**
- 担保の出口は、実際のプールで換えた額で数える。オラクルの価格で数えない。USR / RLP のように出口のないものは対象外
- **なぜ残っているのかを 1 行で書く**。速い相手のいる所で残っているものには、たいてい理由があります。担保トークンの送金の制限・停止・ブラックリスト、止まっているオラクル、清算の権限を確かめる。理由が「分からない」ままなら出さない
- capital は必要な最小限（元本がフラッシュローンや callback で足りるなら、ガスの分だけ）。bot あたり 400 USD、L 50 USD などの上限はそのまま
- 別の ID で出す（`oneshot-<対象>-<chain>`）。README の先頭に「単発」と書く

### 流れ

1. earner: 見つけたセッションのうちに fork で実証し、paper に置く。paper で機会を待つ必要はない
2. paper-reviewer: 次の回で先に審査する。fork の再現と上の条件がそろっていれば promote してよい。中間ウォレットに資金のないチェーンなら、必要な額を inbox/human に書く
3. bot: 1 回取れたら、または対象が消えたら、それ以上送らずに待つ
4. earner か paper-reviewer: 取れた・消えたを確かめたら inbox/meta に書く。meta が inbox/human に回し、人間が `gate stop` する
5. promote から 48 時間で取れていなければ、同じ流れで停止を勧める

同時に live に置く単発の bot は 2 本まで（次のブロック型の試行の 2 本とは別枠）。

### 今回の wbCOIN

まだ残っているかを head の fork で確かめ、条件を満たせば上の流れに乗せてください。もう取られていれば、attempts に 1 行書いて終わりです。

### これからの取り残しの測定

crash-postmortem の 1-3 と、今後の同じ測定では、「床の下なので記録だけ」で終えず、この条件で見てください。

## 2. `{{IDLE_BEFORE_STOP}}` は 14 日

meta の提案どおり **14 日** にします。meta が live-operator.md を書き換えてください。

watchdog には、この条件で live-operator を起こす処理はありません。今の watchdog が起こすのは、signer の記録にない nonce、1 回の読み取りの間の L を超える減少、promote 以降の損失 30 USD 超、日次損失の上限、bot のサービスの failed だけです。この条件は今は作りません。そのため:

- live-operator.md のその行には、「watchdog には実装がなく、この理由で起こされることは今はない」と分かる書き方をしてください
- 当面は meta が見ます。検知も送信も 14 日ない live bot があれば、inbox/human に停止を勧めてください（decision 2026-11-13-blocked-infra-feed-retriage の 3 と同じ線です）

## 3. Pull 型の基盤は、いずれ作る。今は作らない

pull-oracle-markets の第 1 版の結論（基準に当たる市場は 0、取れそうな唯一の市場は 1 日約 2 USD）を読みました。価格配信を受ける仕組みは**今は作りません。ただし、やらないと決めたのではなく、いずれ作ります。**

- Pull 型の区分は C のままです。D に落とさず、調べる対象から外さないでください
- 第 2 版（Dolomite、Fluid）は出してください
- 基準（取られるまでの秒数が R を超え、30 日の粗利が 300 USD 以上）を満たす市場が出たら、すぐ inbox/human に出してください。作る時期は人間が決めます

## meta へ

1 を earner.md と paper-reviewer.md に、2 を live-operator.md と meta.md に反映してください。手順の細かい所は wiki（`methods/oneshot-leftovers.md`）に置き、役割ファイルには短い案内だけを足してください。プロンプトの大きさ（56,000 バイト以下）は守ってください。数字の線（10 分、10 USD、48 時間、2 本）は人間が置いた目安です。
