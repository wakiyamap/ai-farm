# 1inch Fusion API key の登録 (paper bot reserve-folio-dtf-ethereum)

日付: 2026-11-08 (run 38ad26233ab648f28039ebc21ed9a2bf)

## 提案

1inch の API key を 1 個、開発者ポータルでメール登録（アカウント取得）してほしい。
取得後、`bots/paper/reserve-folio-dtf-ethereum/state/fusion_key.json` に
`{"key": "..."}` として置いてください（bot が読み取ります）。

## 理由（測定済み事実）

- Reserve Folio (DTF) のリバランス Dutch オークションで、計測された唯一の実行可能な venues は
  1inch Fusion vault である:winner の fill は Swapper `0x6131b5fae19ea4f9d964eac0408e4408b66337b5`
  と AGV vault `0x8f10b468b06c6fd214b65f87778827f7d113f996` だけを通過し、バスケットの Ondo 株トークン
  12 種は Uniswap V3 プールが USDC/WETH に対してゼロ（attempt 560、`scratch/dtf-v3-pools.json`）。
- 新しい quote は `https://api.1inch.com/v1.1/1/fusion-v1/swap` からのみ取れる。
  quote は taker 限定（Order の taker を our executor に patch すると vault が revert:
  attempts 563/564、fork tx `0x9cc194beacc8119000ee0fafaa526fda969fd8e2de7116a94a15922f3b005a8b`）。
  したがって winner の blob の使い回しは不可、bid ごとに新しい quote が必要。
- この endpoint は key なしで HTTP 401（`Missing or invalid authorization`、
  `scratch/dtf96-401.txt`）。`Authorization: demo` / `1234567890` も 401 `Invalid API key`
  （run 38ad2623 で再測定、`scratch/dtf96-auth-*.json`）。key のチェックはパラメータ検証より前に走る。
- 必要量は小さい:quote は auction あたり 1〜3 回 × auctions ~1.3 回/日（census 2026-10-19..11-06 で
  AuctionOpened 25 件）→ 1 日 10 回以内。無料プランの rate limit で足りる見込み（有料プランが必要なら
  月額の数 USD の範囲と読む）。on-chain の追加コストは 0（quote は HTTP、legs は executor が実行）。

## 影響

key が届くと:paper bot が次の auction バーストで venue legs を組み、profitable paper capture
（after-gas、実際の venue legs、wallet payout）を審査に出せる。executor v3
（`FolioBidV3.bidWithLegs`、guard は `src/FolioBidV3.sol:56`、同一 tx で owner payout）の
fork 上の venue-out success proof も同じ key 待ち（`fork_evidence` に guard/control tx は記録済み）。
key が無い間、bot は fail closed（venue legs なしでは send しない。fake legs は作らない）。
