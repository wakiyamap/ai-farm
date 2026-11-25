#!/usr/bin/env python3
"""Bounded research-only log export; no partial output is published on failure."""
import argparse
import json
import os
from pathlib import Path
import re
import sys
import time
import urllib.error
import urllib.request


class ScanError(Exception):
    pass


def address_batches(filter_):
    """Bound address arrays to the farm's 32-address provider policy."""
    if 'address' not in filter_:
        return [filter_]
    value = filter_['address']
    addresses = value if isinstance(value, list) else [value]
    if not addresses:
        raise ScanError('address list must not be empty')
    unique = {}
    for address in addresses:
        if not (isinstance(address, str) and len(address) == 42
                and address.startswith('0x')
                and all(c in '0123456789abcdefABCDEF' for c in address[2:])):
            raise ScanError('address must be 0x + 40 hex characters')
        unique.setdefault(address.lower(), address)
    addresses = list(unique.values())
    if not isinstance(value, list):
        return [filter_]
    return [dict(filter_, address=addresses[i:i + 32])
            for i in range(0, len(addresses), 32)]


def scan(filter_, start, end, request, max_requests=64, retries=2, sleep=time.sleep,
         page_blocks=2000):
    """Split explicit address/size limits; retry availability errors without fanout."""
    audit, logs = [], []

    def visit(batch, lo, hi):
        for attempt in range(retries + 1):
            if len(audit) >= max_requests:
                raise ScanError('request budget exhausted; no complete export')
            query = dict(batch, fromBlock=hex(lo), toBlock=hex(hi))
            t = time.monotonic()
            response = request(query)
            error = response.get('error')
            audit.append({'from': lo, 'to': hi, 'seconds': round(time.monotonic()-t, 3),
                          'address': batch.get('address'),
                          'error': error, 'count': len(response['result'])
                          if isinstance(response.get('result'), list) else None})
            if error is None:
                result = response.get('result')
                if not isinstance(result, list):
                    raise ScanError('malformed result; no complete export')
                for log in result:
                    if log.get('removed') or not lo <= int(log['blockNumber'], 16) <= hi:
                        raise ScanError('removed or out-of-range log; retry a stable range')
                logs.extend(result)
                return
            message = str(error).lower()
            addresses = batch.get('address')
            address_limit = (re.search(r'(?:maximum of|at most)\s+\d+\s+address(?:es)?\b', message)
                             or any(s in message for s in (
                                 'address array limit', 'too many addresses', 'max addresses')))
            array_rejected = 'untagged enum variadic' in message
            if isinstance(addresses, list) and (address_limit or array_rejected):
                if len(addresses) == 1:
                    # Some public providers accept an address string only.
                    visit(dict(batch, address=addresses[0]), lo, hi)
                else:
                    mid = len(addresses) // 2
                    visit(dict(batch, address=addresses[:mid]), lo, hi)
                    visit(dict(batch, address=addresses[mid:]), lo, hi)
                return
            size_error = any(s in message for s in (
                'max results', 'too many results', 'response size',
                'block range', 'query returned more', 'limit the query',
                # Observed relay JSON truncation on a dense cbBTC log page.
                'unterminated string'))
            if size_error:
                if lo == hi:
                    raise ScanError('single-block size limit; narrow address/topics')
                mid = (lo + hi) // 2
                visit(batch, lo, mid)
                visit(batch, mid + 1, hi)
                return
            transient = any(s in message for s in (
                '429', '503', '502', '504', 'timeout', 'timed out',
                'no provider available', 'all providers failed', 'rate limit'))
            if not transient or attempt == retries:
                raise ScanError('RPC failure: ' + str(error))
            sleep(2 ** attempt)

    try:
        batches = address_batches(filter_)
        for lo in range(start, end + 1, page_blocks):
            for batch in batches:
                visit(batch, lo, min(lo + page_blocks - 1, end))
        unique = {}
        for log in logs:
            key = (log['blockHash'], log['transactionHash'], log['logIndex'])
            if key in unique and unique[key] != log:
                raise ScanError('inconsistent duplicate log')
            unique[key] = log
        result = sorted(unique.values(), key=lambda x: (
            int(x['blockNumber'], 16), int(x['transactionIndex'], 16), int(x['logIndex'], 16)))
        return result, audit
    except Exception as exc:
        exc.audit = audit
        raise


def check_topics(topics, keep_trailing_nulls=False):
    """Reject filters that silently match nothing (wiki pitfalls/relay-getlogs-invalid-params.md 3, 5, 6)."""
    if not isinstance(topics, list) or len(topics) > 4:
        return 'topics must be a list of at most 4 entries'
    for i, entry in enumerate(topics):
        for t in (entry if isinstance(entry, list) else [entry]):
            if t is None and not isinstance(entry, list):
                continue
            if not (isinstance(t, str) and len(t) == 66 and t[:2] == '0x'
                    and all(c in '0123456789abcdefABCDEF' for c in t[2:])):
                return ('topics[%d] %r is not a 32-byte hash (0x + 64 hex); build it with '
                        'cast keccak "Event(types)", never from a 4-byte selector' % (i, t))
    if topics and topics[-1] is None and not keep_trailing_nulls:
        return ('trailing null topics require the log to have that many topics and silently match '
                'nothing for shorter events (ERC-20 Transfer has 3); drop them, or pass '
                '--keep-trailing-nulls if that length filter is intended')
    return None


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--chain', choices=['base', 'arbitrum', 'ethereum', 'bsc', 'polygon', 'avalanche', 'optimism', 'hyperevm', 'elysium'], required=True)
    ap.add_argument('--filter', type=Path, required=True, help='JSON address/topics filter')
    ap.add_argument('--from-block', type=int, required=True)
    ap.add_argument('--to-block', type=int, required=True)
    ap.add_argument('--max-requests', type=int, default=64)
    ap.add_argument('--page-blocks', type=int, default=2000, help='initial page size; shrinks on size errors')
    ap.add_argument('--keep-trailing-nulls', action='store_true',
                    help='send trailing null topics (only to require >=N topics, e.g. ERC-721 vs ERC-20 Transfer)')
    ap.add_argument('--output', type=Path, required=True, help='new file; must not exist')
    ap.add_argument('--audit', type=Path, required=True, help='new file; must not exist')
    args = ap.parse_args()
    if args.from_block < 0 or args.to_block < args.from_block or args.max_requests < 1 or args.page_blocks < 1:
        ap.error('invalid range or request budget')
    if args.output == args.audit or args.output.exists() or args.audit.exists():
        ap.error('output and audit must be distinct new files')
    filter_ = json.loads(args.filter.read_text())
    if not isinstance(filter_, dict) or set(filter_) - {'address', 'topics', 'fromBlock', 'toBlock'}:
        ap.error('filter accepts only address/topics and optional replaced numeric range')
    if not filter_.get('address') or not filter_.get('topics'):
        ap.error('address and topics required to bound query volume')
    topic_error = check_topics(filter_['topics'], args.keep_trailing_nulls)
    if topic_error:
        ap.error(topic_error)
    try:
        address_batches(filter_)
    except ScanError as exc:
        ap.error(str(exc))
    relay = os.environ['RPC_RELAY_URL'].rstrip('/')

    def request(query):
        payload = {'jsonrpc': '2.0', 'id': 1, 'method': 'eth_getLogs', 'params': [query]}
        req = urllib.request.Request(relay+'/'+args.chain+'?lane=research',
            data=json.dumps(payload).encode(), headers={'content-type': 'application/json'})
        try:
            with urllib.request.urlopen(req, timeout=25) as response:
                return json.load(response)
        except (urllib.error.URLError, TimeoutError) as exc:
            return {'error': {'message': str(exc)}}

    try:
        result, audit = scan(filter_, args.from_block, args.to_block, request, args.max_requests,
                             page_blocks=args.page_blocks)
    except Exception as exc:
        with args.audit.open('x') as f:
            json.dump({'complete': False, 'error': str(exc), 'requests': getattr(exc, 'audit', [])}, f, indent=2)
        print(str(exc), file=sys.stderr)
        return 1
    with args.output.open('x') as f:
        json.dump(result, f)
    with args.audit.open('x') as f:
        json.dump({'complete': True, 'logs': len(result), 'requests': audit}, f, indent=2)
    print(json.dumps({'complete': True, 'logs': len(result), 'requests': len(audit)}))
    return 0


if __name__ == '__main__':
    sys.exit(main())
