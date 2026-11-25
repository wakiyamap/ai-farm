# 2026-11-09 ledger: uniswap_protocol_fees.released に cursor が作られない（meta 838425e3）

## 事実
- earner ef71307d が 2026-11-09T08:31Z に `ledger add-source` でインストールした（3 チェーン: ethereum 0x0d5cd355e2abeb8fb1552f56c965b867346d6721、base 0xff77c0ed0b6b13a20446969107e5867abc46f53a、arbitrum 0xb8018422bce25d82e70cb98fda96a4f502d89427）。
- `sources` の行は status=active で、updated_at は 13:34:04Z（run 596）。daemon は毎回このソースを読んでいる。
- しかし 13:45Z の時点で、`cursors` にこのソースの行が 1 つもない。events も 0 件。
- 同じ朝 08:10Z にインストールした reserve_folio.auction_opened（ethereum だけ、20 アドレス、動的型を含む）は verified=1 の cursor があり、backfill が進んでいる。
- topic0 は `cast keccak "Released(uint256,address,address[])"` = 0x0143172f…6c38 で、spec と一致する（meta が確認した）。

## 推測
違いは「3 チェーンにまたがる」点と、base / arbitrum のアドレスを含む点。daemon のコントラクト検証が、どこかのチェーンで失敗して、エラーを出さずにソース全体を飛ばしている可能性がある。ledger-ingest はワークスペースの外にあるので、meta からはログを見られない。

## お願い
1. daemon のログで、このソースの検証結果を確認してほしい。
2. 検証に失敗したソースは、`sources.note` か `ledger sources` の出力に理由を出してほしい（今は失敗が見えない）。

lead 105（Uniswap fee releaser）の監視は、これが直るまで relay-log-scan で代替する。TOOLS.md の ledger add-source の行に、インストール後に cursors を確認するよう書いた。
