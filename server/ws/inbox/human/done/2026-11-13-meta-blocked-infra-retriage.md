# blocked_infra の見直し 一覧（meta、2026-11-13）

decision 2026-11-13-blocked-infra-feed-retriage の 4 による報告です。earner が全件の分類を終えました（元の英語: `inbox/meta/blocked-infra-retriage-list-039c55c9.md`、`2026-11-13-retriage-31-41-42-44.md`、attempts 1053〜1084）。数字は earner の記録をそのまま訳したもので、meta は測り直していません。

## unmeasured に戻したもの（7 件）

| lead | 対象 | 分類 | ブロック数の内訳・根拠 |
|---|---|---|---|
| 14 | morpho ethereum | (a) 速度 | 0 ブロック 15 件 / 1 ブロック 3 件 / 2 ブロック以上 14 件（粗利 12,313 / 4,083 / 記載なし USD） |
| 17 | aave ethereum | (a) 速度 | **11 月初めの測定（attempt 60）の持ち越し**: 抽出 10 件中 7 件の窓が 600〜89,916 秒。下の注意を参照 |
| 33 | dolomite ethereum | (a) 速度 | 30 日で 18 件。2 ブロック以上 9 件（うち 5 件は 8 ブロック以上）、2 ブロック以下 9 件 |
| 21 | base | (a) 速度 | 再開（attempt 1068） |
| 44 | morpho midnight base | (a) 速度だが、越える時刻は前もって計算できる（満期の秒） | 0 / 0 / 2 ブロック以上 318 件。大口 26 件で粗利 6,508 USD、窓 5〜359 秒（farm の 2〜3 秒より長い）。見直しで初めて「作る対象」になった lead |
| 72 | moonwell 大口 base | (a) 速度（古い抽出） | 対象の組み合わせが復活し、ポーリングで取れる事例が 30 日で 5 件 |
| 157 | morpho base | (a) 速度（先取りされた分） | 公開から取られるまでの窓を 11 件で測定 |

## blocked_infra のまま

- (a) 速度、数え直しても 2 ブロック以上の粗利がほぼない: 5（compound v3 eth、+1 ブロックは 1 件だけ）、35、67、1、2、6、7、9、12、13、15、31、41、42、57、147、18、73、117
  - base / arbitrum は秒でも数えた: arbitrum で 2 ブロック以上は 30 件中 3 件（0.7 / 1.3 / 149 秒、粗利 0.04 USD 以下）。exactly（41）は 105 件すべてが 0.2〜2 秒で farm より速い
- 10（aave base の利息で境界を越える型）: 越える時刻は計算できるので速度勝負ではない、と記録したうえで据え置き
- (d) 道具: 91、94、103（1inch のキーは 11-09 に見送り済み）、129（hyperevm、キーなしのエクスプローラ API がない）
- (b) 権限: 145（morpho hyperevm、NOT_AUCTIONEER / BAD_NONCE で revert することを fork で確認）

## 注意: lead 17 の数え直しは無効でした

11-13 02 時台に earner が「ethereum の eth_call が全部 revert する relay の障害」として記録した件は、いただいた指摘どおり呼び出し側の誤りでした。meta が確かめたところ、原因は 2 つありました。

1. decimals() のセレクタを手で打って間違えた（0xed42883a。正しくは 0x313ce567）
2. lead 17 の 30 日の数え直し（`recount.py`）が、アドレスの引数を 32 バイトに詰めずに送っていた。15 件すべてが revert したのはこのためで、詰めて送ると同じブロックで値が返る

lead 17 の next_steps に訂正を書き、やり直しの手順も書きました。aave-watcher2-ethereum は、decision 2026-11-13-aave-watcher2-recount のとおり、測り直しと SVR の確認がそろうまで promote されません（paper-reviewer.md に反映済み）。

再発を防ぐため、`tools/rpc.py` を変えました。eth_call が空のデータで revert したとき、引数の長さが 32 バイト単位でないことと、セレクタが既知の getter かどうかを stderr に表示します。earner.md にも「セレクタは cast sig で、calldata は cast calldata で作る。障害と判断する前に既知の getter を 1 つ試す」と足しました。

## お願い

判断していただくことはありません。報告だけです。
