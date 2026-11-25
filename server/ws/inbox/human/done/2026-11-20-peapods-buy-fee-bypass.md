# 発見の報告: Peapods の pod の買い手数料 (3%) を回避する経路が ethereum で実際に使われています

送信者: builder-claude、run 850a82b6f2854974834d7b374a579889、2026-11-20。緊急ではありません。farm の資金には関係しません。

## 結論

- Peapods (ethereum) の pod トークンは、公式ペアから出る転送に買い手数料 (pLONGPEAS は 3%) をかけます。ただし転送先が Uniswap V2 Router02 のときは手数料がかかりません (流動性の引き出し用の例外)。
- ある EOA がこの例外を使い、手数料を払わずに pod を買って debond し、差額を取っています。7 日で 17 回、1 回あたり 1.5-8.5 USDC です。
- farm はこの経路をまねしません。プロトコルが誰にでも払うつもりの報酬ではなく、手数料の回避だからです (S: 迷ったら不可)。メインネットでは何も試していません。fork でも回避の経路は実行していません (手数料を払う経路だけを試し、損になることを確かめました)。
- 資金が盗まれる種類の欠陥ではありません。プロトコルの手数料収入が減るだけです。Peapods に知らせるかどうかは人間の判断にお任せします。

## 根拠

- 検証済みソース `DecentralizedIndex.sol` 168 行目 (実装 0x50d2acb0d9ee43c39dcf7cf694e94a0f9187491a): `bool _buy = _from == V2_POOL && _to != V2_ROUTER;`
- 実際の取引: 0xd10f4cfeed06033ab1b840dc6c4666d02c9de665f4d9d32c1972f6a71a56917e (block 26,444,422)。ペア 0x01396bd6... が pLONGPEAS 859.69 枚を Router02 (0x7a250d56...) に送り、その後 `removeLiquidityETHSupportingFeeOnTransferTokens` (LP 2,000 wei) で Router02 の残高がまとめて送信者側に渡ります。手数料の burn は記録にありません。
- 送信者 0x82cfdff27cec8b15951c73c35db9d4a3913c02bf (Euler EVC 0x0c9a3dd6... 経由)。持ち主は調べていません。
- 手数料を払う同じ経路: fork (親 block 26,444,421) で 349.66 USDC が 344.26 USDC になり、1.5% の損です。ペアの出力は 857.86 枚で、手数料なしの計算値 884.4 枚のちょうど 97% でした。
- 記録: KB attempts:2893、protocols:1311、wiki `pitfalls/replay-gain-native-leg-artifact.md`、スクリプト `scratch/r850a/`、`scratch/peapods-arb-ethereum/`。

## お願いしたいこと

なし (報告のみ)。Peapods への連絡をする場合は上の取引ハッシュとソースの行で足ります。
