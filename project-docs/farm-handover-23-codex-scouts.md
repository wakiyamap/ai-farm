> Farm 仕様書の続き（23 個目）。本体は `farm/farm-handover.md`。この文書は phase 16e（scout を codex へ、builder-codex と paper-reviewer-claude の廃止）を扱う。
> 状態: **2026-11-24 04:5x JST に人間が適用済み**（テスト 8 項目、codex の疎通、sha256 一致。適用時、待ち行列 140 件、scout 4 本は Qwen の回の途中）。

# phase 16e: scout を codex に、builder-codex と paper-reviewer-claude を廃止

## 何のためか

人間の判断（11-24 04:47、`farm/ops/2026-11-24-0447.md`）: ローカル LLM（qwen-server）を別の用途に使うので、Qwen で動かしていた scout-1〜4 を gpt-6-sol（codex）にする。builder-codex と paper-reviewer-claude は廃止。

## 変更

| 項目 | 前 | 後 |
|---|---|---|
| roles.conf の scout-1〜4 | `scout dsh qwen3.8-flash-next` | `scout codex gpt-6-sol` |
| agent@scout-N の drop-in `scout.conf` | User=earner、qwen-server に After/Wants、`~/.dsh` の bind、ExecCondition で :8003 を確認 | 既定のユーザー（harness）、Qwen に依存しない。35 分・UMask 0002・待ち行列が空なら始めない、は同じ |
| builder-codex | 02:10 JST から 3 時間おき | `farm-builder-codex.timer` を disable（unit と roles.conf の行は残す） |
| paper-reviewer-claude | 24 時間おき、codex 製の bot だけ審査 | `farm-paper-reviewer-claude.timer` を disable（unit と roles.conf の行は残す） |
| `/opt/farm/context/paper-reviewer`（14a の振り分け） | codex 製は `other-reviewer` にして paper-reviewer から外す | 振り分けをやめ、paper-reviewer（codex）がすべての bot を審査。codex 製の bot には review.md に `same-model review (codex)` と書かせる |
| `/srv/farm/ws/scout` | earner が書いたファイル | `chmod -R g+rwX`（harness は group farm） |

- 変えていないもの: run-role（codex の分岐は `--sandbox danger-full-access` で harness として動く）、scout.md、context-scout・scout-enum・scout-done、gate・signer・watchdog・relay、qwen-server（止めるか別用途にするかは人間）
- scout-enum（`farm-scout-enum.service`）は earner のまま。待ち行列のフォルダは harness:farm 2775 なので両方から書ける
- 使用の上限: scout は待ち行列がある限り 4 本が続けて回る（1 本 1 日最大約 40 回）。ChatGPT のプランを paper-reviewer と分け合う。上限に当たるなら scout を 2 本にする（`sudo systemctl disable --now farm-scout@{3,4}.timer`）
- 自己審査: builder-codex 製で paper に残っている bot（grad-flatmoney-arbitrum など）は、同じ codex 系のモデルが審査することになる

## バンドル

- `farm-phase16e.tar.gz` sha256 `31091899e0e91d0315e8bf220c0aa0fd7a3ffeedd0f7e869c1402b26c8d73049`（今回はサーバーでも小文字の元の名前のまま届いた）
- 中身（sha256）: install.sh `184573826b163e9da6be42dc954dc19801ad954fac0d3e32a8c4dd4e57f857db`、context-paper-reviewer `a13d575ef44ae435866a1706c08136b5f89edb6ff900692c9231916f24473995`、units/scout.conf `d8ca1eff6cb35bf792601c92c28f7fa39331187c9b14bc1014bbae65cc45c60e`、test-16e.sh `c7887c40c0b8968873a52f8b97a7b6f57a0fd75dc5149d294704b4e4b1cc927c`、meta 宛て `816c7b892d53ba1dbb292cb194e02b18d3beec84341b968843f69c68867434ec`
- install.sh は最初に harness で `codex exec -m gpt-6-sol` の疎通を確かめ、通らなければ何も変えない。走っている Qwen の scout は止めない（最大 35 分で終わり、次から codex）。すぐ Qwen を空けるなら `sudo systemctl stop agent@scout-{1,2,3,4}.service`（取っていた候補は 45 分後に待ち行列へ戻る）
- meta 宛て `inbox/meta/2026-11-24-phase16e-codex-scouts.md`（役割ファイルから 2 本目の builder と振り分けの記述を消す、flatmoney の調査は builder-claude に、codex の上限に当たったかを報告）

## 止め方・戻し方

- バックアップは `/etc/farm/bak-16e/`（roles.conf、context-paper-reviewer、scout-1〜4.conf）
- 戻す: `sudo cp -a /etc/farm/bak-16e/roles.conf /etc/farm/roles.conf`、`for n in 1 2 3 4; do sudo cp -a /etc/farm/bak-16e/scout-$n.conf /etc/systemd/system/agent@scout-$n.service.d/scout.conf; done`、`sudo cp -a /etc/farm/bak-16e/context-paper-reviewer /opt/farm/context/paper-reviewer`、`sudo systemctl enable --now farm-builder-codex.timer farm-paper-reviewer-claude.timer`、`sudo systemctl daemon-reload`、scout-1〜4 の `assemble-prompt`
