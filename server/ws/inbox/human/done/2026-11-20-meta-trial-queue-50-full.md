# 試行の bot の枠 50/50 が埋まり、審査済みの 3 本が待っています（meta 2026-11-20 04:10 UTC）

判断が必要なのは 1 だけです。2 と 3 はお知らせです。

1. **枠**: `gate status`（04:00 UTC）で live の `trial-` は 50 本で、`2026-11-20-trial-slots-50.md` の上限に届いています。技術の審査を通って枠を待っているのは次の 3 本です（審査を通った順）。
   - trial-aave4-optimism（清算、Aave v4 spoke）
   - trial-aave4-avalanche（清算、Aave v4 spoke）
   - trial-folio-nav-base（清算以外、Reserve Folio の NAV アービトラージ）
   11-24 までにこれらも試すなら、枠をもう 3 本増やすか、何も送っていない live の試行を止めて入れ替えるかのどちらかが要ります。50 本のうち 42 本は nonce が 1 で、executor の配備のほかには一度も送信していません。決めていただくまで、reviewer はいまのまま待ちます。
2. **入金**: paper-reviewer が 00:19 UTC に「optimism と avalanche の残高が足りない」と inbox/meta に書きましたが、04:00 UTC には optimism 34.15 USD、avalanche 19.02 USD あり、2 本とも capital と配備のガスに足ります。追加の入金は要りません。
3. **Alchemy の月の枠**: `/health` の `cycle` では 43.1M / 95.2M CU を使っています。最近のペースは 1 日 8.8〜9M CU（今日は 04:00 までに live 0.80M を含めて 1.49M）で、このままなら 11-25 ごろに尽きます。11-24 より前には尽きない見込みなので、判断 `2026-11-20-trial-slots-45.md` の 5 のとおり、対応は要りません。ただ、11-24 に試行を締めて live の読み取りが減らなければ、12-01 の期の終わりまでもちません。
