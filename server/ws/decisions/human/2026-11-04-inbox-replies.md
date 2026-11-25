# 2026-11-04 inbox/human 4 件への回答（人間）

## 1. inbox/meta のファイル権限（2026-11-03-meta-inbox-permissions.md）

phase 6（11-03 夜）で inbox/*・bots/paper・scratch・claims・logs に group farm の default ACL を設定済み。それ以前に作られたファイルは手で group 読み取り可にした。以後は新規ファイルは読めるはず。読めないファイルがまた出たら、ファイル名と `ls -l` の結果を inbox/human に書いてほしい。

## 2. signer でコントラクトをデプロイできるか（2026-11-03-meta-signer-contract-deploy.md）

phase 6 で解決済み。signer の `send()` は引き続き `to` 必須で、bot 自身はデプロイしない。代わりに gate が promote 時に manifest の `executor:`（forge artifact のパス）を bot の鍵でデプロイし、そのアドレスを signer の許可先に自動追加する（`gate-ctl deploy_executor`）。

- (a) 公開 CREATE2 deployer を allowed_contracts に入れる方法は認めない（不要になったため）。
- (b) signer への `op: "deploy"` 追加も行わない。デプロイは gate の責務。
- 「小額ルート」は不要。executor 経由が唯一の live 経路（common.md の L、earner.md 3b）。

まだ実際の promote でデプロイを実行した例はない。最初の promote が初回の実デプロイになるので、reviewer は promote 直後に `gate status <id>` で executor アドレスが出ていることを確認してほしい。

## 3. meta からのインフラ依頼 3 件（2026-11-03-meta-infra-requests.md）

すべて phase 6c（2026-11-04 適用）で対応した。

1. paper-reviewer のキュー: `next_review_at: null` を期限切れ扱いしていたのはキュー生成スクリプトのバグ。null / none は「予定なし」とし、代わりに review.md より新しいファイル（bot.js・manifest・contracts 等）がある bot を `CHANGED` として出す。`due` が `no` の bot は 1 行記録で済ませてよい（paper-reviewer.md に入れたスキップルールと整合）。
2. RPC relay: 上流の応答を 8 MiB で切ってパースに失敗し、その provider を 30 秒 cooldown にしていたのが「no provider available」の原因。応答上限を 32 MiB に上げ、超えた場合は provider を休ませずに呼び出し元へ「response larger than 32 MiB; narrow the block range or filter」を返すようにした。8 MiB 超の eth_getLogs はブロック範囲を分けてほしい。
3. `ledger query --json "<SQL>"` を追加。1 行 1 JSON オブジェクト、セルの切り捨てなし（行数上限 50 はそのまま）。TOOLS.md への反映は researcher か meta にお願いしたい。

## 4. executor の在庫保護に関するセキュリティ所見（e9a6679c-executor-inventory-security.md）

読んだ。人間側の対応は不要で、修正は earner、判定は paper-reviewer に任せる。earner の aave-watcher-base v3（11-04 07:07 のセッション）が 6 件のブロッカーへの対応を提出しているので、reviewer は v3 の executor ソースで operator 認証・swap 先の制限・在庫保護が入っているかを確認してから判定すること。promote の条件は変えない。
