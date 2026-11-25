# meta 報告（2026-11-17 09:0x UTC、run 94d68923）: HAI の順序の比較、試行 bot の成績、確認事項

## 1. 署名ライブラリの読み込み修正の確認（ご依頼 2026-11-17-human-live-signer-path.md）

05:39 UTC の `gate restart` 以降、パッチを当てた 5 本のどの live ログにも `No module named 'farmbot_signer'` は出ていません。

| bot | 再起動 | 再起動後のエラー | 再起動前 |
|---|---|---|---|
| trial-aave-arbitrum | 05:39 | 0 | 43 回 |
| trial-aave4-base | 05:39 | 0 | — |
| trial-cv3-buy-base | 05:39 | 0 | — |
| trial-morpho-cbbtc-base | 05:39 | 0 | — |
| trial-revert-lend-arbitrum | 05:39 | 0 | — |

trial-morpho-eth-base（06:06 promote）と trial-morpho-whype-hyperevm（04:29 promote）は、promote 前に修正済みのコードで、エラーは 0 です。paper の 5 本（cv3-buy-arbitrum / -optimism / -polygon、feusd-redeem-hyperevm、morpho-khype-hyperevm）は manifest-check で全部 OK です。

## 2. HAI（optimism）: 手数料の順で並んでいない → 3 本の停止をおすすめします

ご依頼のとおり、負けたブロックの中での tx の位置を比べました（builder ではなく meta が live ログから集計。receipt と window_result をブロック番号でつないだもの。attempts:1658）。

- 3 本合わせて **100 回送って 0 勝**。ブロックに入った tx はすべて revert（status 0）。
- 同じブロックで負けた 56 回（oraclejob 43、oraclebatch 13）では、**勝った相手は毎回 index 1**（L1 情報の deposit tx のすぐ次）、こちらは index 5〜70（中央値 16 と 23）。
- oraclejob の 43 回のうち 11 回は、**こちらの優先手数料（0.03 gwei）が相手と同じか高かった**（相手は最低 0.0076 gwei）のに、それでも後ろに並びました。
- こちらの送信はすべて、ブロックのタイムスタンプの 2.4 秒前に出ています。相手の tx は、そのブロックを作り始める時点でもう sequencer の pool にあり、こちらのは作っている最中に届いた、と読めます。
- **したがって入札を上げても index 1 より前には出られません。** 前に出るには、due のブロックを作り始める前に pool に入れておく必要があります（1 ブロック早く入ると revert する tx を先に出す、という時間の勝負です）。ご指示の条件「手数料の順でなければ止める」に当てはまるので、**trial-oraclejob-hai-optimism、trial-oraclebatch-hai-optimism、trial-updaterate-hai-optimism の `gate stop`** をおすすめします。updaterate は 9 回のうち 5 回が 1 ブロック遅れで、同じ結論です。
- 費用: receipt の手数料の合計は 0.000225 ETH（約 0.7 USD）。wallet 残高は oraclejob 17.33/20、oraclebatch 2.92/3、updaterate 4.97/5 USD（oraclejob の 2.67 USD の差は receipt の手数料より大きく、L1 データ費と ETH 価格の変化と思われますが、まだ突き合わせていません）。
- 学んだことは wiki `methods/timer-first-block-send.md` に書きました（OP Stack で手数料を上げる前に、勝者とこちらの index の差を測ること）。

## 3. 試行 bot の成績（live 10 本、09:00 UTC 時点）

| bot | live になった時刻 | 送信 | 勝ち | 主な負け方 / 状態 |
|---|---|---|---|---|
| trial-oraclejob-hai-optimism | 11-16 22:06 | 71 | 0 | 同じブロックで index 1 に負け（上の 2） |
| trial-oraclebatch-hai-optimism | 11-17 01:18 | 15 | 0 | 同上。こちらの手数料はいつも相手より低い |
| trial-updaterate-hai-optimism | 11-16 18:54 | 14 | 0 | 同じブロック 4 回、1 ブロック遅れ 5 回 |
| trial-aave-arbitrum | 11-16 20:49 | 0 | 0 | 05:39 まで署名できず。その後、清算できる案件なし |
| trial-aave4-base | 11-17 02:53 | 0 | 0 | 案件なし |
| trial-cv3-buy-base | 11-17 01:16 | 0 | 0 | absorb なし |
| trial-morpho-cbbtc-base | 11-17 02:52 | 0 | 0 | 案件なし |
| trial-morpho-eth-base | 11-17 06:06 | 0 | 0 | 案件なし |
| trial-morpho-whype-hyperevm | 11-17 04:29 | 0 | 0 | 5 回 simulate で revert（`position is healthy`、ratio 0.99999）: 送らずに済んでいる |
| trial-revert-lend-arbitrum | 11-16 23:44 | 0 | 0 | 案件なし |

合計: 送信 100、勝ち 0、差し引きは手数料分（約 −0.7 USD、残高ベースでは約 −2.8 USD）。gate の本日の損 0、capital 966.41 USD。

## 4. 試行の枠（10 本）と、待っている bot

paper で審査を通って枠待ちのものが 5 本あります: trial-cv3-buy-arbitrum、trial-morpho-khype-hyperevm、trial-feusd-redeem-hyperevm、trial-cv3-buy-optimism、trial-cv3-buy-polygon。HAI の 3 本を止めると 3 枠空きます。builder は、過去 7 日の粗利で順番を決めることを提案しています（optimism cv3 約 165 USD、arbitrum cv3 約 12 USD）。hyperevm（68.71 USD）と polygon（29.79 USD）の中間 wallet は、資金の依頼のあとに入金されたことを gate status で確認しました。

## 5. ご確認ください（gate の設定は workspace から見えません）

1. **polygon で gate が数える USDC はどちらですか**: USDC.e `0x2791bca1...` か native USDC `0x3c499c54...`。Compound v3 の comet が払うのは USDC.e です。違う方なら、利益が X と sweep から見えず、失われたことになります。
2. **optimism の USDC** は native `0x0b2c639c533813f4aa9d7837caf62653d097ff85` で合っていますか（trial-cv3-buy-optimism はこれで利益を返します）。
3. `fork deploy` に gas の指定がなく、hyperevm では `tx.gas_limit > env.block.gas_limit` で失敗します（builder は `fork send` で回避）。`--gas` を付けていただけると助かります（fork のツールは workspace の外です）。

## 6. 手順のずれ（直しました）

live の試行 10 本のうち 6 本は、`review.md` の一番上に promote の記録がありません（gate がディレクトリを移したあとに書こうとしたもの）。paper-reviewer.md の promote の行そのものに「先に review.md に書いてから `gate promote`」と書き、資金不足の連絡先を `inbox/human/` から `inbox/meta/` に直しました（reviewer には inbox/human への書き込み権がありません）。

## 7. 14 日間送信なしの確認

gearbox-v3-watcher-ethereum は 11-09 に live、nonce 1（executor のデプロイのみ、送信なし）。11-23 に 14 日になります。次の meta がそこで停止のおすすめを出します。bold-redeem-tail と morpho-nextblock はまだ 14 日未満です。
