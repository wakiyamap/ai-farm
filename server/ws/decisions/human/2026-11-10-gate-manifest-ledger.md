# 2026-11-10 gate の manifest 読み取り・executor の配備・ledger の予算配分（phase 9e）

## 何が壊れていたか（人間側の不具合）

1. **gate の allowed_contracts の読み取り**: gate は `- 0x…` で始まる行しか読まず、franken-dutch の書き方では「allowed_contracts がない」と拒否していた（inbox/meta/2026-11-09-franken-gate-allowed-contracts.md）。signer も、`- 0x… # コメント` のように後ろにコメントがある行を、アドレスとして読めていなかった（live になっていれば、その宛先への送信がすべて拒否されていた）。
2. **executor の配備**: gate は artifact のバイトコードだけを配備し、manifest の `executor_args` を付けていなかった。コンストラクタに引数がある executor は、promote しても全部失敗していたはず。
3. **ledger**: agent が追加した source は、ファイル名の順に 1 回の実行あたり 6000 CU を分け合っていた。後ろの順番の source（uniswap_protocol_fees.released など）には予算が回らず、cursor が作られていなかった（inbox/human/2026-11-09-meta-ledger-uniswap-source-no-cursor.md）。

## phase 9e で直したこと

- gate と signer の manifest の読み取り: `allowed_contracts` と `chains` は、ブロック形式（`- 0x…`）、インライン形式（`[0x…, 0x…]`）、マッピングのリスト（`- address: 0x…`）のどれでもよい。行末のコメントは無視する。**allowed_contracts のブロックの中にあるアドレスは、すべて許可対象になる**（コメントの中のアドレスは対象外。executor_note など別のキーのアドレスも対象外）。
- executor の配備: gate は `executor_args`（ABI エンコード済みの 16 進数）をバイトコードの後ろに付けて配備する。**コンストラクタに bot 自身のアドレス（owner など）を渡す場合は、そのワードを `{bot}` と書く**。gate が promote の時点で、bot のアドレスを 32 バイトにパディングして差し込む。gate は配備のレシートを待ち、成功しなかった場合は promote を中止する。
- ledger: agent の source は、毎回開始位置をずらして均等に予算を配分する。1 つの source あたり最低 600 CU。そのあと残りの予算を同じ順番で配る。

## 指示

- **earner**: executor のコンストラクタに owner 引数がある bot は、`executor_args` のその位置を `{bot}` にすること（固定のアドレスを入れると、gate が配備する executor の owner が bot にならず、live で呼べなくなる）。msg.sender を owner にする作りなら、そのままでよい。
- **meta**: `tools/manifest-check.py` に `{bot}` の記法を受け付ける変更を入れること（`{bot}` を 64 桁のゼロとして長さを検査する）。TOOLS.md にも書くこと。
- **paper-reviewer**: franken-dutch の gate による拒否は不具合だったので、最終判断として扱わなくてよい。基準を満たしている bot は、phase 9e の後にもう一度 promote してよい。promote が配備で失敗したら、gate のエラーをそのまま inbox/meta に書くこと。
- uniswap_protocol_fees.released は、次の数回の実行で cursor ができるはず。meta は、6 時間後に cursor ができていることを確かめること。
