# 2026-11-09 ledger の動的型・タプル型イベント（inbox/human/2026-11-09-meta-ledger-dynamic-events.md への回答）

meta の最小案を採用し、phase 9d で入れた。

- `event` には、動的型・タプル型・配列を含む完全な正規シグネチャを書く。例: `Released(uint256,address,address[])`、`AuctionOpened(uint256,(address,address,uint256),uint256)`。topic0 は従来どおり、このシグネチャ全体の keccak256 と照合する。
- `indexed` は、先頭から indexed のパラメータに順に名前を付ける（最大 3 つ）。動的型やタプルが indexed の場合は、topic のハッシュ値がそのまま記録される。
- `data` は、残りのパラメータの**先頭から続く静的な 1 ワード型**（address / bool / bytes32 / uintN / intN）にだけ名前を付ける。それより後ろの動的型・タプル・配列は名前を付けずに省略してよく、デコードもされない（CU は増えない）。`data: []` でもよい。
- topic0 が合わないときは、ツールがハッシュしたシグネチャと計算した値をエラーに表示する（11-08 の小さな改善の §1）。
- 制約（従来どおり）: indexed のパラメータは、シグネチャの先頭に並んでいる前提。indexed と非 indexed が交互に並ぶイベントは、今のツールでは正しく対応付けられない。そういうイベントは actor_field を tx_from にして、indexed には何も名前を付けないこと。
- これで、lead 105（Uniswap の fee releaser、3 チェーン）と reserve-folio-dtf の AuctionOpened を ledger で追跡できる。earner / researcher は、以前に拒否された source を直して `ledger add-source` し直すこと。meta は TOOLS.md の ledger の行と、ledger のヘルプに書かれた「Only static ABI types」の説明を、この内容に更新すること（ヘルプの文言は次のバンドルで人間が直す）。
