# meta 1b442801 からの依頼 3 件 (2026-11-08)

## 1. relay の状態読み取りが全レーンで空を返した (17:14-17:25Z)

earner run eeccd209 が生のリクエスト/レスポンス付きで記録しました: `scratch/relay-state-empty-eeccd.json`、メモは `inbox/meta/2026-11-08-relay-state-reads-empty.md`。

- ethereum: eth_getCode(USDC) = "0x"、eth_call(balanceOf) = "0x"、eth_getBalance(Binance8) = 0、getStorageAt = 0。paper/live/research の全レーン、latest でもブロック番号指定でも同じでした。base の eth_call も空でした。
- 正常だったもの: blockNumber、getLogs、ブロックヘッダ、alchemy_getAssetTransfers。research レーンの CU は 187888/500000 で、予算切れではありません。
- 同じ URL に `cast call` しても "no code" が返りました。呼び出し側のミスではありません（earner.md の確認手順はすべて満たしています）。
- 影響: anvil fork (9003) も relay から状態を取るので、その間の fork 証明と paper シミュレーションがすべて空状態で動きました。ガードが NoProfit で revert するため損失はありません。
- 18:39Z の run a955115c では状態読み取りが戻っていました。
- お願い: この時間帯に relay が状態系メソッドをどこへ振っていたか、ログを確認してください。午前の `2026-11-08-meta-relay-ethereum-research-anomalies.md`（getCode -32602、getLogs が空）と同じ系統の可能性があります。

## 2. 1inch Fusion API キー（earner から 2 通届いた件をまとめます）

`2026-11-08-1inch-fusion-api-key.md` と `2026-11-08-dtf-1inch-api-key.md` は同じ依頼です。reserve-folio-dtf-ethereum の venue 脚に使う見積りは、1inch のキー必須 API からしか取れません（キーなしでは 401）。

- この 2 通は earner の権限外です（earner が inbox/human に書けるのはセキュリティ所見だけです）。earner.md を修正し、今後は `leads` の `needs_human:` 行として記録させ、meta がまとめて転送します。
- **注意**: 依頼文はキーを `bots/paper/<id>/state/fusion_key.json` に置くよう求めています。ワークスペースは全エージェントが読めるので、資格情報の置き場所として不適切です。採用する場合は gate/signer 側で保持する形を検討してください。
- 経済性はまだ確定していません。lead 91/94 の見積りでは全体のプールが 70-130 USD/日で、既存の入札者が 4 人います。paper-reviewer の最新判定は fix です（principal 変換に保護がない、実際の venue での成功例がない）。meta としては、急いでキーを出す必要はないと考えます。

## 3. `paper restart` / `paper start` の挙動（`inbox/meta/paper-ctl-restart-active.md`）

- サービスが active のとき `paper restart` は "restart failed ... result running" を返し、再起動しません。
- `paper stop` の直後に `paper start` すると "start failed" と出ますが、実際には新しいコードで起動しています。
- `paper` コマンドはワークスペースの外にあるため meta では直せません。提案: active なら start を成功扱いにし、restart は実際に再起動する。stop は停止が終わるまで待つ。
