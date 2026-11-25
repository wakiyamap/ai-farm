# meta より: phase 11c の反映、ethereum fork の報告の訂正、copy-other-bots の反映（meta run cb13f5e0、2026-11-13）

## 1. phase 11c（EXECUTOR_ADDR）の反映

- earner.md: live では `EXECUTOR_ADDR`（複数チェーンは `EXECUTOR_ADDR_<CHAIN>`）を読み、未設定なら分かるメッセージで終了すること、fork のアドレスに戻らないことを明記しました。lead を閉じる箇所に「2026-11-13T18:35Z より前の executor bot の live 送信 0 件は根拠にならない」を追加しました。
- paper-reviewer.md: promote のたびに live ログの最初の行が `state/executor.json` のアドレスを示すか確認し、違えばすぐ inbox/human に書くこと、ハードコードしたアドレスへの fallback は `fix`、を追加しました。
- `tools/manifest-check.py`: `EXECUTOR_ADDR || '0x…'` のような fallback を警告するようにしました。測定: 既知の 4 本（gearbox-v3-watcher、morpho-nextblock、moonwell-whale3、paper の aave-pricefeed-ethereum）が変更前 0 件、変更後 4/4 件で警告されます。env だけを読む franken-dutch は警告されません（正しい挙動です）。この形の fallback は bot 16 本（live 3、paper 1、archive 12）にありました。
- 「主に live 送信 0 件を理由に lead を閉じた、または bot を止めた」ものの確認（指示 11c-follow-up 第 3 項）:
  - **moonwell-whale-base**（11-10 に人間が停止）: 理由のひとつが「16 時間で送信 0」でした。bot.js:150 に fork アドレスへの fallback があったので、この期間は送れませんでした。ただし主な理由（Alchemy 約 10M CU/日、同一ブロックでの清算が多い）はこの件と関係なく有効です。
  - **morpho-watcher-ethereum**: 11-12 の再審査のきっかけは「19 件あって送信 0、シミュレーションは 7 wei の 1 件だけ」でした。live で fork アドレスを使っていたので、executor へのシミュレーション自体が成り立っていなかった可能性があります。lead は 11-12 に、C-1 時点で清算可能だった事例の分類（attempts 926/1016）を理由に閉じられており、主な理由は送信 0 件ではありません。
  - どちらも meta からは再開していません（指示どおり）。

## 2. 「ethereum fork が ERC-20 の state を返さない」という earner の報告は誤りでした

inbox/meta/ethereum-fork-empty-erc20-state.md（attempts 1139）は fork の再起動を求めていましたが、**再起動は不要です**。earner が確認に使った DAI `0x6B17…C2` と USDC `0xA0b8…2A` は、先頭だけ合っていて後半が違うアドレスでした（mainnet でも code がありません）。正しい DAI/USDC と、lead 167 のブロック 26300832 で、USDT・LUSD・DAI の読み取りはすべて値を返しました（attempts 1144）。lead 167 は `unmeasured` に戻し、原因は executor の経路側だと next_steps に書きました。

再発防止: `tools/rpc.py` が、よく使うトークンのアドレスの「先頭だけ一致」と空の結果に対して stderr にヒントを出すようにしました（この 2 件のアドレスで変更前 0/2、変更後 2/2）。earner.md と wiki pitfalls/ethcall-empty-revert-calldata.md にも書きました。

## 3. decision 2026-11-14-copy-other-bots の反映

- wiki `methods/copy-bots.md` を新しく作りました（A/B/C/D の分類、運用者ごとのカード、毎回の調査、週 1 回の B/C 一覧）。
- researcher.md には要点 1 項目、earner.md には 1 行（A は target、「timing wanted」のカードは測定）、meta.md には B/C 一覧を転送する 1 文を足しました。
- earner のプロンプトは 55,319 → 55,782 バイトです（56,000 以下）。copy-bots の追加分より多い量（過去の事例の注記など）を削りました。増えた分は phase 11c とアドレスの注意書きです。次に earner.md へ何か足すときは、同じ量を削る必要があります。

## 判断をお願いしたいこと

ありません（報告のみ）。
