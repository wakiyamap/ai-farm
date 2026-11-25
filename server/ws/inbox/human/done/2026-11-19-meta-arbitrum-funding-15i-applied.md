# arbitrum の資金不足（承認済みの試行 3 本）、15i の反映、trial-aave-base の停止（meta 9c24f7f1, 2026-11-19 22:2xZ）

## 1. arbitrum が足りません（判断 2026-11-20-trial-slots-45 の 3 による連絡）

paper-reviewer（run 5ba2cc1c, 19:31Z）からの依頼を転送します（paper-reviewer は inbox/human に書けないため）。

- 技術の審査が済んで `wait (parked: approved, waiting for Arbitrum funding)` の bot が 3 本: `trial-dolomite-arbitrum`、`trial-llamalend-arbitrum`、`trial-silo1-liq-arbitrum`。dolomite と llamalend は `gate promote` が exit 2「intermediate wallet on arbitrum has less than 10.00 USD + gas」で止まりました。
- いまの中間 wallet（`gate status` 22:2xZ）: arbitrum ネイティブ 3.35 USD、USDC 0。**arbitrum が少なくとも 26.65 USD + 配備ガス 3 回分足りません**（1 本 10 USD + 配備ガス）。
- もう一つの制約: `gate status` で数えると `trial-` の live は **45 / 45 で満杯**です。入金しても、枠が空くか枠を広げるまで 3 本は promote できません。並びはそのままにしてあります（review.md に保存済み）。
- 参考: elysium の中間 wallet も 4.89 USD と少なめです（今のところ待っている bot はありません）。

## 2. 15i は反映しました

- scout.md: scout の枠は 1.2M CU/日、public の次は Alchemy。7 日の件数（bsc の getLogs を含む）が出るのが当たり前で、「lane spent で未測定」とは書かない。
- builder.md: fork の回避策の行を消し、「11-20 から fork は Alchemy だけで日の上限なし。`public:` が出たら inbox/meta へ」に置き換え。feed は 1 チェーン 16 本まで。research 1.5M。試行の枠 30 → 45（判断 6）。
- paper-reviewer.md: 試行の枠 30 → 45。チェーンの残高が足りないときは inbox/meta に書き、meta が転送する。
- TOOLS.md: lane の数字（fork は上限なし、scout 1.2M、research 1.5M）。
- wiki: `pitfalls/fork-past-state-public-nodes.md`（fork については解決済み、research / scout のみに残る話として整理）、`infra/feed.md`（16 本）。
- prompt の大きさ: earner 55,924 / paper-reviewer 53,772 / builder 52,132 / scout 40,240（上限 56,000 以下）。

## 3. Alchemy の月の枠（判断 5）

`/health` `cycle`: 41.1M / 95.2M CU を使用、ペース 5.17M/日。**11-24 の終わりで約 62M の見込みで、11-24 より前には尽きません**。今日の内訳では live lane が 3.0M（全体の約 7 割、試行 45 本 + 4 本）。

## 4. trial-aave-base は止まりました（お金の損はなし）

live-operator（run 4c63fe7b, 17:00Z 頃）が `gate stop` して archive しました（掃き戻し済み、今日の損 0.01 USD）。原因: 日の CU 上限（75k）に達したあと外から再起動され、`main()` がループの try の外で RPC を読む（`reserves()`）ため、上限エラーで落ちて再起動を繰り返していました。同じ書き方が live の試行 8 本（trial-aave の arbitrum / avalanche / bsc / optimism / polygon、xlend-base、hyperlend-hyperevm、hypurrfi-hyperevm）にもあります。再起動がなければ問題は出ず、出ても失うのは 00:00 UTC までの監視時間だけなので、止めてはいません。builder.md と paper-reviewer.md に確認の行を足し、wiki `pitfalls/bot-startup-read-budget-crashloop.md`（live-operator のページに統合）を更新しました。

ご判断が要るのは 1 だけです（arbitrum への入金と、試行の枠の扱い）。
