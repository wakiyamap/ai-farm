# DFX V2 Ethereum: AssimilatorV2 のアクセス制御確認依頼

Ethereum の DFX V2 を調査中、検証済みの `AssimilatorV2` ソースに、アクセス制御のない `outputRaw(address _dst, uint256 _amount)`、`outputNumeraire(address _dst, int128 _amount)`、`transferFee(int128 _amount, address _treasury)` を見つけました。いずれもコントラクトが保持するトークンを指定先へ送る実装です。これらがプール資産を保持する Assimilator にデプロイされている場合、第三者による不正引き出しの可能性があります。

根拠: DefiLlama アダプターが Ethereum の V2 factory `0x9adeac3b6d29d9d5e543b8579e803a7cce72c9cd` を指定。factory の `NewCurve` ログから pool `0xda9dcc7fd51f0d9aa069a82647a5f3ba594edaed` を確認し、Etherscan 検証済みソースの `src/assimilators/AssimilatorV2.sol` 153–195 行と 306 行以降を確認しました。`intakeRaw` はトークンを Assimilator 自身へ転送します。

本番で引き出し関数の呼び出しや残高調査はしていません。コード上の懸念であり、実際の影響範囲は未確認です。プロトコル側への責任ある報告を検討してください。farm はこの経路を収益化しません。
