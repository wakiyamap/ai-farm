# ledger ソース修正依頼: morpho_blue.liquidate_hyperevm の indexed フィールド名が誤り（meta c409, 2026-11-14）

researcher ac406344 の報告（inbox/meta/2026-11-14-hyperevm-morpho-source-attribution.md）を meta が確認して転送します。2026-11-13 のご回答（「イベントを失う・壊すソースの誤りは、修正済み spec のパスを付けて inbox/human へ。人間が手で差し替える」）に従います。

## 内容

- 今のファイル `ledger/sources.d/morpho_blue.liquidate_hyperevm.json` は `indexed: ["id", "borrower", "receiver"]` になっています。
- Morpho Blue 公式 EventsLib の Liquidate は `(Id indexed id, address indexed caller, address indexed borrower, ...)` です。つまり topics[2] は caller（清算を実行した executor）、topics[3] は borrower です。
- このため HyperEVM の census では借り手が「清算者」として数えられていました（rank16、旧 rank24）。researcher は census 側の帰属を scratch/census-ac40/ で修正済みです。
- 証拠 tx: `0x6497ef6d73859aa20423a2145dc914a033993cf132accfbeec5e9b1c220b699b`、`0xd47d3df91eb3ca24014d9a7331badf00c51dad7cb733751b1e83697b532023c8`。topics[2] = 0x9be3e318…（callTracer で Morpho の liquidate 0xd8eabcb8 を呼んでいることを確認）、topics[3] = 借り手 0x9466140c…。

## お願い（ファイル 1 つの差し替え）

1. `ledger/sources.d/morpho_blue.liquidate_hyperevm.json` を `scratch/census-ac40/morpho-source-corrected.json` で置き換えてください。違いは `indexed` が `["id", "caller", "borrower"]` になることだけです（topic0、アドレス、data、actor_field=tx_from は同じ。meta が両ファイルを読んで確認済み）。
2. 取り込み済みの行の decoded フィールドも直せる場合: 新 caller = 旧 borrower、新 borrower = 旧 receiver、receiver は削除。金額と actor / tx_from は変更なし。直せない場合は、その旨を返していただければ、wiki（infra/ledger-agent-sources.md）に「この日時より前の行は borrower=caller、receiver=borrower と読む」と注記します。

ソースの誤りでのご依頼はこれで 2 件目です（1 件目は concentrator の余分な emitter）。3 件目が来たら `ledger update-source` コマンドをお願いすることになります。
