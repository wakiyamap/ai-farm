#!/usr/bin/env python3
"""Phase 10g: exact-text patches - elysium (chain id 99901) on the read side and the money path.

  patch-10g.py check <gate-ctl> <farm-signer> <farm-watchdog> <fork> <farm.nft> <common.md>
  patch-10g.py apply <gate-ctl> <farm-signer> <farm-watchdog> <fork> <farm.nft> <common.md> <outdir>

Every old text must occur exactly once, or nothing is written. Safe to re-run (markers).
"""
import os
import sys

GATE = [
("farmchains: feed_chain and the Nitro gas helpers",
r'''from farmchains import CHAIN_IDS, ETH_USD_FEED, CORE, usdc_scale, price_ok, native, max_tx_gas  # noqa: E402
''',
r'''from farmchains import CHAIN_IDS, ETH_USD_FEED, CORE, usdc_scale, price_ok, native, max_tx_gas  # noqa: E402
from farmchains import feed_chain, nitro, transfer_gas_budget, usdc_gas_budget  # noqa: E402  (10g)
''',
"from farmchains import feed_chain, nitro, transfer_gas_budget, usdc_gas_budget"),

("eth_usd: the feed is read on its own chain (elysium is priced on hyperevm)",
r'''            res = self.rpc.call(chain, "eth_call", [{"to": ETH_USD_FEED[chain], "data": farmkeys.selector("latestAnswer()")}, "latest"])
            price = int(res, 16) / 1e8
            if not price_ok(chain, price):
                die(f"implausible {native(chain)}/USD price {price} on {chain} (feed {ETH_USD_FEED[chain]})")
''',
r'''            res = self.rpc.call(feed_chain(chain), "eth_call", [{"to": ETH_USD_FEED[chain], "data": farmkeys.selector("latestAnswer()")}, "latest"])
            price = int(res, 16) / 1e8
            if not price_ok(chain, price):
                die(f"implausible {native(chain)}/USD price {price} on {chain} (feed {ETH_USD_FEED[chain]} on {feed_chain(chain)})")
''',
'self.rpc.call(feed_chain(chain), "eth_call", [{"to": ETH_USD_FEED[chain], "data": farmkeys.selector("latestAnswer()")}, "latest"])'),

("send_usdc: on Nitro chains the gas limit is estimated (capped), not a fixed 90,000",
r'''        data = farmkeys.encode_call("transfer(address,uint256)", to, raw_amount)
        gas = 90_000
''',
r'''        data = farmkeys.encode_call("transfer(address,uint256)", to, raw_amount)
        gas = 90_000
        if nitro(chain):
            # Nitro charges the parent-chain posting cost as gas: estimate, with headroom, within
            # the budget the callers reserve (10g)
            est = int(self.rpc.call(chain, "eth_estimateGas", [{"from": frm, "to": token, "data": data}]), 16)
            gas = min(int(est * 1.3), usdc_gas_budget(chain))
''',
"gas = min(int(est * 1.3), usdc_gas_budget(chain))"),

("transfer_gas(): 21,000, or an estimate on Nitro chains",
r'''    def send_eth(self, chain, label, to, value_wei, *, nonce=None, bump=1.0, fees=None):
        """Sign and broadcast a plain ETH transfer from the derived key `label`."""
''',
r'''    def transfer_gas(self, chain, frm, to, value_wei=0):
        """Gas limit for a plain native transfer. 21,000 everywhere except Arbitrum Nitro chains
        (arbitrum, elysium), where the parent-chain posting cost is charged as gas and a limit of
        21,000 is rejected as "intrinsic gas too low" (10g): estimated there, with 30% headroom."""
        if not nitro(chain):
            return 21000
        try:
            est = int(self.rpc.call(chain, "eth_estimateGas", [{"from": frm, "to": to, "value": hex(value_wei)}]), 16)
        except (RuntimeError, ValueError):
            # e.g. an emptied wallet the node will not estimate for: plan with the budget instead
            return transfer_gas_budget(chain)
        return int(est * 1.3)

    def send_eth(self, chain, label, to, value_wei, *, nonce=None, bump=1.0, fees=None, gas=None):
        """Sign and broadcast a plain ETH transfer from the derived key `label`."""
''',
"def transfer_gas(self, chain, frm, to, value_wei=0):"),

("send_eth: uses transfer_gas (or the limit the caller already budgeted)",
r'''        tx = {"chainId": CHAIN_IDS[chain], "nonce": nonce, "to": to, "value": value_wei, "data": "0x",
              "gas": 21000, "maxFeePerGas": max_fee, "maxPriorityFeePerGas": tip}
        raw = farmkeys.sign_eip1559(priv, tx)
        return self.rpc.call(chain, "eth_sendRawTransaction", ["0x" + raw.hex()]), 21000 * max_fee
''',
r'''        if gas is None:
            gas = self.transfer_gas(chain, frm, to, value_wei)
        tx = {"chainId": CHAIN_IDS[chain], "nonce": nonce, "to": to, "value": value_wei, "data": "0x",
              "gas": gas, "maxFeePerGas": max_fee, "maxPriorityFeePerGas": tip}
        raw = farmkeys.sign_eip1559(priv, tx)
        return self.rpc.call(chain, "eth_sendRawTransaction", ["0x" + raw.hex()]), gas * max_fee
''',
"gas = self.transfer_gas(chain, frm, to, value_wei)"),

("fund_reserve_wei: the reserve covers the chain's real transfer gas",
r'''        return max(10**15, (21000 + (90_000 if with_usdc else 0)) * self.fees(chain)[0] * 2)
''',
r'''        return max(10**15, (transfer_gas_budget(chain) + (usdc_gas_budget(chain) if with_usdc else 0)) * self.fees(chain)[0] * 2)
''',
"(transfer_gas_budget(chain) + (usdc_gas_budget(chain) if with_usdc else 0))"),

("sweep: the gas top-up for the USDC transfer uses the chain's budget",
r'''                need = 90_000 * fees[0] * (2 if chain != "ethereum" else 1) + 21000 * fees[0] * 2
                have = self.balance_wei(chain, bot_addr)
                if have < need:
                    # the bot ran its gas float down: top it up from the intermediate wallet and wait
                    topup = need - have + 21000 * fees[0]
''',
r'''                need = usdc_gas_budget(chain) * fees[0] * (2 if chain != "ethereum" else 1) + transfer_gas_budget(chain) * fees[0] * 2
                have = self.balance_wei(chain, bot_addr)
                if have < need:
                    # the bot ran its gas float down: top it up from the intermediate wallet and wait
                    topup = need - have + transfer_gas_budget(chain) * fees[0]
''',
"topup = need - have + transfer_gas_budget(chain) * fees[0]"),

("sweep: the native transfer reserves and signs the same gas limit",
r'''            cost = 21000 * fees[0] * (2 if chain != "ethereum" else 1)
''',
r'''            # one gas limit for both the reserve and the signed transfer: on Nitro chains it is an
            # estimate, and estimating twice could ask for more than was reserved (10g)
            sweep_gas = self.transfer_gas(chain, bot_addr, inter)
            cost = sweep_gas * fees[0] * (2 if chain != "ethereum" else 1)
''',
"sweep_gas = self.transfer_gas(chain, bot_addr, inter)"),

("sweep: the native transfer is sent with that limit",
r'''                h, _ = self.send_eth(chain, label, inter, bal - cost, nonce=n, fees=fees)
''',
r'''                h, _ = self.send_eth(chain, label, inter, bal - cost, nonce=n, fees=fees, gas=sweep_gas)
''',
"nonce=n, fees=fees, gas=sweep_gas)"),
]

SIGNER = [
("farmchains: feed_chain",
r'''from farmchains import CHAIN_IDS, ETH_USD_FEED, CORE, usdc_scale, price_ok, desc_ok, native, max_tx_gas  # noqa: E402
''',
r'''from farmchains import CHAIN_IDS, ETH_USD_FEED, CORE, usdc_scale, price_ok, desc_ok, native, max_tx_gas  # noqa: E402
from farmchains import feed_chain  # noqa: E402  (10g: elysium is priced with the feed on hyperevm)
''',
"from farmchains import feed_chain"),

("verify_feeds: decimals read on the feed's own chain",
r'''                dec = int(self.rpc.call(chain, "eth_call", [{"to": feed, "data": farmkeys.selector("decimals()")}, "latest"]), 16)
                raw = self.rpc.call(chain, "eth_call", [{"to": feed, "data": farmkeys.selector("description()")}, "latest"])
''',
r'''                dec = int(self.rpc.call(feed_chain(chain), "eth_call", [{"to": feed, "data": farmkeys.selector("decimals()")}, "latest"]), 16)
                raw = self.rpc.call(feed_chain(chain), "eth_call", [{"to": feed, "data": farmkeys.selector("description()")}, "latest"])
''',
'self.rpc.call(feed_chain(chain), "eth_call", [{"to": feed, "data": farmkeys.selector("description()")}, "latest"])'),

("eth_usd: price read on the feed's own chain",
r'''        res = self.rpc.call(chain, "eth_call", [{"to": ETH_USD_FEED[chain], "data": data}, "latest"], lane="live")
''',
r'''        res = self.rpc.call(feed_chain(chain), "eth_call", [{"to": ETH_USD_FEED[chain], "data": data}, "latest"], lane="live")
''',
'self.rpc.call(feed_chain(chain), "eth_call", [{"to": ETH_USD_FEED[chain], "data": data}, "latest"], lane="live")'),
]

WATCHDOG = [
("farmchains: feed_chain",
r'''from farmchains import CHAIN_IDS, ETH_USD_FEED, usdc_scale, price_ok  # noqa: E402
''',
r'''from farmchains import CHAIN_IDS, ETH_USD_FEED, usdc_scale, price_ok  # noqa: E402
from farmchains import feed_chain  # noqa: E402  (10g: elysium is priced with the feed on hyperevm)
''',
"from farmchains import feed_chain"),

("price read on the feed's own chain",
r'''                        price = int(rpc(url, chain, "eth_call", [{"to": ETH_USD_FEED[chain], "data": farmkeys.selector("latestAnswer()")}, "latest"]), 16) / 1e8
''',
r'''                        price = int(rpc(url, feed_chain(chain), "eth_call", [{"to": ETH_USD_FEED[chain], "data": farmkeys.selector("latestAnswer()")}, "latest"]), 16) / 1e8
''',
'rpc(url, feed_chain(chain), "eth_call"'),
]

FORK = [
("fork port 9009 for elysium",
r'''"bsc": 9004, "polygon": 9005, "avalanche": 9006, "optimism": 9007, "hyperevm": 9008}   # 10a
''',
r'''"bsc": 9004, "polygon": 9005, "avalanche": 9006, "optimism": 9007, "hyperevm": 9008,   # 10a
         "elysium": 9009}   # 10g
''',
'"elysium": 9009}'),
("help lists elysium",
r'''  (chains: base | arbitrum | ethereum | bsc | polygon | avalanche | optimism | hyperevm |
''',
r'''  (chains: base | arbitrum | ethereum | bsc | polygon | avalanche | optimism | hyperevm | elysium |
''',
"optimism | hyperevm | elysium |"),
]

NFT = [
("comment: fork ports 9001-9009",
"# 9001-9008 (fork nodes),",
"# 9001-9009 (fork nodes),",
"# 9001-9009 (fork nodes),"),
("earner may reach forks 9001-9009",
"8545, 9001-9008, 29483 }",
"8545, 9001-9009, 29483 }",
"8545, 9001-9009, 29483 }"),
("bots may reach forks 9001-9009",
"{ 53, 8545, 9001-9008 }",
"{ 53, 8545, 9001-9009 }",
"{ 53, 8545, 9001-9009 }"),
]

COMMON = [
("nine chains",
r'''OP Mainnet (10) and HyperEVM (999). Nothing is simulated or forked.''',
r'''OP Mainnet (10), HyperEVM (999) and Elysium (99901). Nothing is simulated or forked.''',
"HyperEVM (999) and Elysium (99901)"),
("farm name elysium, and what is different there",
r'''`optimism`, `hyperevm`. The last five were added on 2026-11-10''',
r'''`optimism`, `hyperevm`, `elysium`. **Elysium** (added 2026-11-11) is Kinetiq's Arbitrum Orbit chain that settles to HyperEVM; its mainnet opened on 2026-11-09, so almost everything on it is days old. Reads, the ledger, the KB, the fork and the gate, signer and watchdog work there like on the others; a promotion needs HYPE (and USDC, if the manifest asks for principal) in the intermediate wallet on elysium. What bites there: the gas token is **HYPE** (bridged 1:1 from HyperEVM) and the farm prices it with HyperEVM's HYPE / USD feed, so elysium cannot be priced while HyperEVM is unreadable; blocks come every **100-200 ms**, so a bot that polls every block burns relay quota about 100 times faster than on Ethereum - poll on a timer you can justify and say what it costs per day; it is an **Arbitrum Nitro** chain, where a plain transfer needs more than 21,000 gas and every gas limit must come from `eth_estimateGas`, never from a constant; Alchemy may not serve `debug_*` / `trace_*` there; USDC is `0xb47c4C8F73F009CC0C0d3f92B388d13E293F0B65` (6 decimals); contract addresses come only from the protocol's own docs or the chain's explorer (elysium.kinetiq.xyz/explorer), and a token or pool that is days old can be gone tomorrow - measure liquidity before you count on it. Another, older chain is also called Elysium (Vulcan Forged, chain ids 1338 / 1339): not this one. The five before it (`bsc` to `hyperevm`) were added on 2026-11-10''',
"`optimism`, `hyperevm`, `elysium`."),
]

FILES = [("gate-ctl", GATE), ("farm-signer", SIGNER), ("farm-watchdog", WATCHDOG), ("fork", FORK),
         ("farm.nft", NFT), ("common.md", COMMON)]


def patch(text, hunks, name):
    for title, old, new, marker in hunks:
        if marker in text:
            print(f"  {name}: already applied: {title}")
            continue
        n = text.count(old)
        if n != 1:
            raise SystemExit(f"{name}: cannot apply '{title}': old text found {n} times (expected 1); "
                             "nothing was changed")
        text = text.replace(old, new)
        print(f"  {name}: applied: {title}")
    return text


def main(argv):
    if len(argv) == 7 and argv[0] == "check":
        out = None
    elif len(argv) == 8 and argv[0] == "apply":
        out = argv[7]
    else:
        sys.exit(__doc__)
    results = []
    for path, (name, hunks) in zip(argv[1:7], FILES):
        with open(path, encoding="utf-8") as f:
            results.append((name, patch(f.read(), hunks, name)))
    if out:
        for name, text in results:
            with open(os.path.join(out, name), "w", encoding="utf-8") as f:
                f.write(text)


if __name__ == "__main__":
    main(sys.argv[1:])
