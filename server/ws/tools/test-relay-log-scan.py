"""Offline provider-limit and completeness regressions; no chain requests."""
import importlib.util
from pathlib import Path
import unittest

spec = importlib.util.spec_from_file_location('scanner', Path(__file__).with_name('relay-log-scan.py'))
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)
ADDRESSES = ['0x%040x' % i for i in range(1, 66)]


def provider(query):
    addresses = query['address']
    if len(addresses) > 32:
        return {'error': {'message': 'invalid argument: address array limit 32'}}
    return {'result': [dict(address=a, blockNumber=hex(n), blockHash=hex(n),
                            transactionHash=a, transactionIndex=hex(i), logIndex='0x0')
                       for n in range(int(query['fromBlock'], 16), int(query['toBlock'], 16) + 1)
                       for i, a in enumerate(addresses)]}


class Tests(unittest.TestCase):
    def test_complete_address_and_block_product(self):
        logs, audit = m.scan({'address': ADDRESSES}, 10, 13, provider, page_blocks=2)
        self.assertEqual(len(logs), 260)
        self.assertEqual(len(audit), 6)
        self.assertEqual([len(a['address']) for a in audit], [32, 32, 1] * 2)
        self.assertEqual({(x['address'], int(x['blockNumber'], 16)) for x in logs},
                         {(a, n) for a in ADDRESSES for n in range(10, 14)})

    def test_one_budget_for_all_batches(self):
        with self.assertRaises(m.ScanError) as ctx:
            m.scan({'address': ADDRESSES}, 10, 13, provider, page_blocks=2, max_requests=5)
        self.assertIn('budget exhausted', str(ctx.exception))
        self.assertEqual(len(ctx.exception.audit), 5)

    def test_size_split_preserves_address_batch(self):
        def limited(query):
            if query['fromBlock'] != query['toBlock']:
                return {'error': {'message': 'max results'}}
            return provider(query)
        logs, audit = m.scan({'address': ADDRESSES}, 10, 11, limited)
        self.assertEqual(len(logs), 130)
        self.assertEqual(len(audit), 9)
        self.assertTrue(all(len(a['address']) <= 32 for a in audit))

    def test_duplicates_and_validation(self):
        a = '0x' + 'ab' * 20
        self.assertEqual(m.address_batches({'address': [a, '0x' + 'AB' * 20]}),
                         [{'address': [a]}])
        for bad in [[], None, '0x1234', ['0x' + 'z' * 40], [None], {}]:
            with self.subTest(bad=bad), self.assertRaises(m.ScanError):
                m.address_batches({'address': bad})

    def test_transient_retries_only_current_batch(self):
        calls = []
        def flaky(query):
            calls.append(query)
            if len(calls) == 2:
                return {'error': {'message': 'HTTP 429'}}
            return provider(query)
        logs, audit = m.scan({'address': ADDRESSES}, 10, 10, flaky, sleep=lambda _: None)
        self.assertEqual(len(logs), 65)
        self.assertEqual(len(audit), 4)
        self.assertEqual(calls[1], calls[2])

    def test_lower_provider_address_limit(self):
        def limited(query):
            if len(query['address']) > 10:
                return {'error': {'message': 'all providers failed: A maximum of 10 addresses is allowed'}}
            return provider(query)
        logs, audit = m.scan({'address': ADDRESSES[:20]}, 10, 11, limited)
        self.assertEqual(len(audit), 3)
        self.assertEqual({(x['address'], int(x['blockNumber'], 16)) for x in logs},
                         {(a, n) for a in ADDRESSES[:20] for n in (10, 11)})

    def test_provider_rejects_arrays_including_singleton(self):
        def scalar_only(query):
            if isinstance(query['address'], list):
                return {'error': {'message': 'invalid type: untagged enum Variadic'}}
            return provider(dict(query, address=[query['address']]))
        logs, audit = m.scan({'address': ADDRESSES[:2]}, 10, 10, scalar_only)
        self.assertEqual(len(logs), 2)
        self.assertEqual(len(audit), 5)
        self.assertEqual([r['address'] for r in audit if r['error'] is None], ADDRESSES[:2])

    def test_address_split_obeys_shared_request_budget(self):
        def limited(query):
            return {'error': {'message': 'A maximum of 1 address is allowed'}}
        with self.assertRaises(m.ScanError) as ctx:
            m.scan({'address': ADDRESSES[:20]}, 10, 10, limited, max_requests=3)
        self.assertIn('budget exhausted', str(ctx.exception))
        self.assertEqual(len(ctx.exception.audit), 3)

    def test_scalar_address_limit_is_terminal(self):
        with self.assertRaises(m.ScanError) as ctx:
            m.scan({'address': ADDRESSES[0]}, 10, 10,
                   lambda _: {'error': {'message': 'A maximum of 0 addresses is allowed'}},
                   sleep=lambda _: None)
        self.assertEqual(len(ctx.exception.audit), 1)


if __name__ == '__main__':
    unittest.main()
