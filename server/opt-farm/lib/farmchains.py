"""Per-chain constants shared by gate-ctl, farm-signer and farm-watchdog (phase 10b; 10g adds elysium).

One table instead of a CHAIN_IDS / ETH_USD_FEED copy in each program. The USDC token addresses
stay in /etc/farm/gate.json ("usdc"); this file holds what the code needs to price and move them.

  feed        Chainlink Standard proxy for the chain's native token in USD (8 decimals). Not the
              SVR proxy: SVR is an OEV-recapture route that can lag. Addresses from data.chain.link
              (ethereum/base/arbitrum since phase 4, the rest copied by the human on 2026-11-10 and
              checked on chain by phase 10a: decimals 8, description, price).
  feed_chain  the chain the feed lives on, when it is not the chain itself (10g). Elysium's gas
              token is HYPE bridged 1:1 from HyperEVM, so it is priced with HyperEVM's HYPE / USD
              feed (human decision 2026-11-11). Pricing elysium therefore needs hyperevm readable.
  desc        accepted feed descriptions (Polygon's feed still says MATIC / USD after the rename)
  native      the gas token, for messages
  usdc_dec    decimals of the USDC configured in gate.json (BSC: Binance-Peg USDC, 18)
  price       plausible native/USD range; a reading outside it is refused (wrong feed or decimals)
  max_tx_gas  per-transaction gas the chain will actually include. HyperEVM small blocks take 2M
              gas; bigger transactions wait for big blocks only if the sender has opted in on
              HyperCore (evmUserModify usingBigBlocks), which farm keys never do.
  nitro       Arbitrum Nitro chains (Arbitrum One, Orbit chains such as elysium): the cost of posting
              to the parent chain is charged as extra gas, so a plain transfer needs MORE than
              21,000 gas (a hard-coded 21,000 fails with "intrinsic gas too low") and a token
              transfer more than on an L1. The gate estimates gas for its own transfers there (10g).
"""

CHAINS = {
    "ethereum": {"id": 1, "feed": "0x5f4eC3Df9cbd43714FE2740f5E3616155c5b8419", "desc": ("ETH / USD",),
                 "native": "ETH", "usdc_dec": 6, "price": (100, 100000)},
    "base": {"id": 8453, "feed": "0x71041dddad3595F9CEd3DcCFBe3D1F4b0a16Bb70", "desc": ("ETH / USD",),
             "native": "ETH", "usdc_dec": 6, "price": (100, 100000)},
    "arbitrum": {"id": 42161, "feed": "0x639Fe6ab55C921f74e7fac1ee960C0B6293ba612", "desc": ("ETH / USD",),
                 "native": "ETH", "usdc_dec": 6, "price": (100, 100000), "nitro": True},
    "bsc": {"id": 56, "feed": "0x0567F2323251f0Aab15c8dFb1967E4e8A7D42aeE", "desc": ("BNB / USD",),
            "native": "BNB", "usdc_dec": 18, "price": (10, 100000)},
    "polygon": {"id": 137, "feed": "0xAB594600376Ec9fD91F8e885dADF0CE036862dE0", "desc": ("POL / USD", "MATIC / USD"),
                "native": "POL", "usdc_dec": 6, "price": (0.001, 100)},
    "avalanche": {"id": 43114, "feed": "0x0A77230d17318075983913bC2145DB16C7366156", "desc": ("AVAX / USD",),
                  "native": "AVAX", "usdc_dec": 6, "price": (0.1, 10000)},
    "optimism": {"id": 10, "feed": "0x13e3Ee699D1909E989722E753853AE30b17e08c5", "desc": ("ETH / USD",),
                 "native": "ETH", "usdc_dec": 6, "price": (100, 100000)},
    "hyperevm": {"id": 999, "feed": "0xa5a72eF19F82A579431186402425593a559ed352", "desc": ("HYPE / USD",),
                 "native": "HYPE", "usdc_dec": 6, "price": (0.1, 100000), "max_tx_gas": 2_000_000},
    # Kinetiq's Elysium (Arbitrum Orbit, settles to HyperEVM, mainnet since 2026-11-09). HYPE is the
    # gas token; no Chainlink feed on the chain itself, so the HyperEVM HYPE / USD feed prices it.
    "elysium": {"id": 99901, "feed": "0xa5a72eF19F82A579431186402425593a559ed352", "feed_chain": "hyperevm",
                "desc": ("HYPE / USD",), "native": "HYPE", "usdc_dec": 6, "price": (0.1, 100000), "nitro": True},
}
# chains the farm had before phase 10: a feed problem there still stops the signer at start
CORE = ("ethereum", "base", "arbitrum")

CHAIN_IDS = {c: v["id"] for c, v in CHAINS.items()}
ETH_USD_FEED = {c: v["feed"] for c, v in CHAINS.items()}      # historical name: native/USD feed per chain


def usdc_scale(chain):
    """Raw USDC units per 1 USD on this chain (10**6, or 10**18 on BSC)."""
    return 10 ** CHAINS[chain]["usdc_dec"]


def price_ok(chain, price):
    lo, hi = CHAINS[chain]["price"]
    return lo < price < hi


def desc_ok(chain, desc):
    return desc in CHAINS[chain]["desc"]


def native(chain):
    return CHAINS[chain]["native"]


def max_tx_gas(chain):
    return CHAINS[chain].get("max_tx_gas", 3_000_000)


def feed_chain(chain):
    """The chain whose RPC serves this chain's native/USD feed (the chain itself, except elysium)."""
    return CHAINS[chain].get("feed_chain", chain)


def nitro(chain):
    """Arbitrum Nitro chain: gas for the gate's own transfers must be estimated, not assumed."""
    return bool(CHAINS[chain].get("nitro"))


def transfer_gas_budget(chain):
    """Gas to reserve for one native transfer when planning (the send itself estimates on Nitro)."""
    return 100_000 if nitro(chain) else 21_000


def usdc_gas_budget(chain):
    """Gas to reserve for one USDC transfer; on Nitro also the cap on the estimated limit."""
    return 300_000 if nitro(chain) else 90_000
