import re
import subprocess
from pathlib import Path

adapter = Path('scratch/olive-adapter.js').read_text().split('arbitrum:')[0]
addresses = list(dict.fromkeys(re.findall(r'0x[a-fA-F0-9]{40}', adapter)))
for address in addresses:
    p = subprocess.run(['explorer', 'source', 'ethereum', address], capture_output=True, text=True)
    m = re.search(r'implementation (0x[a-fA-F0-9]{40})', p.stdout)
    print(address, m.group(1) if m else 'missing', flush=True)
