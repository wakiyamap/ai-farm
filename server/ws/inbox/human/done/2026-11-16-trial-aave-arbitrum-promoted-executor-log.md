# trial-aave-arbitrum を promote しました（安いチェーンの試行）: live ログに executor のアドレスの行がありません

- 2026-11-16 20:50Z に `gate promote trial-aave-arbitrum` が成功しました。bot wallet は 0x82eCDC82eab0Cd3fe16340170151692ce061B4b2、資金は arbitrum のガス 15 USD、principal は 0 です。
- `bots/live/trial-aave-arbitrum/state/executor.json` の executor は 0x46aaa11f0146a3c49faaeae30ed9a82feda15480 です（deploy tx 0x3441740e355a1eb9d27e356a39ec621662b5bf9d39293872ed81519e50196e5b、wallet nonce 1）。deploy まで済んでいるので、資金だけ入って止まった状態ではありません。
- ただし、bot の起動ログ（`ev:start, mode:live`）には executor のアドレスが出ません。bot のコードがこのアドレスをログに書いていないためです（phase 11c の確認項目）。`executor armed` の行は不要です（セットアップの tx がない bot です）。bot は環境変数 `EXECUTOR_ADDR(_ARBITRUM)` を読み、無ければ live では起動しない作りなので、実害はないと見ています。
- 1 回の送信の損は、最大手数料 0.1 gwei × 推定 gas ×1.25 で約 0.11 USD です。executor は利益が gas 上限の 125% を下回ると revert します。fork で reviewer が再現しました（成功 tx 0x2ddac27e...: wallet +0.00449 ETH、残高・approve はともに 0。revert は NoProfit / 対象なし / owner 以外の 3 通り）。
- 対応: 次に earner が触るときに、起動ログへ executor のアドレスを足すよう review.md に書きました。止める必要はないと考えます。
