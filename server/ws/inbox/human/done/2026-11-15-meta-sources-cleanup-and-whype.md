# ledger sources.d の整理（途中）と whype-gap-elysium の件（meta run a35cc7b2、2026-11-15 12:2xZ）

decision `2026-11-15-whype-gap-review-points` への報告です。

## 3. sources.d の整理: 外す 4 件は決めたが、ファイルを消せなかった

条件（measured の lead、live / paper の README）を確かめた結果:

| source | 判定 | 根拠 |
|---|---|---|
| across.filled_relay | 外す | lead 168 は dead_end。取り込みも 11-09 05:27Z から止まっている（17,651 行） |
| uniswapx.fill | 外す | lead 166 は bsc / arbitrum / base とも dead_end（attempts 1106, 1251） |
| debridge_dln.claimed_unlock | 外す | attempts 1252 で dead_end |
| horizon_rwa.liquidation | 外す | 取り込みは 0 件、lead 58 は dead_end |
| gearbox_v3.liquidate_credit_account | **外さない** | live の gearbox-v3-watcher-ethereum の manifest が根拠にしており、lead 48 が measured |

- 4 件の定義は `tools/ledger-sources-retired/` に写しました（説明は同じ場所の README.md）。dead_end の lead 58 / 166 / 168 の next_steps にも、source を外すことと、再開の確かめ方（直接スキャンか再インストール）を書きました。
- **ただし、meta のこの回は `ledger/sources.d` の中のファイルを消す・移すことが権限で断られました**（rm / mv とも拒否）。4 件の元ファイルはまだ有効で、sources.d は 40 / 40 のままです。researcher の `bond_protocol.bonded` もまだ入れられていません。
- お願い: 次のどちらかをお願いします。(a) 人間が 4 つのファイル（`across.filled_relay.json`、`uniswapx.fill.json`、`debridge_dln.claimed_unlock.json`、`horizon_rwa.liquidation.json`）を sources.d から消す。写しは保存済みです。(b) meta のセッションで sources.d 内のファイル削除を許可する（または `ledger retire-source <id>` のような道具を作る）。消えたら、次の meta が bond_protocol を入れて wiki を直します。
- 補足: bond_protocol を求めていた lead 183（Olympus の買い戻し）は、その後 attempts 1274 で dead_end になりました（プールの手数料 0.3% で中央値の 1 回が −0.09 USD）。入れる価値は下がっていますが、決定どおり空いたら入れます。不要なら言ってください。
- gearbox の代わりの 5 件目は今は不要です（1 枠あけば足ります）。今後の候補は `pendle_v2.create_yield_contract`（7 日で数件、関連の lead なし）ですが、外す前に条件を確かめます。

## 2. whype-gap-elysium: 審査の前に終わりました

- 審査の 4 点を役割ファイルに渡す前に、earner（run 86c4cf54、attempts 1293）が保存済みの系列を計算し直し、gas の前で **−5.86 USD / 100 USD（12 往復）** と出しました。同じプールで買って売る形では、枠の条件「売値 ≥ 原価」を満たす入口が構造上ありえない（買った直後の見積もりが原価の 99.78%）ことも示し、lead 184 は dead_end です。
- paper-reviewer（run 080cc76e）がこの bot を demote しアーカイブしました。そのため 2 の 4 点を earner / reviewer に渡す必要はなくなりました。
- **elysium の中間ウォレットに入金された資金（HYPE 約 5.01 USD、USDC 199.96）は今は使い道がありません。** X には数えられています（gate status: 合計 882.64 / 2000）。戻すか、次の elysium の候補まで置くかは人間が決めてください。

## その他

- gate: live 3 本、今日の損失 0、frozen なし。持ち高の枠は 0 / 200。3 本とも promote から 14 日たっていないので、14 日の休眠チェックは 11-23 から。
- morpho-nextblock-ethereum の bot ウォレットは ETH 約 7.81 USD まで減っています（他の 2 本は 80 USD 台）。live-operator の判断事項ですが、念のため。
