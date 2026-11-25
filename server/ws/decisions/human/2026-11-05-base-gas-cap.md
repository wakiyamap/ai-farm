# 2026-11-05 Base（OP Stack）での L の扱い（inbox/human/2026-11-04-meta-base-l1fee-and-perms.md への回答）

## §1 L の手数料上限 → (a) を採用、phase 6i で実装済み

reviewer の指摘は正しい。OP Stack では L1 データ手数料と operator fee が inclusion 時に課され、署名済み tx のどのフィールドでも上限を決められない。そこで Base では「bot のネイティブ ETH 残高」を強制上限とする。

コードで強制していること（phase 6i、2026-11-05 適用）:

- `/etc/farm/gate.json` に `gas_wallet_cap_usd: {"base": 18}`。
- gate は promote / fund で、対象チェーンの bot ネイティブ残高が cap を超えるような送金をしない（送る額 = min(要求額, cap − 現残高)）。`gate status` に cap を表示。
- signer は対象チェーンでの署名要求ごとに bot のネイティブ残高を読み、cap を超えていれば拒否する（想定外の入金があれば自動的に止まる。watchdog の全停止も従来どおり）。
- common.md の L に上記を明記した。

帰結: Base 上の bot の 1 tx の最悪損失は「その時点のネイティブ残高 ≤ 18 USD < L」で、tx のフィールドではなくウォレット残高と signer の検査が保証する。bot 側で `LIVE_FEE_CAP_ENFORCED=false` にして live 送信を止めている回避は不要になるので、earner はそれを外して再提出してよい。reviewer は「inclusion 時の手数料上限」のブロッカーを、この gate / signer の不変条件で満たされたものとして扱うこと（`gate status` の `gas_wallet_cap_usd` と signer の `limits` で確認できる）。

前提: Base の bot は元本をフラッシュローンまたはトークン残高で調達し、ネイティブ ETH はガスにしか使わない。ネイティブ ETH を元本に使う設計は Base では L を満たせないので、manifest でそう設計しないこと。

(b)（推定の N 倍以内なら可）は採用しない。(c) も採用しない（Base は live 可）。

## §2 meta の python3 / git が denied

phase 6f の許可パターンに私のミス（`//srv/...` という接頭辞）があり一致していなかった。phase 6h で修正済み（2026-11-05）。次回の meta から `python3 /srv/farm/ws/tools/*` と `git -C /srv/farm/ws log / show / diff / status` が通る。まだ denied なら、拒否されたコマンドをそのまま inbox/human に書いてほしい。

## §3 scratch の 0600

earner の umask ではなく、dsh の Write が明示的に 0600 で作るため default ACL の mask が落ちる。5 分ごとの farm-acl-fix.timer で group 読み取りを開けているが、find の書き方のバグでファイルに効いていなかった。phase 6h で修正。reviewer が 0600 に当たったら、5 分待って再試行すれば読める。
