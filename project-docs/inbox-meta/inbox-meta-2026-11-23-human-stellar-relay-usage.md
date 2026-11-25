# Stellar の relay の 2 件は scout の使い方の問題でした（人間、2026-11-23 06:3x JST）

`inbox/meta/2026-11-22-stellar-relay-getledgerentries.md` と `inbox/meta/stellar-relay-getevents-pagination.md` への答えです。relay（16a）は正しく動いています。人間がサーバーで relay 経由で確かめました。

1. **getLedgerEntries**: scout の key は型の部分が誤り（`00000082` = 130 という型はない）。契約のハッシュは正しかった。contract instance の LedgerKey は `CONTRACT_DATA(6) + ScAddress contract(1) + 32 バイトのハッシュ + SCV_LEDGER_KEY_CONTRACT_INSTANCE(20) + PERSISTENT(1)` の 48 バイトを base64 にしたもの。`/srv/farm/ws/tools/stellar-key.py instance C...` が作る（ほかに `account G...`、`code <wasm hash>`、`decode`）。CD3KRKGD…GLYF の instance で `entries: 1` が返った
2. **getEvents のページ送り**: 2 ページ目以降は `startLedger` を付けず、cursor を `"pagination": {"cursor": "...", "limit": 100}` の中に入れる。scout は cursor を外側に置いていたので無視され、cursor だけの呼び出しは「startLedger must be positive」になっていた。1 回の呼び出しは最大約 10,000 ledger しか見ないので、空や短いページは終わりではない。cursor の数値を 32 ビット右にずらした値（= ledger）が latestLedger に届くまで続ける（7 日で約 12 回）。scout の「10,000 ledger ずつ startLedger をずらす」も同じ結果になる
3. getLedgers は `pagination.limit`（素の `limit` ではない）。1 件でも大きいので close time を見るときは limit 1
4. getTransaction の `xdrFormat:"json"` は snake_case（scout の報告どおり）

## お願い（meta）

- `roles/scout.md` の「Stellar (16a, read only)」の節に、上の 1〜3 を 1 行ずつ足してください（getLedgerEntries の key は stellar-key.py で作り手で組まない、getEvents は pagination.cursor で続け空ページで止めない、getLedgers は pagination.limit 1）
- scout が提案した wiki `infra/stellar-relay` を作ってください（上の 1〜4 と、Alchemy だけで公開ノードなし、送信は relay が全部拒否）
- `/opt/farm/context/scout` の Stellar の手順は人間が直しました（16b）
- 2 件のメモは RESOLVED.md に載せてください。getEvents を 10 ページで打ち切った scout の Stellar の結果（例: protocol-stellar-xoxno-lending の最初の「1 件」）は、数え直しが要るかもしれません
