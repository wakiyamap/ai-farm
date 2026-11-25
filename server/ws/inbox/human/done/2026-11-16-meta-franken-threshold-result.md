# meta 6bc72caa（2026-11-16 09:0xZ）: franken の閾値入札 bot の結果、earner の状況

## 1. decision 2026-11-16-franken-threshold-bid の「4. 知らせてほしいこと」への答え

- **challenge 11（block 26403144）**: 2026-11-14 04:22:47Z（block 26410802）、満期の約 1.59 時間後に、汎用の取り手 `0x2ff82bd2` が取りました（attempts 1386）。
- **最初の非公開送信の結果**: ありません。bot `franken-threshold-ethereum` は paper で archive されました（attempts 1390）。reviewer が fork で自分で再現したところ、相手が取ったブロックの 1 つ前で打つと、3 件（num 8・9・10）すべて `FlashShort` で revert しました。数えてよい 30 日の期待収益は 0 USD で、lead 74 は blocked_infra に戻りました。同じブロックなら num 8 は +788 USDC、num 10 は +24.6 USDC（ガス前）通りますが、decision の 2 のとおり数えていません。
- earner の fork の証明（num 8 が +2,434 USDC）は、1 つ前のブロックに戻したあと deploy と入札の tx を順に掘ったため、実際には相手のブロックの **後** で入札していました。reviewer が wiki `pitfalls/fork-deploy-off-by-one.md` に書きました。
- meta の変更: earner.md の fork 証明の手順（build の 4）に「deploy や fund の tx を掘るたびにブロックが進む。receipt のブロックが主張するブロックか確かめる」と 1 文足しました（組み立て後 55,533 → 55,663 bytes、上限 56,000 以内）。

## 2. earner の空回り（前回の提案のその後）

- 02:39Z 以降の earner 22 回のうち、対象なしは 9 回（前回 00:00〜02:34Z は 17 回中 15 回）。人間の decision 3 件と researcher の lead 3 件で仕事ができたためです。
- 待ち行列の確認だけの attempts 行は 2/23（前回 20/41）に減りました。前回の earner.md の変更は残します。
- 起動の間引きの提案はそのままです。板が空になると、また同じ状態に戻ります。

## 3. その他

- live は 2 本（gearbox-v3-watcher-ethereum、morpho-nextblock-ethereum）、今日の損失 0、capital 678.82 USD。franken-dutch-ethereum は archive 済みです。
- earner 1 回（c51126ed）が fork の trace の途中で時間切れになり、報告なしで終わりました（1 件のみ、繰り返しなし）。
