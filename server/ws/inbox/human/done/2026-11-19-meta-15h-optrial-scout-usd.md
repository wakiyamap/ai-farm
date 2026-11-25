# meta f5e76c77（2026-11-19 10:0xZ）: 15h の後の arbitrum fork、OP Stack 試行の損失上限の読み方、scout の USD 規則ほか

## 1. 依頼への回答: scout の USD 規則（human-scout-usd-units）

- `prompts/roles/scout.md` の USD の行を書き換えました。USD の数字には必ずトークンを書く（保有・支払いをする契約から on-chain で読んだアドレス、on-chain の `decimals()`、価格の出所と時刻）。価格がなければトークン単位と `usd: unpriced`。ほかのトークンの価格で代えない。プロトコルの規模はプロトコル自身の一覧 getter（`getDebtTokens()` など）から数える（lead 291 は 2 つの debt token の 1 つだけを読んで 5.6k USD と書いた。実際は 301k USD）。7 日呼ばれていない関数で 1 回 10 USD 超なら「未検証」と理由を書く。
- サイズ: scout ロール 5,875 bytes、組み立て後 40,118（上限 56,000 以内）。builder.md と paper-reviewer.md には足していません（builder が今回捕まえたので、その確認で足りると判断）。

## 2. 直接ノード読み取りの数（15g の依頼）

- 指標: scratch にある公開ノード URL（bsc-dataseed, publicnode ほか）を含むスクリプト。11-18 は 3 件以上（avalon-bsc scan2-4.py、fluid_*.py / probe1.py）。
- 11-19 04:00Z 以降に書かれたもの: **0 件**。KB の attempts（04:00Z 以降）にも公開ノード名は 0 件。scout がシェルで curl したかはセッション記録が読めないので数えていません。

## 3. 報告: 15h の後も arbitrum の fork で `public: HTTP 403 Archive`（2026-11-19 08:12-08:14Z）

- paper-reviewer run 57f67367 が `fork reset arbitrum 525390726` の後、PEAS の storage 読み取りで `all providers failed: public: HTTP 403 Archive requests require a personal token`。2 回目の reset も同じ。trial-peapods-arb-arbitrum の審査は `wait` のまま。
- 15h の後なので、fork レーンの古い状態の読み取りが公開ノードに行ったことになります。推測（未確認）: 「約 800 ブロックより古い」の閾値が arbitrum では約 200 秒にしかならず、それより新しいブロックの読み取りは公開ノードにも行ける。arbitrum の公開ノードは最新以外をすべて archive として 403 を返す。**fork レーンは、最新ブロック以外の読み取りをすべて Alchemy だけにする**（少なくとも arbitrum、base、elysium など速いチェーンで）ことを提案します。wiki `pitfalls/fork-past-state-public-nodes.md` に 15h の修正とこの件を書きました（d7158d1）。

## 4. 判断の報告: OP Stack の試行 bot の「1 回の損失 1 USD 以下」（opstack-trial-loss-bound）

- reviewer の読み方が 2 通りに分かれていました。trial-peapods-arb-base は「base の L1 データ費は署名で縛れない、native の wallet（10 USD）が上限なので 1 USD を超える」で `fix`。一方 trial-peapods-base ほか、live の base / optimism の試行 12 本（wallet 10-18 USD）は「署名の上限 + 測った L1 費の見積もりが 1 USD 未満」で通っています。
- decision `2026-11-17-cheap-chain-trials.md` の 1 は「base と optimism は L1 のデータ費も足して見積もる」です。meta はこれを後者（見積もり）の意味と読み、`paper-reviewer.md` の cheap-chain trial の行に「署名の上限 + 測った L1 / operator 費の見積もりで 1 USD 未満、wallet ≤ 18 USD が残りを縛る、wallet を 1 USD 未満にすることは求めない」と書きました（paper-reviewer 組み立て後 53,275 bytes、builder 51,631 bytes）。
- 厳しい読み方（wallet を 1 USD 未満に）が人間の意図なら教えてください。その場合、live の 12 本（trial-aave-base, trial-aave4-base, trial-cv3-buy-base, trial-euler-base, trial-moonwell-base, trial-morpho-cbbtc-base, trial-morpho-eth-base, trial-xlend-base, trial-aave-optimism, trial-cv3-buy-optimism, trial-exactly-optimism, trial-moonwell-optimism）も外れます。
- builder からの質問: `gate promote` は小数の `capital_usd`（0.75）を受け付けますか。manifest-check は受け付けます。

## 5. 報告: base の feed のフィルタが 8 本で満杯（base-feed-filters-full）

- 11-19 07:50Z、base の新しいフィルタに `429 base already has 8 log filters`。重なっているフィルタが 2 組あります（別々の bot なので、自己完結の決まりで統合できない）。新しい base の bot はポーリングになります（trial-peapods-arb-base は 30 秒ごと、74,880 CU/day）。
- wiki `infra/feed.md` に 8 本の上限と満杯のときの扱いを書き（751ac22）、builder.md の feed の行に 1 文足しました。1 チェーン 8 本の上限を上げるかどうかは人間の判断です（meta は急ぎではないと見ています）。

## 6. 報告: builder のセッション文脈が古い項目を出す（builder-queue-stale-entries、scout-leads-unit-and-coverage-errors）

文脈を作るスクリプトは workspace の外なので、人間に回します。
1. 「修正待ちの paper bot: trial-bim-harvest-base」: 修正は 11-18 21:44Z に出ていて、再審査待ち。`review.md` の時刻と bot.py / manifest.yaml の時刻を比べ、コードの方が新しければ「再審査待ち」に出してほしい。
2. 「bot のない measured lead」: 8 件中 6 件は `next_steps` に `TRIAL BOT PLACED`（291, 242, 289, 286, 284, 280）、1 件は `NOT A BUILD TARGET`（288）。bots/paper・bots/live に bot がある lead を除いてほしい。
3. 「Trial bots live: 30 / 10」: 分母が 10 のまま。上限は 30（`2026-11-18-trial-slots-30.md`）。

## 7. gate と live（10:0xZ）

- live 34 本（試行 30 本）、今日の損失 0、capital 1,042.04 USD、frozen なし。
- 送信: ほぼすべての試行 bot が nonce 1（executor のデプロイのみ、送信 0）。trial-flatmoney-arbitrum nonce 5（送信 4）、morpho-nextblock-ethereum nonce 2。
- 14 日の無検出・無送信: まだなし。gearbox-v3-watcher-ethereum は live 開始（11-09 17:44Z）から検出 0（heartbeat 29,191 件で `liquidatable` > 0 が 0 件）、送信 0。**11-23 17:44Z に 14 日**になり、次の meta が停止の推奨を出す予定です。
