# trial-morpho-cbbtc-base: Base の gas 資金不足

paper-reviewer run `82942d06bfff4171bd1d04597bb04f35` は、この安いチェーンの試行 bot の fork 成功・利益ガード revert・live 経路を確認しました。しかし `gate promote trial-morpho-cbbtc-base` は `intermediate wallet on base has less than 18.00 USD + gas; deposit first` と拒否しました。直後の `gate status` では Base の中間 wallet に native $18.30、Base USDC $100.00 があり、bot への資金移動・deploy はありません。要求は native $18.00 の bot 配分に加えて deploy 用 gas です。正確な gas reserve 額は gate が出していないため、少なくともその不足分を Base の中間 wallet に補充するか、補充しない判断をお願いします。gate の拒否をこの試行の最終結果として記録し、紙 bot は待機のままです。
