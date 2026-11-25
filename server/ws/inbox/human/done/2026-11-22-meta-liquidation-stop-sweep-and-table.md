# 清算型 33 本の停止: sweep の確認と送信の表（meta, 2026-11-22 04:3xZ, run bad6e546）

`inbox/meta/2026-11-22-human-stop-liquidation-bots.md` への回答です。

## 1. sweep（お願い 1）: 未完の bot はありません

- gate.log は meta の権限では読めないので、チェーン上で確かめました。33 本すべてのウォレットで、残っているネイティブはチェーンごとの dust だけです（polygon 0.025 POL 以下、avalanche 0.00063 AVAX 以下、ほかは 0.00001 ETH/BNB/HYPE 以下で、どれも 0.02 USD 未満）
- 停止前に USDC を持っていた 2 本（trial-aave2-avalanche 0.79、trial-kinza-bsc 0.08）の分は、中間ウォレット側の avalanche:usdc 0.79 と bsc:usdc 0.08 に戻っています
- `gate status` の capital_usd 1409.32 は、中間ウォレット 882.00 と live 50 本の残高 527.35 の合計 1409.35 と一致します。sweep が終わっていない bot の分は X に入っていません
- 終了コード 3 で止まった bot はない、と判断しています

## 2. 止めた 33 本の成績（お願い 5、11-24 の判断材料）

送信数は bot ウォレットの nonce から executor の deploy と sweep を除いた数です（arbitrum と optimism は explorer の tx 一覧で数えました）。勝ち・負けと粗利は bot 自身のログの `send_result` から取っています。差し引きは、gate が入れた額に対して、sweep で戻った額と残った dust を足したものです。チェーン上の送金から計算し、ネイティブは今の価格で USD にしています。

| bot | chain | 送信数 | 勝ち | 負け | 勝ちの粗利 USD | 差し引き USD |
|---|---|---|---|---|---|---|
| trial-aave-arbitrum | arbitrum | 0 | 0 | 0 | 0 | -0.03 |
| trial-aave-avalanche | avalanche | 0 | 0 | 0 | 0 | -0.04 |
| trial-aave-bsc | bsc | 0 | 0 | 0 | 0 | -0.03 |
| trial-aave-optimism | optimism | 1 | 0 | 0 | 0 | -0.00 |
| trial-aave-polygon | polygon | 1 | 0 | 1 | 0 | -0.31 |
| trial-aave2-avalanche | avalanche | 3 | 1 | 1 | 0.79 | +0.02 |
| trial-aave2-polygon | polygon | 4 | 0 | 4 | 0 | -0.81 |
| trial-aave4-avalanche | avalanche | 2 | 0 | 2 | 0 | -0.98 |
| trial-aave4-base | base | 4 | 0 | 4 | 0 | -0.15 |
| trial-benqi-avalanche | avalanche | 0 | 0 | 0 | 0 | -0.06 |
| trial-dolomite-arbitrum | arbitrum | 0 | 0 | 0 | 0 | -0.03 |
| trial-euler-base | base | 0 | 0 | 0 | 0 | -0.01 |
| trial-euler-bsc | bsc | 0 | 0 | 0 | 0 | -0.04 |
| trial-exactly-optimism | optimism | 3 | 0 | 2 | 0 | -0.07 |
| trial-felix-liq-hyperevm | hyperevm | 0 | 0 | 0 | 0 | -0.00 |
| trial-fluid-arbitrum | arbitrum | 0 | 0 | 0 | 0 | -0.04 |
| trial-fluid-polygon | polygon | 1 | 0 | 1 | 0 | -0.15 |
| trial-flux-bsc | bsc | 0 | 0 | 0 | 0 | -0.03 |
| trial-hyperlend-hyperevm | hyperevm | 0 | 0 | 0 | 0 | -0.01 |
| trial-hypurrfi-hyperevm | hyperevm | 0 | 0 | 0 | 0 | -0.01 |
| trial-kinza-bsc | bsc | 7 | 1 | 5 | 0.08 | -0.14 |
| trial-llamalend-arbitrum | arbitrum | 0 | 0 | 0 | 0 | -0.05 |
| trial-moonwell-base | base | 0 | 0 | 0 | 0 | -0.01 |
| trial-morpho-arbitrum | arbitrum | 1 | 0 | 1 | 0 | -0.06 |
| trial-morpho-cbbtc-base | base | 1 | 0 | 1 | 0 | -0.02 |
| trial-morpho-khype-hyperevm | hyperevm | 0 | 0 | 0 | 0 | -0.01 |
| trial-morpho-whype-hyperevm | hyperevm | 0 | 0 | 0 | 0 | -0.01 |
| trial-revert-lend-arbitrum | arbitrum | 0 | 0 | 0 | 0 | -0.04 |
| trial-silo1-liq-arbitrum | arbitrum | 0 | 0 | 0 | 0 | -0.05 |
| trial-venus-bsc | bsc | 0 | 0 | 0 | 0 | -0.03 |
| trial-peapods-base | base | 0 | 0 | 0 | 0 | -0.01 |
| gearbox-v3-watcher-ethereum | ethereum | 0 | 0 | 0 | 0 | -3.28 |
| morpho-nextblock-ethereum | ethereum | 1 | 0 | 0 | 0 | -6.78 |
| **計** | | **29** | **2** | **22** | **0.87** | **-13.28** |

読み方:
- 33 本のうち 20 本は一度も送信していません。損失はほぼ deploy と sweep のガスだけです
- 勝ちは 2 回で、粗利は合計 0.87 USD です。負けの 22 回のうち 21 回は、相手が同じブロックか 1-4 ブロック前に取っていました（ログの `blocks_after_winner` は 0 が 2 回、1 が 10 回、2 が 2 回、3 が 6 回、4 が 1 回）。残る 1 回は 273 ブロック遅れでした
- 損失の 3/4 は ethereum の 2 本（deploy と pool init のガス）です。清算以外の試行と比べるときは、L2 の 31 本を合計した約 -3.2 USD を使ってください
- 送信数と勝ち負けの数が合わない bot が 4 本あります（aave-optimism、aave2-avalanche、exactly-optimism、kinza-bsc）。approve のような送信か、ログを書く前に止まった送信です。gearbox と morpho-nextblock は `send_result` を書かない古い形式の bot です
- 再計算用のスクリプトは `scratch/meta-bad6-table.py`、元データは `scratch/meta-bad6-net.json` です

## 3. ほかのお願いについて

- お願い 2: 33 本は `bots/archive/` のままです。paper に戻ったものはありません。paper-reviewer.md に「止めた 33 本は再審査も再 promote もしない」と書き足しました
- お願い 3: promote できるのは paper-reviewer だけで、meta にはできません。trial-kdiem-redeem-base はすでに live です。trial-swave-arb-polygon は 11-21 21:52Z の審査で `fix` でした（利益が USDC.e で払われ、gate の USDC として数えられない）。builder が直して出し直すまで promote はできません。今の試行の枠は 75 のうち 48 が使われています
- お願い 4: paper-reviewer.md の「live ones stay to 11-24」を「only live ones in profit since promote stay to 11-24 (the human stopped the other 33 on 11-22 …)」に直しました。builder.md には「live の清算型は 11-24 まで置く」という文がもともとなかったので、変えていません。prompt の大きさは paper-reviewer で 54445 bytes です（上限の目安 56000 以内）
