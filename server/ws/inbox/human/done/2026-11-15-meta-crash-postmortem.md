# crash-postmortem: 11-11〜11-14 の急落で、farm に取れる清算はなかった（meta、2026-11-15）

decision 2026-11-15-widen-beyond-liquidations の残り項目（phase 12a 依頼 1）です。出典はすべて wiki `infra/crash-2026-11-14.md`（attempts 1185〜1240）。

## 結論

**急落時でも今の farm に取れる清算はなかった。** 「数えてよい（counted）」かつガス差し引き後 1 USD 超の取り方は 72 時間で 12 件見つかりましたが、3 系統とも作れないと分かり、すべて閉じました。新しい清算の lead は残っていません。

## 数字（窓 A: 11-11 07:00〜11-14 07:00 UTC、比較 B: その前の 72 時間）

- 窓 A: 4,440 件、返済 7,480 万 USD、名目の粗利（返済額 × ボーナス、ガス・スワップ前）362 万 USD。B は 3,405 件／3,970 万／222 万（粗利で 1.6 倍）
- 1 日の件数の最大は 11-13 の 2,268 件、直前 5 日平均の 2.35 倍（自動で始める線の 3 倍には届かず）
- **粗利の 67% 以上は Atlas の OEV オークション経由（型 O、真似できない）**、28% は価格更新の直後に同じブロックで取る型（B か O）。許可制・遅い掃除・時刻が読める型（P/S/T）は 5% 以下で、誰でも取れて証拠のあるものは 0
- 時間を測った行（16 系統）は、ほぼすべてが「取り込みブロックの中で清算可能になった」= 窓 0 秒の競争

## 「数えてよい」12 件の行方

| 系統 | 件数・正味 | 結果 |
|---|---|---|
| Base Morpho（遅い掃除の 2 アドレス） | 6 件、593 USD（うち 594 USD は 1 本の 15 件まとめ tx） | lead 170 blocked_infra: 取れる部分は 0.2 秒ブロック 1 つ分の競争と判明 |
| Base Moonwell core | 1 件、23.90 USD | lead 171 blocked_infra: 期待値 0.33 USD/日で下限未満 |
| Base Exactly | 5 件、685 USD | lead 172 dead_end: 清算の入口が liquidator の許可リストで閉じている |
| HyperEVM Morpho（当初 2 件 3,112 USD と報告） | 0 | lead 173 dead_end: auctioneer 専用の入口。keeper の実受取はガス後マイナス（−0.14 USD）。当初の数字は取り下げ |

## 取り残し（10 分以上だれも取らない清算可能ポジション）

- ほぼすべてが端数（負債 1 USD 以下）か、担保に出口がないもの（USR/RLP 市場: オラクル 1.0001 に対し実際に売れる値 0.034）
- farm 規模で正味プラスの残りは 2 件: Base wbCOIN（名目利益 57 USD、一回限り）と ethereum ynETHx（lead 174、粗利 880 USD、accrueInterest が revert する市場）。lead 174 は担保の出口の測定後 blocked_infra
- 一回限りの規則（正味 10 USD 以上でその場で paper bot）で作られた bot は 0

## 次の急落で

この作業は decision で閉じたので、自動の再実施はしません（wiki `methods/crash-postmortem.md` に「閉じた」と明記済み）。各 dead_end の lead に、どの条件なら測り直すかが書いてあります（例: lead 169 / 175 / 178 は負債 100〜250 USD 超の取り残しが出たときだけ）。

## ほかの依頼への返事（phase 12c 依頼 4、12d 依頼 4）

**`private-send` の印がある lead**（ethereum のものだけ再開できます）:
- ethereum: 5（compound v3 清算）、35（LlamaLend 清算）、179（Convex vlCVX の期限切れロック kick 報酬、dead_end）
- それ以外（再開不可）: base 1, 2, 6, 171、arbitrum 7, 15

5 と 35 は清算で、lead 14 の実測（取り手が粗利のほぼ全額をビルダーに払う）から、非公開の送信でも取れる見込みは薄いと見ています。179 は清算ではないので、earner が非公開の送信で測り直す候補です。

**「持つ型」の lead**:

| lead | chain | 元手 | 持つ時間 | 枠に合うか |
|---|---|---|---|---|
| 184 Elysium USDC/WHYPE プールの割安買い・戻り売り | elysium | holding_usd 20 から（測定は 100 USD で約 11.6 USD/日） | 中央値 29 分、上限 24 時間で設計 | 合う（同じチェーン、プールで即時に売れる）。paper bot `whype-gap-elysium` が稼働中 |
| 187 Kinetiq KHYPE の NAV 割れ | hyperevm | 未測定 | 未測定 | プールで USDC に売り戻すなら合う。unstake の償還を待つ形なら対象外。測定依頼の段階 |
| 181 Nest AVR の LP 手数料 | elysium | — | — | 対象外（利回り型、dead_end） |

## meta が今回したこと

- `tools/manifest-check.py` が `send_route`、`holding_usd`、`holding_max_hours`、executor の `exitAll()` を確かめるようになりました（gate の promote の拒否条件と同じ）
- wiki `methods/holding-frame.md`、`infra/private-send.md` を作り、earner.md の 2 つの項目をそこへ向けて短くしました（earner の組み立て後 54,952 → 54,596 バイト。TOOLS.md の gate 行への exit 3「持ち高が戻っていない」、kb-file 行、web 行の追記を含む）
- `tools/kb-file.py update` は、更新の前にその行の chain / protocol（または target, address）を表示し、ファイル中のキーと食い違えば更新を断るようになりました（11-15 の earner が別の id を上書きしかけた件）
- `wiki search` の BM25: hit@1 は入れ替え前 0.831（130 問）→ 0.878（131 問）→ 0.881（135 問、新しい 2 ページの 4 問を追加）。下がっていないので、旧ファイルに戻す必要はありません
