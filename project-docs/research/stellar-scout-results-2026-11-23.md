# Stellar の scout の結果（2026-11-23 15:03 JST、24 件すべて done）

phase 16a・16b の読み取りで、scout（Qwen）が Stellar の候補 24 件（人の 2 件 + DefiLlama の 22 件）を調べた結果。scout/done の `result.verdict` と `result.line` から。

## 集計（計 24）

- **pays_strangers: 0 件**
- no_reward 13（blend-pools v1・v2、blnt-v3、huma、phoenix-defi-hub、soroswap-amm、spectra-v2、stellar-amm、stellar-dex、untangled-rwa、upshift、vaquita、xoxno-lending）
- unpaid 5（aquarius、defindex、gami-labs、near-intents、stellar-defi-hub）
- role_gated 1（defa-by-invoicemate）
- not_found 3（scopuly、templar-lending、bim）
- unclear 2（sushi-stellar、blend-interest-auction）

## 目を引いた点

- **Blend の interest auction: 7 日で 0 件**（両 V2 backstop、作成も fill もなし）。仕組みは source で確認: lot は backstop の取り分が 200 USD 以上たまってから、入札は BLND:USDC の Comet LP を 1.2 倍、オランダ式 0.5%/block。たまるのが遅く、今は誰も取っていない。払われた証拠がないので試行の条件（過去 7 日に払われた tx）を満たさない
- **BIM は Stellar にない**（DefiLlama の Stellar TVL は 0、EVM だけ）。下調べの「BIM 37.5M」は誤り（DefiLlama のページの表の読み違い）
- **DEX は動いている**: Phoenix は 7 日で swap 601 件、送り手 11（CA4ICH… が 310、CD5D72… が 138 = 裁定の bot とみられる）。Aquarius は router のイベントが 7 日で約 2.56 万件と推定。Soroswap の router も user の swap が続いている。ただし「呼んだ人に払う関数」はどこにもない。取れるとすれば DEX 間の裁定だけで、既に専用の bot がいる
- defa-by-invoicemate は 1 つの coordinator が 1 日約 58 件の清算を回す（role_gated）
- stellar-defi-hub の報酬（7 日で 101 USD）は預け主だけが受け取る

## 結論（Claude の見立て）

- keeper の報酬・誰でも呼べて払われる型は、Stellar の DeFi（TVL 上位 22）には今のところ無い
- 残る可能性は DEX 間の裁定（Blend V2 の flash loan を使う形）だけ。出来高が小さく（1 日約 290 万 USD）、既に専用の bot がいて、署名・executor・証明の仕組みを丸ごと作る必要がある。**次の段（署名など）に進む根拠はない**
- 読み取りのレーン（16a・16b）は使わなければ費用がかからないので残してよい。scout-enum は新しい Stellar のプロトコルが TVL 2.5 万 USD 以上で載れば自動で候補にする
- Blend の interest auction は、backstop の取り分がたまれば出てくる可能性がある。月に 1 回、同じ候補を数え直す程度でよい
