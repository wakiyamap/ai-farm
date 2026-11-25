# 2026-11-07 ワークスペース外ツールの 4 件（inbox/human/2026-11-07-meta-infra-requests.md への回答）

## §1 web_search

- 鍵は設定しない（2026-11-06 の判断どおり）。harness からツールを外せるかは人間側で確認中で、外せたら別途書く。
- それまでのあいだ earner は web_search を呼ばないこと。アドレス探しは web_fetch（DefiLlama の adapter リポジトリ、プロトコルの docs、GitHub）か、エミッタースキャンで行う。web_search の鍵エラーを inbox/meta に報告するのも、これ以降は不要。

## §2 relay の eth_getTransaction

- `eth_getTransaction` という JSON-RPC メソッドは存在しないので、-32601（method not found）が正しい応答。正しい名前は **`eth_getTransactionByHash`** で、relay ではこれまでも許可されている（20 CU。キャッシュあり）。calldata は戻り値の `input` 欄にある。meta はこの点を TOOLS.md に書くこと。

## §3 eth_getLogs のアドレス配列

- relay は配列の長さを検査していない。拒否しているのは上流のノード（主に公開ノード）。上限はプロバイダごとに違い、保証できない。
- 決め事: 1 回の eth_getLogs に渡すアドレスは **32 個まで**。それより多いときは 32 個ずつに分けて呼ぶ。メソッドで絞り込めるなら topic だけで（アドレスなしで）スキャンし、アドレスはクライアント側で絞り込んでもよい。ただし Base の公開ノードはアドレスなしの getLogs を拒否する。meta はこれを TOOLS.md に書くこと。

## §4 ledger add-source のタプル型

- 当面は対応しない。Dolomite は blocked_infra で閉じていて、GMX は対象外。タプル型のイベントが必要な bot 候補が実際に出てきたら、もう一度 inbox/human に挙げること。
