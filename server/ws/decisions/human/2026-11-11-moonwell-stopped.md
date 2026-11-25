# moonwell-whale-base を止めた理由と、同じ型を出すときの条件（人間の判断 2026-11-11）

## 何をしたか

2026-11-10 18:03Z に、人間が `gate stop moonwell-whale-base` で止めた。sweep と archive は正常に終わっている（PnL −0.02 USD、配備と sweep のガス代だけ）。11-13 02:00Z まで様子を見る予定だったが、それを待たずに止めた。

## なぜ止めたか

- live にしていた約 16 時間で、送信が 1 件もなかった（bot wallet の nonce は executor の配備と sweep だけ）。
- その間、この bot だけで Alchemy を 1 日あたり約 10M CU 使っていた。月間枠は 95.2M で、このペースだと 11-19 ごろに使い切る。月間枠が尽きると、送信は Alchemy だけを通るので、ほかの live bot も含めて全部の送信が止まる。
- reviewer と earner の記録にあるとおり、Moonwell の清算の多くは価格更新と同じブロックで起きる。ポーリングで待つ作りでは、そこに間に合わない。

11-10 の判断（decisions/human/2026-11-10-overlayer-moonwell.md）のとおり、Alchemy の呼び出しは利益が出るなら増やしてよく、出ないならその bot を止める。今回は後者に当たる。

## これからの扱い

1. **同じ型（Moonwell などの清算をポーリングで待つ bot）をもう一度出すなら、次の 2 つを manifest か bot の README に書くこと。** どちらもなければ reviewer は fix にする。
   - ポーリングで取れる根拠: ledger の過去の清算のうち、価格更新と別のブロックで起きたものの件数と、そのときの利益の見積もり。
   - live にしたときの Alchemy の消費見積もり（1 日あたりの CU。ポーリング間隔 × 1 周の呼び出し数 × メソッドごとの CU）。
2. **earner が bots/paper/moonwell-whale-base/ で進めている mAERO 拡張は、別の ID で出すこと**（例: moonwell-maero-base）。同じ ID は archive 済みの bot の記録と混ざる。出すときは 1 の条件も満たすこと。
3. **reviewer は promote の前に、live での 1 日あたりの Alchemy 消費の見積もりを review.md に書くこと**（チェーンと bot の型を問わない）。見込める利益に対して明らかに多い場合は、ポーリング間隔を広げるか、読み取りをまとめる（multicall など）よう fix にする。目安として、1 本で 1 日 1M CU を超える bot は、その根拠を inbox/human に出してから promote する。
4. meta: 1〜3 を earner.md と paper-reviewer.md に反映すること。

Base の中間ウォレットの資金（ETH と USDC 100）はそのまま残してある。Base での promote を止めたわけではない。
