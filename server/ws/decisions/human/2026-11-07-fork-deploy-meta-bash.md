# 2026-11-07 fork deploy の status 0 と meta の Bash（inbox/human/2026-11-06-meta-fork-deploy-bash.md への回答）

## §1 fork deploy の status 0 → 原因はコンストラクタ引数の付け忘れ（ツールの不具合ではない）

- 人間が `scratch/aave2-probe-bytecode.hex` を reviewer 用の fork で再現して確認した。
  - 送信元を変えても、gasUsed は毎回 63022（創成 tx の固有 gas とほぼ同じ）で、revert データは空。
  - 配備先のアドレスにはコードもノンスも無く、アドレスの衝突ではない。
  - anvil は v1.9.0、ethereum の hardfork は Bpo2。設定の問題でもない。
- 原因: このファイルの creation code は `constructor(address)` を持っている。先頭近くの `6102a53803806102a5…` は、コードの末尾からコンストラクタ引数を読む処理で、`0x2a5` = 677 バイトはファイルの長さと同じ。つまり引数が付いていないので、ABI デコードの長さチェックで空の revert になる。「コンストラクタの無い Probe.sol」という報告は誤りで、Probe には immutable を受け取る引数がある。`forge test` は `new Probe(addr)` で引数を付けるので成功していた。
- phase 6u（2026-11-07）から次のようになる。
  - `fork deploy` は引数の付け忘れを検出して、その旨を表示する。
  - `--args <ABI エンコード済みの引数>` で引数を付けられる。例: `fork deploy ethereum <file> --args $(/opt/foundry/bin/cast abi-encode 'constructor(address)' 0x…)`
  - forge の artifact（`out/X.sol/X.json`）をそのまま渡せる。
  - 失敗したときは gasUsed、revert データ、callTracer のエラーを表示する。
- earner.md 3b.2 の回避策（status 0 のときは anvil_setCode か forge test で証明する）は撤回してよい。anvil_setCode で置いたコードではコンストラクタが走らず、immutable が 0 のままになる。そのため本物の配備の証明にはならない。meta は 3b.2 を「fork deploy の警告を読み、引数を付けて再実行」に書き換え、wiki の pitfall にこの症状（固有 gas ぴったり・空 revert）を記録すること。

## §2 meta の Bash

- claude CLI は 11-01 から更新されていない（2.1.316）。人間が同じ設定で `kb --help` を実行させたところ、`Bash(kb *)` の許可で通った。許可リストは 11-06 から変わっていない。
- 拒否は、コマンドの形が原因である可能性が高い。許可は「コマンド行全体」に対して照合される。`cd … && kb …`、`kb … | head`、`VAR=… kb …`、`$(…)` を含む行は、そのうち一部でも許可に無ければ行全体が拒否される。kb / wiki / ledger / `python3 /srv/farm/ws/tools/…` / `git -C /srv/farm/ws/history …` / `date` は、それぞれ単独の 1 コマンドとして実行すること（出力の絞り込みは Read と Grep で行う）。
- phase 6u で、meta に `date` を許可した。
- それでも単独のコマンドが拒否されたら、拒否されたコマンド行をそのまま inbox/human に書くこと。

## §3 モデル名の表記ゆれ

- harness はすべてのセッションに `FARM_MODEL` を渡している（値は roles.conf のモデル名で、ops.db の runs.model と同じ）。
- meta は `tools/session-report.py` を直し、model 欄を引数ではなく `os.environ["FARM_MODEL"]` から埋めるようにすること（引数で渡された値は無視するか、notes に回す）。既存の行は追記専用なので直さず、週次の集計で正規化する。
