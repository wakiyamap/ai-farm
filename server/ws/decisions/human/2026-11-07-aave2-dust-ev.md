# 2026-11-07 aave2-dust-ethereum の採算（人間 → earner / paper-reviewer）

## 見立て

aave2-dust-ethereum の fix 往復を続ける前に、採算の数字が前日の自分たちの判断と食い違っている点を確認してほしい。

- cv2-dust-ethereum（attempts:308）は「1 件あたりの gas 約 0.15 USD に対し、gross 0.012〜0.034 USD」で dead_end にした。
- aave2-dust の数字（leads 29 / attempts 302）は、dust の gross が中央値 0.025 USD/件、gas は batch 32 件 × 359k gas で 1 gwei のとき約 31 USD、つまり約 1 USD/件。実測の gas 下限 0.2 gwei でも約 0.2 USD/件になる。cv2-dust と同じく、dust だけでは gas を回収できない計算に見える。
- 1 日 53 USD という gross の大半は、少数の大口（最大 3853 USD）から来ているはず。ところが lead 29 の fork 計測では、renBTC の大口は capture ブロックの直前に清算可能になっている（同一ブロック競争）。それなら 2026-11-06 の判断（no-latency-race）により対象外になる。
- 加えて、利益は stETH で受け取るのに、同じ tx 内で売る場所が今は無い（attempts 313）。USDC 建ての損益が確定しない。

## 指示

1. **earner**: 次の fix の前に、過去 12.9 日の 346 件を使って次の計算を leads 29 に書くこと。
   - poll で取れる件（清算可能になってから capture まで ≥ 数十ブロック）だけを残す。
   - それを実際に組める batch に分け、batch ごとの gross（USD）から実測 gas（その日の basefee）を引く。
   - 合計が明確にプラスなら fix を続ける。プラスにならなければ cv2-dust と同じく dead_end にして paper bot を止める（`paper stop`）。
2. **paper-reviewer**: aave2-dust の次の審査では、上の正味の採算計算を必須の証拠として扱う。無ければ、ほかの項目を見る前に fix とし、理由に「正味 EV の計算なし」と書く。stETH で受け取る利益を USD に換算する場合は、その換算方法（同じ tx 内での売却か、後から売るときの価格とスリッページ）も確認すること。
3. dust を集めるクラスについて、gas と gross の比較はクラスを選ぶ段階（lead の時点）で行い、bot を作る前に止めること。これは今後の lead 全般に当てはまる。
