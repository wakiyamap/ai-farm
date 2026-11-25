# Moonwell whale bot の Base 昇格資金について

paper-reviewer は `moonwell-whale-base` の昇格基準を満たすことを確認しました。現行 artifact の Base fork では清算の成功で 3.914436 USDC 増え、利益ガードでは `NO_PROFIT` により元本が戻りました。30 USD の累積損失停止も、長時間未決済のレシートと状態ファイル破損を含むテストを通過しました。

2026-11-10 01:22 UTC の `gate promote moonwell-whale-base` は、`intermediate wallet on base has less than 120.00 USD + gas; deposit first` で拒否されました。直後の `gate status` では Base の中間ウォレットに約 21.25 USD 相当のネイティブ資産があり、必要額との差は**少なくとも 98.75 USD 相当と送金ガス代**です。gate の拒否を最終判断として扱い、今回は再試行していません。

Base 中間ウォレットに昇格に必要な資金を補充するか、ご判断ください。Base の bot ネイティブ残高上限は 18 USD のため、gate が 120 USD の事前残高を要求することと実際の bot への送金額の関係も確認していただけると助かります。資金が利用可能になった後、reviewer が再度 gate で判定します。
