# 2026-11-05 資金・共有 fork・変更履歴（inbox/human/2026-11-04-meta-capital-fork-git.md への回答）

## §1 ethereum への入金 → gate の USDC 供給（phase 7）を先に実装し、入金はその後

- gate v1 は bot にネイティブ ETH しか送れない（USDC の供給は未実装）。中間ウォレットに USDC を入れても bot には渡らないので、今 400 USDC を入れても promote はできない。
- 元本の調達方法は規則にしない。フラッシュローンで調達する設計も、bot のウォレットで元本を持つ設計も、どちらも許す。earner は戦略に合う方を選ぶこと。L（1 tx の最悪損失 ≤ 20 USD を tx 自体が保証）は従来どおり。
- 元本をウォレットで持つ bot を live にするための gate 側の対応（promote / fund で USDC を渡す、sweep で USDC を戻す、X の集計と watchdog に USDC 残高を含める、signer の日次送信合計に USDC を含める）を phase 7 として人間側で実装する。cv3-buy-watcher-ethereum が最初の該当 bot なので優先する。
- 入金（USDC 400 + ガス用 ETH）は phase 7 が入った時点で人間が行う。それまで cv3 は paper のまま、reviewer の残りブロッカー（自然発生した機会を実際の手数料上限で取れる証拠）を集め続けてよい。資金待ちで作業を止める必要はない。
- reviewer: gate の資金不足による promote 拒否は、phase 7 と入金が済むまでは最終判断として扱ってよい。

## §2 共有 fork → phase 6k で lease と世代番号を実装

- `fork lease <chain> <minutes> [note]`（最大 60 分）で予約。lease 中は他の run の `fork reset` / `fork replay` が拒否される（`--force` で上書き可、使ったら notes に書く）。`fork release <chain>` で早期解放。
- `fork status` に世代番号（reset のたびに +1）と lease 状態を表示。`send` / `deploy` / `replay` も世代番号を出す。測定の前後で世代が変わっていたら、その測定は無効として扱うこと。
- lease の実体は `scratch/.fork/<chain>.lease`、世代は `scratch/.fork/<chain>.gen`。

## §3 変更履歴 → phase 6k で `ws/history`（git）を追加

- `/srv/farm/ws` 全体を git にはしない（bots や logs を含むため）。代わりに harness が run の終了ごとに `prompts/roles/`、`prompts/common.md`、`ws/tools/` のスナップショットを `/srv/farm/ws/history` に commit する（メッセージは「after <role> run <run_id>」）。
- meta は `git -C /srv/farm/ws/history log / show / diff` と `git -C /srv/farm/ws/wiki log / show / diff` を実行できる。session context の「commits」欄にこの repo の直近コミットを出すのは次の更新で検討する。

## 補足: relay の過去状態

公開ノードは直近 ~1000 ブロック分の状態しか持たない。phase 6k から、head − 800 より古いブロックを指定した状態読み取り（eth_call / getBalance / getCode / getStorageAt / getTransactionCount / estimateGas / debug_traceCall）は Alchemy を先に試す。`fork reset <chain> <古いブロック>` もこれで通るはず。eth_getLogs やブロック・レシート取得は従来どおり公開ノード優先。
