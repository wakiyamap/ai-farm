# セキュリティ所見: Sunflower (SFR) の旧 farm で、預けた直後の人が過去分の報酬まで受け取れる（farm は使いません）

- 書いた人: builder-claude（run 0008b43f、2026-11-21 12:52Z）
- 判断: **S に当たるので farm では使いません。mainnet でも fork でも試していません。** 読んだのは検証済みソースと、他人の取引 1 件の receipt だけです。
- お願い: 特にありません。記録のための報告です。プロジェクトへの連絡が要るかどうかは人間の判断に任せます（2020 年の放置された farm に見えます）。

## 何が起きているか

1. 対象（ethereum）: SunflowerMainV2 `0x8e678b655a6b6e7f31747557a6a90a529b67a990`（Etherscan 検証済み、報酬トークン SFR `0x8ab98c28295ea3bd2db6ac8b3ca57a625c054bd1`）と、旧 SunflowerMain `0x85ffb40d73759e7268c1dde27e02adc53bee6873`。
2. ソースの読み（`scratch/r0008/sfr-rew/SunflowerMainV2.sol` 1570-1617 行）: pool 3 だけ、V2 の `deposit` / `withdraw` が「V2 の預け額 + 旧 V1 の預け額（`getAmountV1`）」に `accSunflowerPerShare` を掛けて報酬を払います。ところが V1 に預けた時点では V2 側の `rewardDebt` は 0 のままです。そのため、V1 に預けた直後に V2 の `deposit(3, 0)` を呼ぶと、預けていなかった期間の分まで報酬として計算されます。払われる額は V2 が持っている SFR の残高が上限です（`safeSunflowerTransfer`）。つまり、ほかの預け手に渡るはずの発行分を、預けてすぐ引き出す人が取れます。
3. 実際にやっている人がいます: MEV bot 2 つ（`0x00000f91109c4d0007e90000d9facad5298a0cac`、`0x2819bac791627e5c5ae5048017145b226f51941d`）が 2 日で 34 回（SFR の mint を伴う取引、ブロック 26,449,170-26,463,570）。例: `0xfdf0b045c4a331151e3c7a2b48dee49cb40b1e2aaba4f25c78362b6f8c25a624`（ブロック 26,455,970）。0.002 WETH でトークン `0xed6b0dc3...` を買い、V1 に預け、V2 から 0.335 SFR を受け取り、V1 から同額を引き出し、全部売って 0.002219 WETH。差は +0.000219 WETH（約 0.36 USD）、ガスは 0.000088 ETH（約 0.15 USD）。
4. 規模: 1 回 0.2 USD ほどの純益、1 日 17 回ほど。小さいです。

## 確かでないこと

- ソースと receipt からの読みで、自分では 1 回も実行していません（S: バグは mainnet で試さない）。V1 側の `getAmountV1` の中身は読んでいません。
- 「意図された仕組み」である可能性は低いと考えます（預けていない期間の報酬が出るため）。迷う場合は不可、の規則に従いました。

## KB

- attempts に dead_end として記録します（対象名に Sunflower / SFR、理由に S）。同じ bot の取引が今後の flash census に出ても、作らないでください。
