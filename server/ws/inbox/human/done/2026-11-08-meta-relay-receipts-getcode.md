# relay: receipt が null になる件 と eth_getCode の件への回答（meta 36a66faf, 2026-11-08）

## 1. eth_getTransactionReceipt / eth_getBlockReceipts が null を返す（依頼）

3 つのセッションが別々に報告しています。いずれも ethereum の research レーンで、エラーは出ずに `result: null` が返ります。同じ tx に対する eth_getTransactionByHash、eth_getLogs、debug_traceTransaction(callTracer) は成功しています。

| 日付 | run | 再現できる tx / ブロック |
|---|---|---|
| 11-06 | researcher d308bfc8 | tx 0x46e5ecec7c78dfe6e96fc77498337ba4d8a6d6de11fed9ff6f4d4631755ae728（ブロック 26160395）。同じブロックへの eth_getBlockReceipts も null |
| 11-07 | earner dc4562f7 | tx 0xce2bd21682a6cda378a1e87933c3fb32ea930df3009222b51421b534ea088733（ブロック 26329900） |
| 11-08 | earner 82055fec | ブロック 23515617 の清算 tx |

お願い: 古いブロックの receipt も、状態の読み取りや trace と同じように Alchemy を優先するか、null が返ったら Alchemy に再問い合わせするようにしてください。それまでの回避策（ブロック番号で eth_getLogs を取り transactionHash で絞る、または trace を使う）は TOOLS.md の relay 行に書きました。

## 2. 「eth_getCode が既知のコントラクトに 0x を返す」件（11-08 の判断 §meta への確認事項への回答）

ノート（inbox/meta/relay-eth-getcode-empty-known-contracts.md）に書かれている条件は次のとおりです。
- run: earner a279553d、2026-11-07（セッション報告の並びから 17〜18 時 UTC ごろ）
- レーン: ethereum の research
- ブロック指定: `"latest"` と、そのときの先頭ブロックの番号（約 26364800）の両方
- 0x が返ったアドレス（4 件とも大文字小文字の混じったチェックサム表記）: 0x87870Bca3F3fD6335C3F4f8307Fcf24007E6eF5b（Aave V3 Pool）、0x1F98430969A57124529677A665539560880E4AeF、0x5C69bEe701ef98a540404BdE40a2A6B6A7f4697f、0x7a250d5630B4CF0795886e19A6bE22F2e0721B9c
- 同じ「バッチ」で USDC と WETH にはコードが返った。ノートでは対照の 2 件を小文字（0xa0b8… / 0xc02a…）で書いている

生のリクエストとレスポンスは残っていません（scratch に getCode のスクリプトがありません）。meta からは curl が使えないので、再現も試せません。

手がかりが 2 つあります。
- 別の earner（9484988b, 11-07）が「Pendle の factory への eth_call で、大文字小文字の混じった `to` だと revert / 空が返り、小文字なら通った」と報告しています。
- ノートには「同じバッチ」と書かれています。JSON-RPC のバッチ（配列）リクエストだった可能性があります。

お願い: 上の 4 アドレスを **チェックサム表記のまま**、さらに **USDC と一緒の JSON-RPC バッチで** 1 回ずつ試してください。どちらでもコードが返れば、earner の誤り（アドレスの書き間違い、または読み方の誤り）として閉じてください。meta 側では、次に報告があれば生のリクエストとレスポンスを残すように頼みます。なお、ノートで「V3 router」とされている 0x7a250d… は実際には Uniswap V2 Router02 で、ラベルにも誤りがあります。

## 3. Base の eth_getLogs で、複数アドレスの配列がときどき拒否される（参考）

earner 95a7bdc8（11-07）からの報告です。Base の research レーンで、`address` に 4 件の配列を渡すと、ときどき `-32602 ... untagged enum Variadic` が返ります。同じパラメータでも通ることがあり、1 アドレスずつなら 33 回中 33 回成功しました。公開ノードに回されたときの挙動と思われます。回避策（1 アドレスずつ）を TOOLS.md に書きました。relay 側で、Base の複数アドレスのリクエストを Alchemy に回すか、公開ノードで -32602 が返ったら分割して再試行するようにしていただけると助かります。
