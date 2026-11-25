# 2026-11-09 relay の空応答、1inch キー、paper-ctl、小さなツール改善（inbox/human の 11-08 分 6 件への回答）

## §1 relay の状態読み取りが空・null・-32602 になる件（phase 6y）

- 原因の見立て: ethereum の paper / research レーンは、公開ノードを先に使う。一部の公開ノードは、状態や receipt を持っていないとき（刈り込み済み、遅れている、壊れている）に、エラーではなく `0x` / null / -32602 を返す。relay はそれを正しい答えとして返し、しかもキャッシュはレーン共通なので、`0x` がキャッシュに残ると live レーンにも同じ答えが返る可能性があった。11-08 17:14-17:25Z の「全レーンで空」はこの経路と考える。
- phase 6y から次のようにした。
  - 公開ノードが返した eth_getCode / eth_call の `0x` と、receipt の null は、次のプロバイダ（Alchemy）でもう一度確かめる。Alchemy が空でない答えを返したら、その公開ノードは 5 分間使わない。
  - こうした空の答えはキャッシュしない。
  - 公開ノードのエラーは、revert 以外（-32602 Variadic / invalid string length、「address を指定せよ」、範囲の上限）なら次のプロバイダに回す。呼び出しは失敗させない。
- これで、TOOLS.md の回避策（from を付ける、1 アドレスずつ、receipt の代わりに getLogs）は不要になるはず。ただ、残しても害はない。meta は 6y 以降に同じ種類の報告が出るかを数え、出なければ回避策を「不要になった」と書き換えること。wiki の `pitfalls/relay-ethcall-from.md` は「未確認」のままでよい。
- meta が頼んだ getCode の確認（チェックサム表記の 4 アドレスを USDC と同じバッチで送る）は、6y を入れた後に人間が行った。結果: USDC にはコードが返り、4 アドレスはすべて `0x`。publicnode と drpc に直接聞いても `0x` で、Etherscan でも 0x87870Bca…6eF5b は EOA（コントラクトではない）だった。つまり、これは relay の不具合ではない。**記憶から書いたアドレスが実在のコントラクトと違っていた**（人間側の Claude も同じ誤りをした）。この件は earner の誤りとして閉じる。
- 教訓（wiki の address-hunt に追記すること）: 有名なコントラクトのアドレスでも、記憶から書いたものは 1 文字違いの別アドレスになりうる。アドレスは必ず一次情報（プロトコルの公式デプロイ一覧、GitHub の deployments ファイル、エクスプローラ、オンチェーンの getter）から取り、`eth_getCode` で確かめてから使うこと。「既知のアドレスにコードがない」と感じたら、relay を疑う前に、まずアドレスの出所を疑うこと。

## §2 1inch Fusion API キー（reserve-folio-dtf-ethereum）

- 当面は出さない（meta の判断に同意する）。理由:
  - reviewer の最新の判定は fix で、ほかの指摘（在庫の消費に上限がない、実際の venue での成功例がない）も残っている。
  - 対象全体でも 1 日 70-130 USD 程度で、既存の入札者が 4 人いる。
  - 資格情報をワークスペース（全エージェントが読める場所）に置く方式は採らない。
- 再検討の条件: キー無しで直せる指摘がすべて解消し、reviewer が「残りはキーだけ」と書いたとき。その場合、キーは /etc/farm に置き、bot には relay と同じように見積りの中継だけを提供する形にする（bot にキーそのものは渡さない）。
- earner: lead 103 は blocked_infra のままでよい。同じ依頼を inbox/human に出し直さないこと（meta がまとめて転送する）。

## §3 paper start / restart の誤った失敗表示（phase 6y）

- 人間側のバグだった。phase 6s で入れた状態確認が、`systemctl show --value` の出力を -p の順に並んでいると決めつけて読んでいた（systemctl は自分の順で出力する）。そのため、正常に動いているのに「failed ... result running」と表示していた。6y で key=value の形で読むように直した。
- 6y 以降、`paper start` / `paper restart` が ok を返したら、実際に動いている。

## §4 小さなツール改善（2026-11-08-meta-small-tool-asks.md）

- ledger add-source のエラーに計算した keccak を出す件: やる。ledger-ingest のソースを確認してから、次のバンドルに入れる。それまでは、`cast keccak "<event string>"` で比べること。
- パイプ付きの kb の拒否メッセージ: 権限の判定は harness（Claude Code / dsh）側で行っていて、Farm からは文言を変えられない。common.md の「kb は単独で実行」と、`tools/kb-file.py` で対処する。

## 処理済みとして閉じる inbox/human

2026-11-08-meta-relay-receipts-getcode、2026-11-08-meta-relay-ethereum-research-anomalies、2026-11-08-meta-small-tool-asks、2026-11-08-meta-relay-state-1inch-paperctl、2026-11-08-1inch-fusion-api-key、2026-11-08-dtf-1inch-api-key
