# Lunos旧SSIPの報酬会計に関する未検証の懸念

Ethereumの旧 `SingleSidedInsurancePool`（`0xa476b3F7333796D4565a3D3666D54cF8557F0169`）の検証済みソースを読み、`harvest(address _to)` の内部処理に会計ミスの可能性を見つけました。`_pendingUno` は `userInfo[_to]` から計算し、`onReward(_to, _pendingUno)` で `_to` に支払いますが、報酬債務を更新する行は `userInfo[msg.sender].rewardDebt = accumulatedUno` です。呼び出し元と `_to` が異なる場合、受取人側の債務が更新されず、同じ未払い額を再度請求できる可能性があります。

根拠: [Etherscanの検証済みソース](https://etherscan.io/address/0xa476b3F7333796D4565a3D3666D54cF8557F0169#code) の `SingleSidedInsurancePool.sol`、`harvest` / `_harvest`（308–326行）。`rewarder()` は `0xa76a4a5c8bd6dc07e165f17b0806553ec02f0852` を返しました。2026-11-16 23:10から11-23 23:10 UTCまで、このプールのログは0件です。

実際の過払い可否は未検証です。メインネットでこの挙動を試していません。プロトコルへの責任ある報告と、必要なら修正の確認をお願いします。
