# 試行 bot 2 本の起動ログに `executor armed` がありません

2026-11-17 01:19 UTC、paper-reviewer run `27962d42400d4406944430dc0f0f593c` で次の 2 本を promote しました。いずれも `state/executor.json` のアドレスと live 起動行の `executor` は一致しています。

| bot | 配備された executor | live 起動行 |
|---|---|---|
| `trial-cv3-buy-base` | `0xc9aebcc566b6d70a055cfda9742891d49f41e237` | 01:16:57Z |
| `trial-oraclebatch-hai-optimism` | `0x730af68bb34e14a98917da99d9eebf962e6dd144` | 01:18:14Z |

両方の bot の live 起動行に `executor armed` がありません。現行 executor は owner 以外の設定・approve を配備後に行う必要がなく、ソースにも setup tx はありません。それでも paper-reviewer の手順は promote 後にこの行がない場合、直ちに人間へ報告するよう求めています。配備の失敗は確認しておらず、現時点で停止操作はしていません。起動ログの形式をこの 2 本に合わせて明確にするか、行を追加するかの判断をお願いします。
