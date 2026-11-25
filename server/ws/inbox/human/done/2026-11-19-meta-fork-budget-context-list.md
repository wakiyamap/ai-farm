# meta ee059752 (2026-11-19 16:xxZ): fork レーン予算切れ・セッション文脈の 2 点・bsc/avalanche の読み取り

## 1. fork レーンの予算を超えると、古いブロックの fork が一日中動かない(15h の説明と食い違い)

- 15h の回答には「fork レーンの古い状態の読み取りは、予算を使い切った後も Alchemy を使う」とありました。実際にはそうなっていません。
- relay `/health`: 09:43Z に `fork` 601,490 / 600,000 CU。そこから少なくとも 14:46Z(603k)まで、`fork reset arbitrum <数時間〜5日前のブロック>` がすべて `all providers failed: public: HTTP 403 Archive requests require a personal token` で失敗しました。報告したのは builder 7790a143、05728037、996fcff1、cb0420ed と reviewer b0031010 です(`inbox/meta/2026-11-19-fork-*`)。base でも `fork deploy` が 3 回に 1 回同じ 403 で失敗しました(再試行で成功)。同じ時刻、research レーンには約 37 万 CU が残っていました。
- 影響: fork で証明できない bot が 3 つあります。`trial-gmx-buyback-slow-arbitrum`(1 バッチ約 8 USD、3 セッション分の証明が失敗)、`trial-peapods-arb-arbitrum`、`trial-silo1-liq-arbitrum`。どれも証明の一部が 00:00Z 以降に持ち越しです。
- お願い(どれか一つ): (a) 予算超過後も古いブロックの読み取りを Alchemy に送る(15h の説明どおり)。(b) fork の予算が尽きたら research レーンの残りを使う。(c) fork の予算を引き上げる。あわせて、09:40Z より前に 60 万 CU を何が使ったのか、確認をお願いします。15h の指示どおり報告すると、fork レーンの CU/日は増えています(11-18 は 400k 枠、11-19 は 600k 枠を朝のうちに使い切りました)。
- こちらで対処したこと: wiki `pitfalls/fork-past-state-public-nodes.md` と builder.md に一行追加しました。内容は「数分前のブロックへの reset はまだ動くので、deploy とガードの revert は先に証明する。古いブロックでの成功は、翌 UTC 日にするか、code override 付きの archive `eth_call` で行う」です。

## 2. builder のセッション文脈(harness が生成。ワークスペースの外なので私は変更できません)

- "Trial bots live: 30 / 10": 上限の表示が古いままです(`2026-11-18-trial-slots-30.md` では 30)。
- "Paper bots waiting for a fix":
  - `trial-bim-harvest-base` は 11-18 21:43Z に修正を再提出済みで(attempts:2268, 2533)、reviewer の再審査待ちです。builder 2 セッションが誤って拾いました。提案: ディレクトリ内に `review.md` より新しいファイルがあれば、reviewer 側に「resubmitted」として表示する。
  - 見出しが `## ... — fix` だけの review(peapods 2 件)は一覧に出ず、5 時間放置されました。reviewer 側は、1 行目を必ず `**Decision: ...**` にするよう paper-reviewer.md で統一しました(現在 17 件中 4 件が不一致)。一覧の照合も、見出し内の `— fix` を拾うようにしていただければ二重に防げます。

## 3. 読み取り経路(参考、判断が必要なら)

- bsc(scout a25fa579): 公開ノードは `eth_getLogs` を 16 ブロックでも `limit exceeded` で返します。さらに過去ブロックの `eth_call` に、エラーを出さず **最新の状態**を返します。`alchemy_getAssetTransfers` は `Invalid category param` で 400 になり、relay が `categories` を落としている可能性があります。wiki に注意書きを追加しました。
- avalanche(scout e4343d3a): keyless の routescan `txlist` は約 8 日遅れていて、research provider の getLogs は 100 ブロックまでです。このため 7 日間の呼び出し数を安く数える手段がありません。scout から「avalanche に使える読み取り経路(live レーンの Alchemy で 10k ブロックなど)はあるか」という質問が来ています。当面は、head と 7 日前の状態の差で活動を判定するよう wiki に書きました。

## gate

live 34 本(trial 30)。本日の損失 0、capital 1026.02 USD。14 日間動きのない bot はありません(gearbox-v3 は 11-23 17:44Z に期限到来)。
