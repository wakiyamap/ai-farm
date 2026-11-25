# meta 報告（2026-11-17 21:45Z、run fa898bbe）: phase 15a/15b の反映、試行の枠、research レーンの予算切れ

## 1. 反映したこと（phase 15a / 15b、判断 2026-11-18-trial-slots-20 / park-approved-trials）

- `paper-reviewer.md`: 試行の live 枠を 20 本に変更。数え方は `gate status` の `trial-` で始まる live bot のみ（gearbox、morpho-nextblock、bold は数えない）。容量で wait にするときは数と id を review.md に書く。Capacity 節に「並ばせる（parked）」の手順を追加（`wait (parked: approved, waiting for a live trial slot)` + `paper stop`、12 枠に数えない、審査を通った古い順に promote、資金不足は並んだままでチェーンと不足額を inbox/meta、変更した bot は審査し直し）。
- `builder.md`: 試行の枠 20 本。parked の bot（trial-euler-base など）を `paper start` しない。
- `TOOLS.md`: explorer の行を「Etherscan、次に Blockscout、`explorer chains` で確認」に、paper runner の行に paper-reviewer の `stop` と builder を追加。
- wiki: `infra/explorer.md`（Blockscout、チェーン別の経路）、`pitfalls/executor-deploy-funding-lag.md`（15b の deploy 待ちと `deploy_executor_not_sent` = 部分 promote）。
- プロンプトの大きさ: earner 55,995（上限の目安 56,000 まであと 5 バイト）、paper-reviewer 52,315、builder 50,240、scout 38,116、他は変化なし。**earner は TOOLS.md に 1 行足すだけで超えます**。次の meta の回で earner.md を短くします（キャッシュは一度切れます）。

## 2. `explorer chains`（21:20Z）

- ok: ethereum、arbitrum、polygon、hyperevm（Etherscan 経由）、base、optimism（Blockscout 経由）。
- 経路なし: avalanche、bsc（Etherscan は plan 外、Blockscout は 404）、elysium（unsupported）。hyperevm は 12-01 に Etherscan が有料化し、Blockscout も 404 なので経路がなくなる見込みです。
- scout や builder が base / optimism のソースを explorer で読んだ例は**まだありません**。20:41Z の scout（run 06583cf3）は base で Sourcify とセレクタ抽出を使っていました。TOOLS.md の行が古いままだったためで、今回直しました。次の報告で数えます。

## 3. 試行の bot の状況（gate status 21:25Z）

- live の試行は 10 本（trial-aave-arbitrum, -aave-bsc, -aave-optimism, -aave4-base, -cv3-buy-base, -flux-bsc, -morpho-cbbtc-base, -morpho-eth-base, -morpho-whype-hyperevm, -revert-lend-arbitrum）。**10 本とも nonce 1（executor の deploy のみ）で、送信は 0 件**です。今日の損 0.62 USD、capital 1,038.38 USD。
- paper は 12 本（11 本が審査済みで枠待ち + trial-hyperlend-hyperevm）。枠が 20 本になったので次の reviewer の回で promote が進むはずです。
- **中間 wallet の bsc は 2.87 USD、avalanche は 0** です。bsc の試行の promote は資金不足で断られます。ほかは base 92.67、optimism 59.67、polygon 60.37、hyperevm 67.80、arbitrum 60.78 USD。
- 前回の指標「OP Stack の先頭ブロック型の試行の新規配置」: 0 本（目標どおり）。

## 4. Alchemy の課金サイクル（判断 2026-11-18-trial-slots-20 の 5）

meta からはダッシュボードの「on course for」が見えません（relay の `/health` は今日の消費だけで、"don't ask" のセッションでは curl も使えません）。85% の見張りを meta にさせる場合は、その数字を workspace のファイルか relay の `/health` に出していただけますか。それまでは人間の側で確認をお願いします。

## 5. 提案: research レーンの予算が毎日夕方に尽きる

- 11-17 は research レーンが 18:45Z ごろ 1,000,000 CU を超え（builder 70dc57b1、scout 06583cf3 の `/health` 読み: 20:30Z に 1,012,452）、以後 00:00Z まで fork を含む research の読みがすべて公開ノードに落ちました。今日の scout は 256 セッションです。
- 影響: 過去ブロックの fork 証明ができない・状態が混ざる（arbitrum 403、hyperevm で panic）、hyperevm の getLogs が対照も含めて黙って `[]` を返す、base は 10 アドレス / 50,000 ブロック上限、avalanche は 100 ブロック上限。builder 3 回と reviewer 1 回が作業を止めたり迂回したりしました。
- meta で済ませたこと: wiki `pitfalls/research-lane-spent-public-fallback.md`、scout.md に 1 文（`public:` のエラーか空の対照なら `unclear`、ゼロとして数えない）。18:45Z 以降の attempts 43 件で `unclear` は 0 件、11 件が public ノードに触れていました（次回この比率を測ります）。
- 人間に決めていただきたいこと（どれか一つ）: (a) fork 用に research とは別の Alchemy 予算を確保する、(b) scout の 1 セッションあたりの読みの上限か、scout の回数を減らす、(c) research レーンの予算を増やす。meta の推奨は (a) です。証明ができない日は builder と reviewer の両方が止まるためです。
- fork の道具（workspace の外）について builder から 2 件: `fork reset <chain> <過去ブロック>` が公開ノードに落ちているときに警告する、`fork deploy` に `--gas`（hyperevm で既定値がブロックのガス上限を超え、毎回手で creation tx を送っている）。

## 6. 転送: builder からの判断依頼

1. **Pyth Hermes のキー**（lead 250、arbitrum flat_money_v2 の executeOrder）: `hermes.pyth.network` がこのホストから HTTP 401。この lead だけなら全体で約 0.89 USD/日なので無料枠のキーで足りる程度です。ただしキーがないと Pyth の pull 型オラクルの keeper 系はすべて閉じたままです。
2. **Superfluid TOGA の PIC 席**（base、lead 248、wiki `mechanisms/superfluid-toga-pic.md`）: 120-400 USD の保証金（USDCx）を入れ、戻りは 7 日以上のストリームか、他者に上書きされた時の一括返還。過去 28 日の報酬は合計 113.69 USDCx（全部取れても最大 4.06 USD/日、競合 1 者、取れる割合は不明）。L とホールディング枠（一度で売れる、100 USD 以下）の外で、watchdog は保証金を損と見ます。**meta の推奨は「例外を作らない」**です。上限 4 USD/日に対して、規則と watchdog の両方に例外が必要なためです。
3. 参考: trial-hyperlend-hyperevm（paper）は、1 USD/tx の試行の上限では払えない混雑時のケースを `gross_not_above_gas_cap` として記録します。合計が大きければ、上限 20-50 USD の版（L の内側、試行の条件の外）を人間に伺う予定です。
