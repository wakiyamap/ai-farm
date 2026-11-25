from pathlib import Path
import shutil, json

root = Path('/srv/farm/ws')
src = root / 'scratch/trial-mycelium-upkeep-arbitrum'
dst = root / 'scratch/trial-mycelium-v2-arbitrum'
contract = dst / 'contracts'
(contract / 'src').mkdir(parents=True, exist_ok=True)
shutil.copy2(src / 'contracts/src/UpkeepTake.sol', contract / 'src/UpkeepTake.sol')
shutil.copy2(src / 'contracts/foundry.toml', contract / 'foundry.toml')
proof = (src / 'proof.py').read_text()
proof = proof.replace('trial-mycelium-upkeep-arbitrum', 'trial-mycelium-v2-arbitrum')
proof = proof.replace('0x759e817F0C40B11C775d1071D466B5fF5c6ce28e', '0x051AFD0B39aCf4cc52C76A479Ad802D0b82A8249')
proof = proof.replace('0x3a52ad74006d927e3471746d4eac73c9366974ee', '0x2bfb8aee6eb2dccd694f8ecb4c31fdebfc22b55a')
proof = proof.replace('525686742', '526410515').replace('1795110778', '1795318868')
proof = proof.replace('0x1f151cb390098e16d4b7fa26a90aa3628b3c0b69bdeff0d63c6a8dee316e2e8a', '0x4a3734f30e9c80f9e6ad36bd99292776e85ede656887e857bb5ab97273f8293d')
proof = proof.replace('0.812823 USDC.e', '0.552131 USDC.e')
proof = proof.replace('hourly', 'every 12 hours').replace('3600 s', '43200 s')
(dst / 'proof.py').write_text(proof)

bot = root / 'bots/paper/trial-mycelium-v2-arbitrum'
bot.mkdir(parents=True, exist_ok=True)
shutil.copy2(root / 'bots/live/trial-mycelium-upkeep-arbitrum/bot.py', bot / 'bot.py')
shutil.copy2(root / 'bots/live/trial-mycelium-upkeep-arbitrum/run.sh', bot / 'run.sh')
(bot / 'run.sh').chmod(0o755)
cfg = json.loads((root / 'bots/live/trial-mycelium-upkeep-arbitrum/config.json').read_text())
cfg['keeper'] = '0x051AFD0B39aCf4cc52C76A479Ad802D0b82A8249'
cfg['pool'] = '0x2bfb8aee6eb2dccd694f8ecb4c31fdebfc22b55a'
cfg['paper_sim_address'] = '0xb464f7314d55ec6a9a0cf6f7f6df17af8ed5b352'
(bot / 'config.json').write_text(json.dumps(cfg, indent=2) + '\n')
for sub in ('logs', 'state'):
    (bot / sub).mkdir(exist_ok=True)
