import hashlib
import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

root = Path('/srv/farm/ws')
run_id = '34931d202bf643759aef873e877ceff4'
names = sys.argv[1:]
for name in names:
    paper = root / 'bots/paper' / name
    if not paper.is_dir():
        print(json.dumps({'bot': name, 'status': 'no_paper_directory'}), flush=True)
        continue
    manifest = (paper / 'manifest.yaml').read_text()
    match = re.search(r'^executor: (.+)$', manifest, re.M)
    if not match:
        print(json.dumps({'bot': name, 'status': 'missing_executor'}), flush=True)
        continue
    artifact = root / match.group(1).strip().strip('"\'')
    source = artifact.parents[2] / 'src' / (artifact.stem + '.sol')
    review_path = paper / 'review.md'
    review = review_path.read_text()
    files = [paper / 'bot.py', paper / 'manifest.yaml', source]
    if any(not f.exists() or hashlib.sha256(f.read_bytes()).hexdigest() not in review for f in files):
        print(json.dumps({'bot': name, 'status': 'changed_or_unreviewed'}), flush=True)
        continue
    now = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')
    entry = (f'# Review {now} — promote (cheap-chain trial)\n\n'
             f'Decision: **promote — cheap-chain trial**. `next_review_at: null`. Reviewer run `{run_id}`.\n\n'
             'Prior independent technical approval and fork success/guard reproduction stand. Current bot, manifest and named executor source SHA-256 hashes match the reviewed hashes; `manifest-check.py --all` passes. '
             'Human decision `2026-11-18-trial-slots-20.md` raises the live trial limit to 20. At the session start, `gate status` showed 10 live `trial-*` bots, $1,041.59 total capital, no freeze. '
             'This promotion follows oldest technical approval first. The earlier review records paid entry, loss cap, CU/day, wallet return, and fork evidence.\n\n')
    review_path.write_text(entry + review)
    result = subprocess.run(['gate', 'promote', name], cwd=root, text=True, capture_output=True)
    output = result.stdout + result.stderr
    item = {'bot': name, 'exit': result.returncode, 'gate': output[-1200:]}
    live = root / 'bots/live' / name
    if live.is_dir():
        executor_file = live / 'state/executor.json'
        logs = live / 'logs/bot.jsonl'
        item['live_directory'] = True
        if executor_file.exists():
            data = json.loads(executor_file.read_text())
            addresses = [v.get('address', '').lower() for v in data.values() if isinstance(v, dict)]
            item['executor_addresses'] = addresses
            if logs.exists():
                starts = [json.loads(x) for x in logs.read_text().splitlines() if '"ev":"start"' in x and '"mode":"live"' in x]
                item['live_starts'] = [x.get('executor', '').lower() for x in starts[-2:]]
                item['address_match'] = bool(starts and starts[-1].get('executor', '').lower() in addresses)
    print(json.dumps(item), flush=True)
