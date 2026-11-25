> Farm 仕様書の続き（9 つ目）。本体は `farm/farm-handover.md`。この文書は phase 14a（builder と、モデルで分けた審査）と 14d（Claude の reviewer と meta の道具）を扱う。
> 状態: **14a は 2026-11-17 04:2x JST、`hourly.conf` は 04:3x JST、14d は 06:38 JST に人間が適用済み**。本体の表（役割とモデル、unit）にはまだ足していない。

# phase 14a: builder と、モデルで分けた審査

## 何のためか

人間の判断（11-17 04:10、`farm/ops/2026-11-17-0410.md`）: 役とモデルの割り当てを入れ替える。14a はその前半で、作り手（builder）と審査の分担を入れる。後半は 14b・14c（scout、`farm/farm-handover-10-scouts.md`）。

## 構成（今の値）

| instance | role | harness / model | 起動 | 備考 |
|---|---|---|---|---|
| builder-claude | builder（新） | claude / `claude-mythos-5-2` | 毎時 40 分（drop-in `farm-builder-claude.timer.d/hourly.conf`。unit 自体は 00:40 JST から 3 時間おき） | earner-claude の後継 |
| builder-codex | builder（新） | codex / `gpt-6-sol` | 02:10 JST から 3 時間おき（1 日 8 回） | |
| paper-reviewer-claude | paper-reviewer（同じ役割ファイル） | claude / opus | 前回終了から 90 分（起動 10 分後が最初） | codex 製の bot だけを審査 |
| paper-reviewer | paper-reviewer | codex / gpt-6-sol | 今のまま | codex 製以外（Claude・Qwen・不明）を審査 |

- 実行ユーザーはどれも harness。builder の 2 本は drop-in `agent@builder-*.service.d/session.conf`（75 分で打ち切り、UMask 0002）。reviewer-claude は既定の 2 時間
- 止めた timer（unit は残す）: `farm-earner-claude`、`farm-researcher-claude`、`farm-researcher-codex`。researcher の仕事（新しい型を探す、bot census、`ledger add-source`）は builder.md に入れた
- 変えていないもの: gate・signer・watchdog・relay、common.md
- 組み立て後の prompt（meta が 11-17 05:47 に TOOLS.md と paper-reviewer.md を足した後）: builder 49,672 bytes、paper-reviewer 50,677 bytes

## ファイル

- `roles/builder.md`（新、16,162 bytes、14a 版 sha256 `ab1cd6c78d281f5ccd200bd29ef0ea63f0881d21d51aed01ce468b13cd026413`）: earner.md から測定のレーン・測定の依頼・researcher との受け渡しを外し、試行の bot（decision 2026-11-17-cheap-chain-trials）を本文に入れ、新しい型の探し方（「誰が払われているか」と bot census の要点）を足した。反応時間と期待収益は試行でない bot だけ。signer のアドレスの辞書の落とし穴を 1 行。meta が保守する（18 KB 以下、規則は削る側）
- `/opt/farm/context/builder`（新）: earner の文脈（レーンの行を除く）に、ethereum 以外で blocked_infra の lead（試行の候補）と、live の試行の bot の数を足す
- `/opt/farm/context/paper-reviewer`: 元のファイルを `paper-reviewer.base` に移し、包むスクリプトに置き換え。manifest の `author` に gpt / codex を含む bot は paper-reviewer-claude、それ以外は paper-reviewer。相手の bot の行は due が `other-reviewer` になる。印の行 `farm-phase14a-reviewer-routing`。meta が paper-reviewer.md に「`other-reviewer` の行は飛ばす」を足した
- roles.conf: 3 行足した（置換前は `roles.conf.bak-14a`）
- meta 宛て: `inbox/meta/2026-11-17-phase14a-builders.md`

## run-role の変遷（sha256 はどれも適用時に実測一致）

| phase | 変更 | 後の sha256 | 置換前 |
|---|---|---|---|
| 13b | earner-claude の Bash の一覧を広げた | `c355840c1a470b6970ef930250b543b8830ea0ea7d721615c0c07a275791c058` | `.run-role.bak-13b` |
| 14a | `earner)` → `earner|builder)` | `586ca98574b6d091a2c290271cb9f29cc3556362cd475292f11b0d9e1c720bd1` | `.run-role.bak-14a` |
| 14d | paper-reviewer と meta の claude の一覧に `date*`・`python3 *`・`jq`・`ls`・`cat`・`head`・`tail`・`grep`・`wc` | `6229fed446698cd92991f9df9aa6460c0504eb628ffa4901365249e622c663ac` | `.run-role.bak-14d` |

14d の理由: paper-reviewer-claude の最初の回で `python3 /srv/farm/ws/tools/manifest-check.py` が拒否された（審査の必須手順。`inbox/meta/2026-11-16-paper-reviewer-claude-bash-denied-7e676a2d.md`）。meta の回でも `ls` と `python3 -c` が拒否されていた（meta の報告 `inbox/human/2026-11-16-meta-phase14-trials-first-report.md` の 5-1）。codex の reviewer は claude の一覧を読まないので影響なし。バンドル `farm-phase14d.tar.gz` sha256 `2240592d676ae5c297d2ffafb8d6a4eadd0010cc7cb1ebbb0c5af5adc371bcbe`。

## 費用（11-17 04:23 の人間の判断）

- 人間が使用クレジットを 1,000 USD 買い足した（計 1,006.04 USD、期限 2027-05-17）。月の上限は買った額ちょうど（人間が設定）。プランの枠を超えた Claude の利用は確認なしでここから引かれる（`-p` のセッション）。人間自身の Claude の利用も同じ
- builder-claude を 1 時間おきにすると、Mythos の回（定価 2〜8.4 USD。05:40 の回は 2.34 USD）が 1 日最大 24 回で、1 日 50〜150 USD

## 実際の動き（11-17 06:30 JST まで）

- builder-claude: trial-oraclejob-hai-optimism の fix を 2 回（時刻で送る形に書き直し、SAFEEngine の権限を tx の中で外す）
- builder-codex: trial-aave-arbitrum を作り、paper-reviewer-claude が 20:49Z に promote。モデルで分けた審査で通った最初の bot
- paper-reviewer-claude の最初の回は Bash がほぼ通らなかった（14d で直した）
- session-report.py が role builder を断っていた（meta が 05:47 に直した）

## 止め方・戻し方

- 1 時間おきをやめる: `sudo rm /etc/systemd/system/farm-builder-claude.timer.d/hourly.conf && sudo systemctl daemon-reload`
- 14d を戻す: `sudo cp -a /opt/farm/bin/.run-role.bak-14d /opt/farm/bin/run-role`
- 14a を戻す: 新しい timer 3 つを disable、`farm-earner-claude`・`farm-researcher-claude`・`farm-researcher-codex` の timer を enable、`cp -a /opt/farm/bin/.run-role.bak-14a /opt/farm/bin/run-role`、`mv /opt/farm/context/paper-reviewer.base /opt/farm/context/paper-reviewer`、`/etc/farm/roles.conf.bak-14a` を戻す、`rm /srv/farm/prompts/roles/builder.md /opt/farm/context/builder`、`systemctl daemon-reload`
