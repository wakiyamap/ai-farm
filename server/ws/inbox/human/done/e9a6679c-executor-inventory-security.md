# 紙上ボットの実行コントラクトに関するセキュリティ所見

Aave Base と Morpho Base の現行案には、第三者が任意のスワップ先を指定でき、蓄積した利益トークンを失う可能性があります。両ボットは `fix` とし、昇格は申請していません。gate status では稼働中のライブボットはありません。

AaveLiquidator.sol の liquidate は認証がなく、担保の既存残高全体を呼出者指定の router に承認します。最終検査は別の呼出者指定 debt トークンのみです。MorphoLiquidator.sol は同じ担保について allowance と callback の二重支払いが可能な構造で、任意市場・任意 swapTarget と組み合わせると既存在庫が最終検査から漏れます。これはソースからの静的所見です。攻撃の実行・検証は行っていません。

修正案は入口の operator 認証、市場・トークン・スワップ先の制限、担保増分だけの使用、不要な承認の削除、callback の有効操作への紐付けです。詳細と証拠は bots/paper/aave-watcher-base/review.md、bots/paper/morpho-watcher-base/review.md、および scratch/review-e9a6679c/ に保存しました。既存の 16:14 頃のレビュー所見を現行ソースで再確認した報告で、外部プロトコルの脆弱性を主張するものではありません。
