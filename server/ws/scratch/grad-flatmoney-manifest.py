from pathlib import Path
import yaml

root = Path('/srv/farm/ws')
src = root / 'bots/live/trial-flatmoney-arbitrum/manifest.yaml'
dst = root / 'bots/paper/grad-flatmoney-arbitrum/manifest.yaml'
m = yaml.safe_load(src.read_text())
m['id'] = 'grad-flatmoney-arbitrum'
m['author'] = 'builder/gpt-6-sol'
m['strategy'] = ('Flat Money delayed-order keeper on Arbitrum: execute a public order with a fresh '
                 'Pyth update, sell its fixed WBTC keeper fee to ETH atomically, and return the ETH to the bot wallet.')
m['copied_from'] = ('trial-flatmoney-arbitrum live record (13 won of 13 sends, 2026-11-17 through 2026-11-20); '
                    'original incumbent EOA 0x45d83e658e2f70ba83e4e519f792f065c4a01d7d; '
                    'winner tx 0xd5e1af2d9a6be6ff7d95fb77daeeae373a3ef274bc8399a142d5503a2cfd87f2.')
m['capital_usd'] = 10
m['max_loss_per_tx_usd'] = 1
m['max_loss_guarantee'] = (
    'FlatOrderKeeper.run requires endNative >= startNative + msg.value + minProfit and sends the entire '
    'native balance to the owner (scratch/trial-flatmoney/contracts/src/FlatOrderKeeper.sol:91-96); '
    'a failed attempt loses gas only. In bot.py SEND_CAP_USD=0.95, eth_estimateGas x 1.30 sets the gas limit, '
    'and gasLimit x maxFeePerGas is capped at 90% of simulated gross, with minProfit equal to that gas cap. '
    'The priority bid remains capped at 20% of gross, unchanged from the trial: its 13 won sends spent '
    '12.2%-13.3% of gross as priority fee, while the historical incumbent used zero. No fee increase is justified '
    'by 13/13 wins. Signer enforces <=1 USD at signing time; manifest cap 1 USD.'
)
m['expected_value'] = (
    'Trial live 126.9 h at 2026-11-23 11:11 UTC, 13/13 sends won; logs/bot.jsonl sum gross '
    '0.001132496901265182 ETH, gas 0.000361711167210385 ETH, net 0.000770785734054797 ETH. '
    'grad-candidates.py gave funded 9.56 USD, wallet 10.85 USD, net +1.29 USD since promote, '
    'about 0.244 USD/day over 5.29 days at the current wallet valuation. '
    'The original 7-day incumbent census: 45 takes, 199-262 sat WBTC each, blocks 522693627-525113627 '
    '(attempts:1835). Fixed reward: increasing capital does not increase gross; keep 10 USD. '
    'This grad replaces the trial once promoted; the trial remains live until the human stops it.'
)
m['fork_evidence'] = ('Reran scratch/trial-flatmoney/proof.py 2026-11-23 11:14 UTC with unchanged artifact; '
                      + m['fork_evidence'])
m['awaited_events'] = ('OrderAnnounced at 0x2326bb21b769d81e134c9b305ca156f989249fe7; '
                       'the live trial observed 15 since promotion and last sent on 2026-11-20 '
                       '(log ts 1795167632.86). Next announcement is not scheduled; safety poll 600 s.')
m['good_signs'] = ('send_result won; 13/13 trial sends won. Receipt status 1 and owner wallet gain. '
                   'Paper opportunities should simulate with a fresh Hermes update and report positive native gain.')
m['bad_signs'] = ('Hermes HTTP 401 after its trial key ends about 2026-12-02: no fresh Pyth update, '
                  'so the keeper cannot send for most orders. Two trial announcements were not takeable '
                  'after 12 attempts, with no winner; do not count them as lost sends. '
                  'Any lost send, price feed lag, or read-budget event needs review.')
m['executor_note'] += (' Reused unchanged trial artifact; reward is fixed per order, so no capital increase '
                       'or 2x/5x size claim. Local Hermes proxy depends on a trial key expiring about 2026-12-02.')
dst.write_text(yaml.safe_dump(m, sort_keys=False, allow_unicode=True, width=130))
bot = dst.parent / 'bot.py'
bot.write_text(bot.read_text().replace('"""Trial: Flat Money', '"""Graduation: Flat Money', 1))
