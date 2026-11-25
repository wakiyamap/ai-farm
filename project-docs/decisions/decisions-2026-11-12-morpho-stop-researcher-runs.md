# morpho の停止、速度勝負の扱い、researcher の回数（人間、2026-11-12）

11-12 04:21 JST のブリーフ、reviewer の morpho-watcher2-ethereum の審査、meta の提案（inbox/human の session-mix）を読んで決めました。

## 1. morpho-watcher-ethereum は人間が止めた

2026-11-12 に `gate stop` で停止し、資金は中間ウォレットに戻しました。理由は 2 つです。

- executor が利益の USDC を自分に残し、bot の wallet に返さない（reviewer が morpho-watcher2 で指摘。executor は live のものと同一）。decision 2026-11-11-executor-bots-funds に合っていません
- 分類の結果、対象市場の 7 日 17 件のうちポーリングで取れたのは 1 件で、それも約 5 秒の差で逃しています。残りは価格更新と同じブロックの競争か、下限未満です

## 2. 速度勝負のクラスは、いまはやらない

まだ 1 件も稼げていない段階で、他の searcher より速いことが前提の機会を追いません。

- 「価格更新と同じブロックで取られる」「取れる状態になってから数秒〜1、2 ブロックで取られる」機会は対象外にします
- 新しい bot の README には、過去の事例ごとに **取れる状態になってから実際に取られるまでのブロック数（と秒数）** を書いてください。中央値と最小値も書く
- その時間が bot のポーリング間隔 + 送信から取り込みまでの時間より短い事例は、期待収益に数えないでください。数えていたら reviewer は fix にしてください
- morpho-watcher2-ethereum は、この条件で数え直して期待収益が残る場合だけ続けてください。残らないなら earner が閉じてください

速度勝負を再開するかどうかは、別のクラスで実際に利益が出てから人間が決めます。

## 3. Metronome sES 市場は別 ID で進めてよい

decision 2026-11-12-live-bots-zero-sends の「市場の追加は分類の結果が出てから」は、分類が出たので解除します。条件:

- 別の ID で paper に出す
- 過去に実際に起きた清算を、そのブロックの 1 つ前の状態の fork で bot 自身に取らせ、**bot の wallet の残高が増える**ことを示す（成功の tx と、利益なしで revert する tx の両方）。2 段の換金の換金率を README に数字で書く
- executor は利益を同じ tx の中で bot の wallet に返す
- 2 の「取られるまでの時間」を 10 件すべてについて書く
- 「1 日約 36 USD」は fork での実証が出るまで仮の数字として扱う。同じ日に moonwell で liquidity の語を shortfall と読み違えた例があったので、清算可能かどうかの判定は 2 通りの方法（コントラクトの view と、担保・債務からの自前計算）で突き合わせる

## 4. researcher は 1 日 4 回にする

未測定の lead が 0 件なので、researcher-codex と researcher-claude をそれぞれ 1 日 2 回にします（04:10 と 22:10 JST が codex、10:10 と 16:10 JST が claude）。timer は人間が変更します。earner の回数は変えません（ローカルのモデルで費用がかからないため、減らす理由がありません）。

## 5. live-operator の定期起動はしない

live-operator は今までどおり watchdog が起こしたときだけ動きます。定期起動は、運用を完全に自動化する段階で考えます。

そのため inbox/live は普段は誰も読みません。**急ぎでない報告や判断の依頼は inbox/live ではなく inbox/meta に書いてください**。meta は人間の判断が要るものを inbox/human に回してください。

## 6. Alchemy の費用の数え方

- live レーンの「日次 1.5M CU」は名目の数字で、超えても絞られません。効くのは月間の上限 95.2M CU（月 50 USD）です。11-12 時点の累計は 17.84M です
- 目安は **100 万 CU ≒ 0.53 USD**。bot の README には 1 日の CU の見込みと、その金額を書いてください。期待収益（2 の条件で数えたもの）がこの金額を下回る bot は promote しないでください
- 月 50 USD を超えて稼げる見込みが立てば、人間が上限を上げます。提案は inbox/human にどうぞ

## meta へ

2〜6 を earner.md、paper-reviewer.md、researcher.md、common.md の該当箇所に反映してください。プロンプトの大きさ（56,000 バイト以下）は守ってください。
