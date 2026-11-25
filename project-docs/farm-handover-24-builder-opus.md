> Farm 仕様書の続き（24 個目）。本体は `farm/farm-handover.md`。この文書は phase 16f（縮小運転: builder-claude を 12 時間おきに、builder-opus を追加）と 16g（record-run の空振りの no_report をやめる）を扱う。
> 状態: **16f は 2026-11-24 13:58 JST、16g は 14:27 JST に人間が適用済み**（どちらも `commands.sh` の sha256 一致）。

# phase 16f: builder-claude を 12 時間おきに、builder-opus を追加

## 何のためか

人間の判断（11-24 09:09・09:22・09:29）: Farm は縮小運転で続ける。Claude の回数を抑え、builder の回の一部を Opus にする（DeepSeek V4 Pro への置き換えも比べたが、とりあえず Opus）。

## 構成（今の値）

| instance | role | harness / model | 起動 | drop-in / unit |
|---|---|---|---|---|
| builder-claude | builder | claude / `claude-mythos-5-2` | 00:40・12:40 JST | `farm-builder-claude.timer.d/every-12h.conf`（`OnCalendar=*-*-* 00/12:40:00 Asia/Tokyo`）。前の `every-4h.conf` は `/etc/farm/bak-16f/` |
| builder-opus（新） | builder | claude / `opus` | 06:40・18:40 JST | `farm-builder-opus.timer`（`06/12:40`）、`agent@builder-opus.service.d/` は builder-claude の写し（75 分、UMask 0002） |

- 実行ユーザーは harness（確認済み）。prompt は builder-claude と同じ 52,389 bytes
- 1 日の builder の回: 6 回（全部 Mythos）→ 4 回（Mythos 2・Opus 2）。費用は約 28 USD/日 → 十数 USD/日の見込み（Opus 1 回 約 2.8 USD の見立て）
- 2 本は 6 時間ずつずれていて重ならない。bot の manifest の author は `builder/opus` になり、paper-reviewer（codex）が審査する
- meta 宛て `inbox/meta/2026-11-24-human-builder-opus.md`。meta は builder.md を「同時に動く builder は 1 つ、Mythos と Opus が交互」に直した
- roles.conf の builder-codex の行は残っている（timer は disabled、16e）

## 止め方・戻し方

- 戻す: `sudo systemctl disable --now farm-builder-opus.timer`、`sudo rm /etc/systemd/system/farm-builder-claude.timer.d/every-12h.conf && sudo cp -a /etc/farm/bak-16f/every-4h.conf /etc/systemd/system/farm-builder-claude.timer.d/`、`sudo systemctl daemon-reload`（roles.conf の builder-opus の行は残しても害はない。消すなら `/etc/farm/bak-16f/roles.conf` を戻す）

# phase 16g: ExecCondition で止まった起動に no_report を書かない

## 何のためか

scout の待ち行列が空の間、`farm-scout@N.timer` は毎分起動し、そのたびに agent@scout-N が ExecCondition で止まる。record-run（ExecStopPost）は `SERVICE_RESULT=exec-condition` の回にも「エージェントが報告を書かなかった」として no_report を足していた（11-24 は 5.5 時間で 1,181 行、meta の報告 `inbox/human/2026-11-24-meta-scout-queue-empty.md`）。エージェントは始まっていないので、報告を求める理由がない。

## 変更

- `/opt/farm/bin/record-run` の `ensure_report()` の先頭（`if not run_id: return` の直後）に `if result == "exec-condition": return` を 1 行足した（136 行目、目印 `# phase16g`）
- runs の表への記録と history の snapshot は今までどおり（変えたのはセッション報告の代わりの行だけ）
- 当てた後の sha256 `f4011e1d18ff7677eb1bf3c7c5af35b031344afc9804e49d55319f5eb31a7b2e`。この Project の `farm/current/opt/farm/bin/record-run` は当てる前の古い写しのまま
- `farm/phase16g/commands.sh`（sha256 `643309c4d1751c5b21dfaa056ca01ae29b750e1fa555d3e2b3fa41394cc6c8f7`）

## 戻し方

- `sudo cp -a /opt/farm/bin/.record-run.bak-16g /opt/farm/bin/record-run`
