import datetime
import json
import pathlib
import subprocess
import time

root = pathlib.Path('/srv/farm/ws')
order = [
    'trial-gmx-buyback-avalanche',
    'trial-fli-arb-polygon',
    'trial-peapods-arb-base',
    'trial-peapods-arb-arbitrum',
    'trial-gmx-buyback-slow-arbitrum',
    'trial-aave2-polygon',
    'trial-euler-bsc',
    'trial-dolomite-arbitrum',
    'trial-felix-liq-hyperevm',
    'trial-llamalend-arbitrum',
    'trial-fluid-polygon',
    'trial-peapods-base',
    'trial-kinza-bsc',
    'trial-metronome-liq-base',
]

def command(*args):
    return subprocess.run(args, cwd=root, text=True, capture_output=True, timeout=180)

for bot in order:
    paper = root / 'bots/paper' / bot
    review = paper / 'review.md'
    if not review.exists() or 'parked: approved' not in review.read_text()[:500]:
        print(bot, 'SKIP: no parked approval', flush=True)
        continue
    status = command('gate', 'status')
    if status.returncode:
        print(bot, 'STATUS ERROR:', status.stderr[-400:], flush=True)
        break
    gate = json.loads(status.stdout)
    live_trials = [x for x in gate['live'] if x.startswith('trial-')]
    if len(live_trials) >= 45:
        print(bot, 'WAIT: 45 slots full', flush=True)
        break
    if gate['frozen'] or gate['halted']:
        print(bot, 'WAIT: gate frozen or halted', flush=True)
        break
    old = review.read_text()
    first = (f'**Decision: promote** — cheap-chain trial; prior technical approval stands. '
             f'2026-11-20-trial-slots-45.md opened capacity; {len(live_trials)}/45 live before this promote. '
             f'Gate status: capital ${gate["capital_usd"]}, daily loss ${gate["daily_loss_usd"]}; '
             f'not frozen. next_review_at: none.\n\n')
    review.write_text(first + old)
    result = command('gate', 'promote', bot)
    print(bot, 'PROMOTE', result.returncode, (result.stdout + result.stderr)[-650:].strip(), flush=True)
    if result.returncode:
        if review.exists():
            now = datetime.datetime.now(datetime.timezone.utc)
            at = (now + datetime.timedelta(hours=2)).strftime('%Y-%m-%dT%H:%M:%SZ')
            review.write_text(f'**Decision: wait** — gate promote refused: {(result.stdout + result.stderr)[-350:].strip()}; next_review_at: {at}.\n\n' + review.read_text())
        continue
    live = root / 'bots/live' / bot
    state = live / 'state/executor.json'
    data = json.loads(state.read_text()) if state.exists() else {}
    addresses = [v.get('address', '').lower() for v in data.values() if isinstance(v, dict)]
    start = ''
    for _ in range(5):
        logfile = live / 'logs/bot.jsonl'
        if logfile.exists():
            lines = logfile.read_text().splitlines()
            starts = [line for line in lines[-25:] if '"ev":"start"' in line and '"mode":"live"' in line]
            if starts:
                start = starts[-1]
                break
        time.sleep(2)
    match = bool(start and any(address in start.lower() for address in addresses))
    print(bot, 'ADDRESS_MATCH', match, 'executor', addresses, 'start', start[:300], flush=True)
