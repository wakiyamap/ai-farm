# 段階4：お金（signer / gate / watchdog）

## 構成

| 部品 | ユーザー | 役目 |
|---|---|---|
| `farm-signer` | farmgate | 鍵を持つ唯一のプロセス。Unix ソケットで本番 bot からの署名要求を受け、ポリシー検査 → 署名 → live レーンで送信 |
| `gate` → `gate-ctl` | farmgate（sudo 経由） | promote / fund / sweep / stop / status。X・n を集計 |
| `gate-root` | root（farmgate から sudo） | bot ディレクトリの paper→live→archive 移動と所有権だけ |
| `farm-watchdog` | farmgate | 15秒ごとに残高・nonce を監視。想定外の送金で全停止、L 超の損失でその bot 停止、n 超で凍結。動いたら live 運用を起こす |

## 鍵（BIP-39 / BIP-44 標準）

- 24語のシードフレーズが `/var/lib/farmgate/mnemonic`（farmgate のみ、0400）。インストール時に生成されます。
- 派生は標準の `m/44'/60'/0'/0/<index>`。**index 0 が中間ウォレット**、bot は promote 時に 1, 2, 3… と順に割り当て（`/var/lib/farmgate/accounts.json`、`gate accounts` で一覧）。
- **他の環境での復元**：Rabby / MetaMask / ハードウェアウォレットに同じ24語を入れると、index 0 が中間ウォレットとしてそのまま出ます。bot のアドレスは「アカウントを追加」で index 順に出てきます。このコードは一切要りません。
- **1本だけ秘密鍵を出す**（中間ウォレットだけ Rabby に入れたい等）：自分のアカウントから `sudo -u farmgate /opt/farm/bin/gate-ctl export-key intermediate`。エージェントのユーザーからは実行できません。
- **バックアップ**：`sudo cat /var/lib/farmgate/mnemonic` の24語を紙に控えてください。これが無いと残高に触れなくなります。チャットには貼らないでください。

## ポリシー（コードで強制）

| 項目 | 値 | どこで |
|---|---|---|
| X 総資金 | 2000 USD | gate（promote / fund 時に残高合計を確認） |
| n 日次損失 | 200 USD | gate（超えたら promote 拒否）、watchdog（起こす） |
| L 1 tx 最大損失 | 20 USD | signer（`value + gas × maxFeePerGas` を ETH/USD で換算） |
| bot あたり資金 | 400 USD | gate（manifest の `capital_usd`）、signer（日次送信合計） |
| 送り先 | manifest の `allowed_contracts` と中間ウォレットのみ | signer |
| approve | 許可コントラクトに対して有限額のみ | signer |
| 送信者の特定 | ソケットの peer credentials + cgroup（`bot@<id>.service`） | signer |

## v1 の範囲と、まだ無いもの

- 動かすのは**ネイティブ ETH だけ**（ガス＋value）。bot への資金供給は中間ウォレットからの ETH 送金です。
- USDC の bot への供給、ERC-20 approve の明示的な取り消し、Relay でのブリッジは次の更新。USDC を使う戦略が paper から上がってきた時点で入れます。
- Chainlink の ETH/USD フィードは signer が起動時に `decimals()==8` と `description()` に "ETH / USD" が含まれることを確認し、違えば起動を拒否します。

## 資金の入れ方（少額から）

1. `sudo ./install.sh` の最後に表示される中間ウォレットのアドレスを控える（`gate intermediate` でいつでも表示）
2. **最初は各チェーンに 0.01 ETH 程度**だけ自分のウォレットから送る
3. `sudo -u harness /opt/farm/bin/gate status` で `capital_usd` に反映されることを確認
4. テスト用 bot で promote → `gate status` → `gate stop` → 中間ウォレットに戻ることを確認（下）
5. 問題なければ本番の額（USDC 2000 相当のうち、まず ETH で数百ドルぶん）を入れる

## 動作確認（お金を少しだけ使う）

```bash
# a bot that sends 0 ETH to itself once, then idles: proves sign -> broadcast -> sweep
sudo -u earner bash -c '
d=/srv/farm/ws/bots/paper/selfping; mkdir -p "$d"
cat > "$d/run.sh" <<"EOF"
#!/usr/bin/env python3
import os, sys, time, json
sys.path.insert(0, "/opt/farm/lib")
if os.environ.get("BOT_MODE") == "live":
    import farmbot_signer as S
    me = S.my_address()["address"]
    print("live, my address", me, flush=True)
    r = S.send(chain="base", to=me, value=0, gas=21000, max_fee_per_gas=20_000_000)
    print("send ->", json.dumps(r), flush=True)
while True:
    time.sleep(60)
EOF
chmod +x "$d/run.sh"
cat > "$d/manifest.yaml" <<"EOF"
id: selfping
author: human/test
chains: [base]
strategy: self-transfer of 0 ETH to prove the signer path
capital_usd: 5
allowed_contracts:
  - 0x0000000000000000000000000000000000000000
max_loss_per_tx_usd: 1
max_loss_guarantee: value is 0 and gas is 21000 at 0.02 gwei max
expedite: false
EOF
'
# allowed_contracts must contain the bot's own address for a self-send; get it after promote:
sudo -u harness /opt/farm/bin/gate promote selfping      # funds ~5 USD of ETH on base, starts bot@selfping
sudo -u harness /opt/farm/bin/gate status selfping
journalctl -u bot@selfping -n 5 --no-pager                # expect: send -> {"ok": false, "error": "to ... not in allowed_contracts"}
```

The first run is expected to be **rejected** (self-address not in `allowed_contracts`): that is the policy working. Then:

```bash
sudo -u harness /opt/farm/bin/gate stop selfping          # cancel/sweep/archive
sudo -u harness /opt/farm/bin/gate status                 # capital back in intermediate (minus gas)
sudo tail -5 /var/lib/farmgate/signer.log /var/lib/farmgate/gate.log
```

## 緊急停止

```bash
sudo -u harness /opt/farm/bin/gate stop --all
```

signer が全要求を拒否する状態（`/var/lib/farmgate/halt`）になり、全 bot を停止・回収します。復帰は `sudo rm /var/lib/farmgate/halt`。スマホからは Tailscale 経由で SSH してこの1行です。
