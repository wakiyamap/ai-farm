#!/usr/bin/env python3
"""Compare agent-installed event specifications with ledger cursor initialization.

Read-only: uses ledger query, never accesses the ledger database or RPC directly.
A cursor is an initialization signal, not evidence of complete historical coverage.
"""
import argparse
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]


def read_cursors():
    rows = []
    offset = 0
    while True:
        sql = (
            "SELECT source_id,chain,contract,next_block,verified FROM cursors "
            "WHERE source_id <> '' ORDER BY source_id,chain,contract "
            f"LIMIT 50 OFFSET {offset}"
        )
        result = subprocess.run(
            ['ledger', 'query', '--json', sql], check=True,
            capture_output=True, text=True,
        )
        page = [json.loads(line) for line in result.stdout.splitlines() if line.strip()]
        rows.extend(page)
        if len(page) < 50:
            return rows
        offset += 50
        if offset > 10000:
            raise RuntimeError('cursor count exceeds bounded 10000-row scan')


def coverage(specs, cursors):
    indexed = {(r['source_id'], r['chain'], r['contract'].lower()): r for r in cursors}
    output = []
    for spec in sorted(specs, key=lambda s: s['id']):
        for chain, configured in sorted(spec['chains'].items()):
            expected = {address.lower() for address in configured}
            present = {address: indexed[(spec['id'], chain, address)] for address in expected
                       if (spec['id'], chain, address) in indexed}
            heights = [r['next_block'] for r in present.values()]
            output.append({
                'source_id': spec['id'], 'chain': chain, 'configured': len(expected),
                'initialized': len(present),
                'verified': sum(bool(r['verified']) for r in present.values()),
                'missing': sorted(expected - present.keys()),
                'unverified': sorted(a for a, r in present.items() if not r['verified']),
                'min_next_block': min(heights) if heights else None,
                'max_next_block': max(heights) if heights else None,
            })
    return output


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', help='exact source id, default all agent-installed specs')
    parser.add_argument('--json', action='store_true', help='emit full JSON, including missing addresses')
    parser.add_argument('--spec-file', action='append', type=Path, default=[],
                        help='additional expected source spec JSON; read-only, does not install it')
    args = parser.parse_args()
    paths = sorted((ROOT / 'ledger/sources.d').glob('*.json')) + args.spec_file
    by_id = {}
    for path in paths:
        spec = json.loads(path.read_text())
        if spec['id'] in by_id and by_id[spec['id']] != spec:
            parser.error(f"conflicting expected specifications for {spec['id']}")
        by_id[spec['id']] = spec
    specs = list(by_id.values())
    if args.source:
        specs = [s for s in specs if s['id'] == args.source]
        if not specs:
            parser.error('no local specification has that source id; use --spec-file with its expected JSON spec')
    output = coverage(specs, read_cursors())
    if args.json:
        print(json.dumps(output, indent=2))
    else:
        print('source_id\tchain\tconfigured\tinitialized\tverified\tmin_next_block\tmax_next_block')
        for row in output:
            print('\t'.join(str(row[k]) for k in (
                'source_id', 'chain', 'configured', 'initialized', 'verified',
                'min_next_block', 'max_next_block')))
        print('Initialization only; no head or historical-completeness claim. Use --json for missing emitters.', file=sys.stderr)


if __name__ == '__main__':
    main()
