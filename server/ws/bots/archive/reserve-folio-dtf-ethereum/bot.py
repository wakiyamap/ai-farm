#!/usr/bin/env python3
"""Reserve Folio (DTF) rebalance Dutch auction bot (lead 91, earner finish 2026-11-08).

Events pinned from the DEPLOYED folio source (logs fetched via relay, positive controls):
  AuctionOpened(uint256 indexed rebalanceNonce, uint256 indexed auctionId, address[] tokens,
      WeightRange[] weights, PriceRange[] prices, RebalanceLimits limits, uint256 startTime, uint256 endTime)
    topic0 0x24c9d9f1ca3e1d57b1fe4445280ced7eb621e75b079f2b23ec634a1072c92e24 (keccak, matches log at block 26306803)
  AuctionBid(uint256 indexed auctionId, address indexed sellToken, address indexed buyToken,
      uint256 sellAmount, uint256 buyAmount)  # per-bid: sellAmount/buyAmount on sale at the bid's block price
    topic0 0x8eda72ced8404ff0ffda416826fcbaed9d7326fbbc62f3bfbfb3b048f8bfe481 (measured 15 logs blocks 26306916-33)
Prices in AuctionOpened are D27{UoA/tok} with UoA in 1e-6 USD: token USD price = raw / 1e21
(measured: auction 9 CSCO low 95851250000000000000 = 95.85125 USD, MRVEL low 67.4575 USD - attempt 549).
Dutch decay: getBid(auctionId,sell,buy,maxSell) -> (sellAmount,bidAmount,price D27{buyTok/sellTok}),
price decays exp from sellHigh/buyLow to sellLow/buyHigh over [startTime,endTime], k = ln(256)/1800s -> no
same-block race (precomputable). Bot bids the remaining size at frac >= BID_FRAC with corridor-low USD anchors.
Paper mode (v6, review 2026-11-09T01:15Z blocker 2: PAPER NEVER TOUCHES THE KEY): the executor
fundSwapAndBid (v6: the MANDATORY USDC->buyToken funding leg pays for this bid's payment inventory
inside the same tx + the venue sell leg + the bid + the owner payout in ONE guarded call) is
simulated with a MockUsdcVenue stand-in on the local fork paying the auction's own corridor-anchor
values (NO key-gated HTTP in paper: state/fusion_key.json is read ONLY on the live path). Live mode:
signer sends the same calldata with the key-gated 1inch Fusion quote legs (endpoint 401 keyless,
attempts 563/564 + scratch/dtf96-401.txt 2026-11-08); without the key every LIVE venue path fails
closed (no send, no fake legs)."""
import json, os, time, urllib.request, urllib.parse, subprocess

FOLIOS = [  # all 28 Folios deployed on Ethereum: FolioDeployed logs on deployers 0xBE3B47587cEeff7D48008A0114f51cD571beC63A/0x4d201a6e5bf975e2cee9e5cbdfc803c0ff122073 (scratch/dtf-folios.json, attempt 546)
 # auctions open on ANY folio (measured: aid 4 opened 2026-11-06 on 0xe592f69e..., which is not in the old 6-folio list)
 "0x9ac93e97928e98a9e8544c1c58be2fbf28a4a22e","0xffc240217bf5b962aac2f4c487285d1409135441","0xe5e394c25a8dcc70b38c2f3c3bb6c5629f07c3fc",
 "0x3fe46c4a4817babc3e9db883fbdf3ccfac47d195","0xcdd9290626ef3296a7e0d32e1d724716b09bdf5d","0xe4a10951f962e6cb93cb843a4ef05d2f99db1f94",
 "0x60105cbd0499199ca84f63ee9198b2a2d5441699","0x4821cac79a6e3747877971d1dc8c75c5c48c2d7f","0xaeb4d85c342c46fe269572f484731542f5e47e56",
 "0x8ec5ac6ece088e650f80a48b8ab0bd9d2ccc914c","0x1d55940cf6eb85321816327aa785006f8dd59ef9","0x08ac8276b5844edd42a710c950b41770a6d61468",
 "0x920527c101ba7b4ab2905be87a6ea6b74d690273","0xe592f69e4f60e9a78dba0043573b898386c01cb8","0x33b44bb8ad29e863cf44e77c010de6795cd19bf7",
 "0x7b7374b163d71a7aa964d06cd3712a5e6942886e","0x6e39a076966f91e7b726e979578ceaaa1aaf5659","0x2cf4dafc17e163abd6770e1794e1ad10deb7d32e",
 "0x9f4535b8eff872ae8f6cad4486ae3f310903c69a","0x5039ece83dc4e0621ebec391128339bd859a84d0","0x1ec1d815488936ec8add5cb76ac4563ceef09de3",
 "0x09a823930fab5b1fda6e519b1ee33e7da9bda0e5","0x3ce752a0eb838084562c9d7a0e1df24a8ae9542d","0x9429a7332b5a3bcde2781b65ac1a9ebd9f466e12",
 "0xb394c76a9404b7eb65841e1551952b97aae7fd5c","0x9befcdddc831198d5805c1690a2fd3bbd587845e","0x8fc660a20b55be94e7ded6f47f8e17a2c7813383",
 "0xe5baa8f8f21e2ceef150be49a7d62ec3f85faf5e"]
OPENED_T0 = "0x24c9d9f1ca3e1d57b1fe4445280ced7eb621e75b079f2b23ec634a1072c92e24"  # AuctionOpened(...) 2 indexed
BID_T0    = "0x8eda72ced8404ff0ffda416826fcbaed9d7326fbbc62f3bfbfb3b048f8bfe481"  # AuctionBid(aid,sell,buy,sellAmt,buyAmt)
USDC = "0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48"
USDC_HOLDER = "0x98c23e9d8f34fefb1b7bd6a91b7ff122f4e16f5c"  # holds >90 MM USDC (measured 26306742, proof.sh)
FROM = "0x15d34a28964846f4f3a393caa6c0a934e7e2d5e4"          # anvil default account (fork gas principal for sim)
# venue pinned from the winner fill trace (attempt 563): Swapper.swap(Order,bytes) pulls sellToken from
# msg.sender and the AGV vault pays buyToken to the Order's taker = the executor; quote blobs are taker-bound.
SWAPPER = "0x6131b5fae19ea4f9d964eac0408e4408b66337b5"
# hardened v3 (review 2026-11-08T17:33Z): constructor(address swapper, address folioA, address folioB);
# pinned venue + the two folios with measured recent opens (aid 8-10 / aid 4); owner extends with setFolio.
CARGS  = "0x0000000000000000000000006131b5fae19ea4f9d964eac0408e4408b66337b50000000000000000000000002cf4dafc17e163abd6770e1794e1ad10deb7d32e000000000000000000000000e592f69e4f60e9a78dba0043573b898386c01cb8"  # scratch/dtf97-constructor-args.txt
PIN_SEL, SETFOLIO_SEL = "5af6c810", "e127d7b0"  # allowedFolio(address), setFolio(address,bool) (cast sig 2026-11-08)
FUSION_URL = "https://api.1inch.com/v1.1/1/fusion-v1/swap"  # key-gated: 401 keyless (attempt 563, scratch/dtf96-401.txt)
# selectors pinned via cast keccak (OpenChain-checked; getBid/bid pinned in proof attempt 550)
GETBID_SEL = "76990dcd"   # getBid(uint256,address,address,uint256) -> (sellAmount,bidAmount,price)
V3_SEL     = "16747cd5"   # FolioBidV3.bidWithLegs(address,uint256,address,address,uint256,uint256,address,bytes,bytes,uint256) (cast sig 2026-11-08, run 38ad2623)
FUND_SEL   = "07d0273c"   # FolioBidV3.fundSwap(address,address,uint256,uint256,address,bytes) (cast sig 2026-11-08, proven funding leg; folded into FSB for the live route)
FSB_SEL    = "7cda801a"   # FolioBidV3.fundSwapAndBid(address,uint256,address,address,uint256,uint256,uint256,uint256,bytes,bytes,bytes,uint256) (cast keccak + cast sig 2026-11-08T21:0xZ): ONE atomic guarded transaction for the live route (review 2026-11-08T20:45Z blocker 2): funding swap + bid + owner payout in one contract call, revert rolls the funding leg back
BAL_SEL    = "0x70a08231" # balanceOf(address)
LRD_SEL    = "feaf968c"   # Chainlink latestRoundData() -> (roundId,answer(int224),startedAt,updatedAt,participants)
FLINK_ETHUSD = "0x5f4ec3df9cbd43714fe2740f5e3616155c5b8419"  # Chainlink ETH/USD, decimals 8 (verified via relay 2026-11-08)
MAX_LOSS_USD = 15.0       # manifest max_loss_per_tx_usd: worst case = the signed gas cap x maxFee at the fresh signing-time price. The live send fails closed if gas x maxFee exceeds this (principal stays in the contract on a revert; only gas is at risk)
GAS_LIVE     = 900000     # executor fundSwapAndBid gas upper bound (fork-measured v6 funded mock success gasUsed 866908, proof8 tx 0x4f8e9aadd86ca1bd5cea622ffa08b2d677f0689aa744484a2df5246b3ebfc6f4, scratch/dtf95-proof/proof8.json 2026-11-09 - the v5 proof7 gasUsed was 820946; live_fee_bound fails closed if GAS_LIVE x maxFee exceeds MAX_LOSS_USD)
FEE_TIP      = 1_000_000_000  # 1 gwei priority tip headroom for inclusion (the network base fee is ~0.04 gwei now)
RELAY = os.environ.get("RPC_RELAY_URL", "") + "/ethereum?lane=" + os.environ.get("RPC_LANE", "paper")
# paper@.service sets no FORK_URL_ETHEREUM; the local fork daemon is farm infrastructure at a fixed localhost port
FORK = os.environ.get("FORK_URL_ETHEREUM") or "http://127.0.0.1:9003"
MODE = os.environ.get("BOT_MODE", "paper")
POLL = 15
BID_FRAC = 0.55          # Dutch: bid after 55% of the window (margin turns positive ~50% with these anchors)
SIZE_USD = 90            # per-bid cost cap in USD at corridor-low buy price (principal 100 USDC)
STATEF = "state/state.json"

def rpc(url, method, params):
    body = {"jsonrpc":"2.0","id":1,"method":method,"params":params}
    req = urllib.request.Request(url, data=json.dumps(body).encode(), headers={"content-type":"application/json"})
    d = json.loads(urllib.request.urlopen(req, timeout=30).read())
    if "error" in d: raise RuntimeError(str(d["error"]))
    return d["result"]
def h(x): return int(x, 16)
def w(v): return hex(v)[2:].zfill(64)
def addr_word(a): return w(int(a, 16))
def call(to, data, url=None):
    return rpc(url or RELAY, "eth_call", [{"to":to,"data":data}, "latest"])
def enc(sel, words): return "0x"+sel+"".join(x.zfill(64) for x in words)
def getbid(folio, aid, sell, buy, max_sell):
    r = call(folio, enc(GETBID_SEL, [w(aid), sell[2:], buy[2:], w(max_sell)]))
    return h(r[2:66]), h(r[66:130]), h(r[130:194])  # sellAmount, bidAmount, price D27{buyTok/sellTok}
DEC = {}
def tok_dec(token):  # token decimals via relay, cached (measured: sell shares 18-dec raw, buy shares 15-dec raw)
    if token not in DEC:
        try: DEC[token] = h(call(token, "0xed42881a"))  # decimals()
        except Exception: DEC[token] = None
    return DEC[token]
def dec_opened(data):
    """decode AuctionOpened non-indexed data: header 8 slots (ptr tokens, ptr weights, ptr prices,
    limits.low/spot/high, startTime, endTime) then dynamic arrays."""
    words = [data[2+i:i+66] for i in range(0, len(data)-2, 64)]
    tok_off = int(words[0], 16) // 32; ntok = int(words[tok_off], 16)  # pointers are byte offsets
    toks = ["0x"+words[tok_off+1+i][24:] for i in range(ntok)]  # last 40 hex chars = address
    poff = int(words[2], 16) // 32; np = int(words[poff], 16)  # prices: 2 words/item (low, high)
    prices = [(int(words[poff+1+2*i],16), int(words[poff+2+2*i],16)) for i in range(np)]
    start, end = int(words[6],16), int(words[7],16)
    return toks, prices, start, end
def fork_call(to, data):
    try: return rpc(FORK, "eth_call", [{"to":to,"data":data}, "latest"])
    except Exception as e: return None
def bal(token, who):
    r = fork_call(token, "0x70a08231"+addr_word(who))
    return 0 if (r is None or r == "0x") else h(r)
def live_fee_bound():
    """Bound the live send's worst-case gas loss to MAX_LOSS_USD at the FRESH signing-time ETH/USD price:
    read the live base fee + a small tip as maxFeePerGas, value GAS_LIVE x maxFee at the Chainlink feed,
    and return None (fail closed -> no send) if that USD cost exceeds MAX_LOSS_USD. Returns (max_fee, cost_usd)."""
    blk = rpc(RELAY, "eth_getBlockByNumber", ["latest", False])
    if not blk or blk.get("baseFeePerGas") is None: return None
    basefee = h(blk["baseFeePerGas"])
    max_fee = basefee * 9 // 8 + FEE_TIP  # 12.5% headroom over the live base fee + priority tip (EIP-1559 inclusion)
    ans = h(call(FLINK_ETHUSD, "0x"+LRD_SEL)[2+64:2+128])  # answer word (int224, positive here) at 8 decimals
    if ans <= 0: return None
    eth_usd = ans / 1e8
    cost_usd = GAS_LIVE * max_fee / 1e18 * eth_usd  # worst-case gas cost in USD at the signing-time price
    if cost_usd > MAX_LOSS_USD: return None  # fail closed: cannot bound L at today's price -> do not sign
    return max_fee, round(cost_usd, 4)
def sh(cmd):
    r = subprocess.run(cmd, capture_output=True, text=True, env=dict(os.environ, PATH="/opt/farm/bin:/opt/foundry/bin:"+os.environ.get("PATH","")))
    return r.returncode, r.stdout.strip()
def fork_gen():
    rc, out = sh(["fork","status","ethereum"])
    import re
    m = re.search(r"gen (\d+)", out)
    return int(m.group(1)) if m else None
def fusion_key():
    """1inch API key the gate/human drops into state/fusion_key.json ({"key": "..."}): the fusion-v1/swap
    quote endpoint is key-gated (HTTP 401 keyless, measured 2026-11-08 attempts 563 + scratch/dtf96-401.txt)."""
    p = os.path.join(os.path.dirname(__file__), "state", "fusion_key.json")
    if not os.path.exists(p): return None
    try: return json.load(open(p)).get("key")
    except Exception: return None
def fusion_legs(sell, buy, sell_amt, taker, log):
    """Live 1inch Fusion quote legs for THIS bid with taker = our executor (the vault pays the output to the
    Order's embedded taker; the winner's captured blob reverts when its taker is patched, attempts 563/564).
    v4 (review 2026-11-08T22:09Z blocker 1, USDC-unit loss guard): the bid leg is quoted on the USDC OUTPUT
    side - fromToken = sellToken, toToken = USDC: the leg pays USDC to the taker (the winner's own fill ran
    exactly this leg first: CSCO -> USDC, then a separate USDC -> buyToken hop), and the executor's USDC
    profit guard (src/FolioBidV3.sol fundSwapAndBid: require(usdcDelta >= usdcIn + minProfit), transfer of
    the whole delta to the owner) values the whole round in USDC units. Returns [leg1, leg2, dstAmount]
    full swapper calldata with dstAmount in USDC raw units, or None (fail closed: no leg, no bid). The raw
    response is logged so the paper-reviewer can audit the shape (the second split-route leg field is
    pinned from the first keyed response; until then one leg per quote and the executor takes leg2 empty)."""
    key = fusion_key()
    if not key: return None
    params = {"chain":"ethereum","fromToken":sell,"toToken":USDC,"fromAmount":str(sell_amt),
              "fromAddress":taker,"toAddress":taker}
    u = FUSION_URL + "?" + urllib.parse.urlencode(params)
    try:
        req = urllib.request.Request(u, headers={"Authorization": key})
        d = json.loads(urllib.request.urlopen(req, timeout=20).read())
    except Exception as e:
        log.write(json.dumps({"ts":int(time.time()),"event":"fusion_quote_error","err":str(e)[:120]})+"\n")
        return None
    log.write(json.dumps({"ts":int(time.time()),"event":"fusion_quote","sell":sell,"buy":buy,
                          "sellAmount":str(sell_amt),"taker":taker,"swap":d.get("swap")})+"\n")
    sw = d.get("swap") or {}
    if (sw.get("to") or "").lower() != SWAPPER: return None
    data = sw.get("data") or ""
    if not data.startswith("0x") or len(data) < 10: return None
    return [data, "0x", sw.get("dstAmount")]  # 3rd field: quote's expected venue output (USDC raw units)
def pad_bytes(h):  # h: hex string without 0x; returns length word + data padded to a 32-byte multiple
    return w(len(h)//2) + h + "0" * ((64 - len(h) % 64) % 64)
def v3_calldata(folio, aid, sell, buy, sellAmt, maxBuy, leg1, leg2, min_profit=0):
    # bidWithLegs(address,uint256,address,address,uint256,uint256,address,bytes,bytes,uint256):
    # head = 7 static slots + 2 bytes-array offsets + minProfit = 10 slots; tails: leg1 then leg2.
    t1 = pad_bytes(leg1[2:] if leg1.startswith("0x") else leg1)
    t2 = pad_bytes(leg2[2:] if leg2.startswith("0x") else leg2)
    off1, off2 = 10*32, 10*32 + len(t1)//2
    slots = [addr_word(folio), w(aid), addr_word(sell), addr_word(buy), w(sellAmt), w(maxBuy),
             addr_word(SWAPPER), w(off1), w(off2), w(min_profit)]
    return "0x"+V3_SEL+"".join(slots)+t1+t2
def fsb_calldata(folio, aid, sell, buy, usdcIn, minOutput, sellAmt, maxBuy,
                 fundleg, leg1, leg2, min_profit=0):
    # fundSwapAndBid(address,uint256,address,address,uint256,uint256,uint256,uint256,uint256,
    # bytes,bytes,bytes,uint256): head = 8 static slots + 3 bytes-array offsets + minProfit = 12
    # slots; tails in argument order: fundLeg, leg1, leg2 (an empty leg is a 32-byte zero section).
    tf = pad_bytes(fundleg[2:] if fundleg.startswith("0x") else fundleg)
    t1 = pad_bytes(leg1[2:] if leg1.startswith("0x") else leg1)
    t2 = pad_bytes(leg2[2:] if leg2.startswith("0x") else leg2)
    offf = 12*32
    off1 = offf + len(tf)//2
    off2 = off1 + len(t1)//2
    slots = [addr_word(folio), w(aid), addr_word(sell), addr_word(buy), w(usdcIn), w(minOutput),
             w(sellAmt), w(maxBuy), w(offf), w(off1), w(off2), w(min_profit)]
    return "0x"+FSB_SEL+"".join(slots)+tf+t1+t2
def exec_sim(folio, aid, sell, buy, sellAmt, buyAmt, log, opened_blk=0, lowSellRaw=0, lowBuyRaw=0):
    """Simulate the live fundSwapAndBid route on the fork.
    Live mode: the key-gated 1inch Fusion legs (taker = the executor) + the signer send.
    Paper mode (v6, review 2026-11-09T01:15Z blocker 2: PAPER MUST NEVER TOUCH THE KEY): the venue
    quote is key-gated HTTP, so paper replaces the quote with the MockUsdcVenue stand-in deployed
    on the fork at a FRESH executor (the live executor's promotion state: it starts at ZERO token
    balances - no fork fund-token of the payment inventory into the executor, review 2026-11-09
    blocker: the paper sim must validate the same initial inventory as the live route). The mock's
    payouts are the CORRIDOR ANCHORS measured from the auction's own AuctionOpened prices (no key,
    no HTTP, no state/fusion_key.json read in paper): usdcIn = the payment cap buyAmt valued at the
    corridor-low buy price, the sell leg's USDC payout = this round's sellSize valued at the
    corridor-low sell price, the funding output = payment cap + 1.56% slack (minOutput equality,
    fundedOut >= bidAmount holds strictly); the corridor margin payout - usdcIn rides as minProfit
    (USDC units, the exact value the contract pays the owner), so a corridor-positive round pays
    exactly its corridor delta and the route's revert = auction not executable."""
    if MODE == "live":
        ex = os.environ.get("EXECUTOR_ADDR")
        if not ex: return {"skipped": "live: no EXECUTOR_ADDR from gate"}
        legs = fusion_legs(sell, buy, sellAmt, ex, log)
        if not legs:
            return {"skipped": "live: no 1inch Fusion quote (state/fusion_key.json key missing or quote failed) -> fail closed, no send"}
        bound = live_fee_bound()
        if bound is None: return {"skipped": "live: fee bound exceeds MAX_LOSS_USD at today's price (fail closed)"}
        max_fee, cost_usd = bound
        # live route (review 2026-11-08T20:45Z blocker 2): ONE atomic guarded transaction
        # fundSwapAndBid - the USDC->buyToken funding leg (deficit only) AND the bid AND the owner
        # payout in the same executor call. live_route_ready prepares the funding leg (and the
        # folio pin / USDC approve setup txs); the bid send carries it. A reverted bid rolls the
        # funding leg back: the wallet USDC never leaves the wallet unless the route succeeded.
        ok, reason, min_profit, fund = live_route_ready(ex, folio, buy, buyAmt, legs[2], cost_usd, max_fee, log)
        if not ok: return {"skipped": reason}
        data = fsb_calldata(folio, aid, sell, buy, fund["usdcIn"], fund["minOutput"], sellAmt,
                            buyAmt, fund["leg"], legs[0], legs[1], min_profit)
        try:
            sys_path_fix()
            from farmbot_signer import send
            r = send(chain="ethereum", to=ex, data=data, gas=GAS_LIVE, max_fee_per_gas=max_fee)
            return {"mode":"signer-send","ok":bool(r.get("ok")),"tx":r.get("transactionHash"),
                    "gas":GAS_LIVE,"maxFee":max_fee,"feeUsd":cost_usd,"usdcIn":fund["usdcIn"],
                    "minOutput":fund["minOutput"],"err":r.get("error")}
        except Exception as e:
            return {"mode":"signer-send","ok":False,"reason":str(e)[:100]}
    # paper: the shared local fork must contain the live auction AND the whole deploy/fund/sim sequence
    # must run under a lease (review 16:00Z: token funding mutates the shared fork too).
    # Lease etiquette: seconds of work, 1 minute max; lease busy = skip this poll, sim stays pending.
    head = h(rpc(RELAY,"eth_blockNumber",[]))
    try: fork_blk = h(rpc(FORK, "eth_blockNumber", []))
    except Exception as e: return {"skipped": "fork unreachable " + str(e)[:60]}
    rc, _ = sh(["fork","lease","ethereum","1","dtf-paper-sim"])
    if rc != 0: return {"skipped": "fork lease busy (another session holds it)"}
    leased = True
    if head - fork_blk > 400 or fork_blk <= opened_blk:
        rc, _ = sh(["fork","reset","ethereum",str(head - 1)])
        if rc != 0:
            sh(["fork","release","ethereum"])
            return {"skipped": "fork reset failed"}
        fork_blk = head - 1
    def fin(res):
        if leased: sh(["fork","release","ethereum"])
        return res
    if fork_blk <= opened_blk:
        return fin({"skipped": "fork stale: auction opened blk %d > fork head %d (auction not on fork yet)" % (opened_blk, fork_blk)})
    if not (lowSellRaw and lowBuyRaw):
        return fin({"skipped": "corridor anchors missing (AuctionOpened prices not decoded)"})
    # corridor sizing (keyless, no HTTP): USDC raw = raw units x USD-per-raw-unit (raw/1e39) x 1e6.
    usdc_in = buyAmt * lowBuyRaw // 10**33 + 1          # the payment cap bought at the corridor-low buy price
    payout  = sellAmt * lowSellRaw // 10**33 + 1        # the sell leg's USDC payout at the corridor-low sell price
    margin  = payout - usdc_in                          # USDC raw units: the corridor delta of the round
    if margin <= 0:
        return fin({"skipped": "corridor margin not positive (payout <= funding spend, fail closed)"})
    out_buy = buyAmt + buyAmt // 64 + 1                 # funding output = payment cap + 1.56% slack
    # deploy the venue stand-in + a FRESH executor pinned to it (constructor args run; the executor
    # is at ZERO token balances at the start - the same initial inventory as the live route).
    sh(["fork","fund","ethereum",FROM,"5"])
    margs = sh(["cast","abi-encode","f(address,address,address,uint256,uint256,uint256)",
                sell, USDC, buy, str(payout), str(out_buy), "0"])[1]
    rc, out = sh(["fork","deploy","ethereum","MockUsdcVenue.json",FROM,"--args",margs])
    import re
    m = re.search(r"0x[0-9a-fA-F]{40}", out)
    if rc != 0 or not m: return fin({"skipped": "mock venue deploy failed " + out[-80:]})
    mock = m.group(0)
    folio2 = "0xe592f69e4f60e9a78dba0043573b898386c01cb8" if folio.lower() != "0xe592f69e4f60e9a78dba0043573b898386c01cb8" else "0x2cf4dafc17e163abd6770e1794e1ad10deb7d32e"
    eargs = sh(["cast","abi-encode","f(address,address,address)", mock, folio, folio2])[1]
    rc, out = sh(["fork","deploy","ethereum","FolioBidV3.json",FROM,"--args",eargs])
    m = re.search(r"0x[0-9a-fA-F]{40}", out)
    if rc != 0 or not m: return fin({"skipped": "executor deploy failed " + out[-80:]})
    ex = m.group(0)
    gen0 = fork_gen()
    # fund the mock (it pays the payouts FROM ITS OWN balances: transfer reverts when short) and
    # the fork wallet FROM (the funding leg's transferFrom(owner) source, USDC-approved below).
    rc, _ = sh(["fork","fund-token","ethereum",USDC,USDC_HOLDER,mock,str(payout + 1)])
    if rc != 0: return fin({"skipped": "fund mock USDC failed"})
    funded_from = None
    for cand in [folio] + FOLIOS[:6]:
        b = bal(buy, cand)
        if b is not None and b >= out_buy:
            rc, _ = sh(["fork","fund-token","ethereum",buy,cand,mock,str(out_buy)])
            if rc == 0: funded_from = cand; break
    if not funded_from: return fin({"skipped": "no buyToken funding source on the fork for the mock (fail closed)"})
    rc, _ = sh(["fork","fund-token","ethereum",USDC,USDC_HOLDER,FROM,str(usdc_in + 1)])
    if rc != 0: return fin({"skipped": "fund owner USDC failed"})
    rc, _ = sh(["fork", "send", "ethereum", json.dumps({"from": FROM, "to": USDC,
            "data": "0x095ea7b3" + addr_word(ex) + w(usdc_in), "gas": "0xEA60"})])
    if rc != 0: return fin({"skipped": "owner USDC approve failed"})
    data = fsb_calldata(folio, aid, sell, buy, usdc_in, out_buy, sellAmt, out_buy,
                        "0xe21fd0e9", "0xe21fd0e9", "0x", margin)
    try:
        rpc(FORK, "eth_call", [{"to":ex,"from":FROM,"data":data}, "latest"])  # from = FROM = the deployer the hardened entry requires (owner-only)
        ok = True
    except Exception as e:
        return fin({"mode":"fork-eth-call","ok":False,"reason":str(e)[:80],"gen":gen0})
    # the eth_call passed: send the SAME transaction on the fork (state-changing, under the lease)
    # to measure the executed gas and the owner USDC delta = corridor margin (fork basefee 0).
    res = None
    try:
        o0 = bal(USDC, FROM); b0 = bal(BUY, ex)
        r = json.loads(sh(["fork","send","ethereum", json.dumps({"from": FROM, "to": ex,
                   "data": data, "gas": str(GAS_LIVE), "value": "0x0"})])[1])
        st = str(r.get("status")); ok1 = st in ("0x1","1")
        res = {"send_status": "0x1" if ok1 else "0x0", "send_gasUsed": r.get("gasUsed"),
               "owner_usdc_delta": str(bal(USDC, FROM) - o0), "buy_left": str(bal(BUY, ex) - b0)}
        ok = ok1  # the send is the measured route; a reverted send is not a profitable capture
    except Exception as e:
        res = {"send_error": str(e)[:80]}
    stale = fork_gen() != gen0
    return fin({"mode":"fork-eth-call+send","ok":ok,"venue":"mock_fusion_standin","funded":"fundSwapAndBid",
                "usdcIn":usdc_in,"minOutput":out_buy,"payout":payout,"outBuy":out_buy,
                "marginUsdCorridor":round(margin/1e6,4),"executor":ex,"mock":mock,"buyFundedFrom":funded_from,
                "send":res,"gen":gen0,"stale":stale})
def sys_path_fix():
    import sys
    if "/opt/farm/lib" not in sys.path: sys.path.insert(0, "/opt/farm/lib")
def wallet_addr():
    """The bot wallet the signer signs with (farmbot_signer.my_address; a dict on some helper
    versions - the compound-accrue review 08:07Z blocker: extract the address string, not the dict)."""
    sys_path_fix()
    from farmbot_signer import my_address
    a = my_address()
    return (a.get("address") if isinstance(a, dict) else a)
def relay_bal(token, who):
    try: return h(call(token, "0x70a08231"+addr_word(who))[2:])
    except Exception: return None
def funding_quote(ex, buy, buyAmt, log):
    """Quote the USDC->buyToken funding leg sized to the payment cap buyAmt with taker = the
    executor (v5, review 2026-11-08T23:42Z blocker 1: fundSwapAndBid's funding leg is MANDATORY -
    every bid pays for its own payment inventory with its own USDC in the SAME tx, so the executor
    pre-existing inventory is never consumed unvalued). Returns {usdcIn, minOutput (the quoted
    dstAmount, must cover buyAmt), leg} or None (key-gated, fail closed)."""
    usd_pu = fusion_quote_usd_per_unit(buy, log)  # USD per raw buyToken unit, from a 10-USDC probe quote
    if usd_pu is None: return None
    usdc_units = int(buyAmt * usd_pu * 1e6) + 100  # ceil + 0.0001 USDC rounding allowance
    params = {"chain":"ethereum","fromToken":USDC,"toToken":buy,"fromAmount":str(usdc_units),
              "fromAddress":ex,"toAddress":ex}   # taker = executor: the pull and the payout are the executor's
    u = FUSION_URL + "?" + urllib.parse.urlencode(params)
    try:
        req = urllib.request.Request(u, headers={"Authorization": fusion_key()})
        d = json.loads(urllib.request.urlopen(req, timeout=60).read())
    except Exception: return None
    sw = d.get("swap") or {}
    fdata = sw.get("data") or ""
    dst_f = sw.get("dstAmount")
    if (sw.get("to") or "").lower() != SWAPPER or not fdata.startswith("0x") or not dst_f: return None
    if int(dst_f) < buyAmt: return None            # the funding output must cover the payment cap
    return {"usdcIn": usdc_units, "minOutput": int(dst_f), "leg": fdata}
def fusion_quote_usd_per_unit(buy, log):
    """Small USDC -> buyToken quote on the key-gated Fusion endpoint (HTTP only, no tx): the implied
    USD price of ONE RAW unit of the buy token (10 USD / dstAmount). None (fail closed) without the key."""
    key = fusion_key()
    if not key: return None
    waddr = wallet_addr()
    params = {"chain":"ethereum","fromToken":USDC,"toToken":buy,"fromAmount":"10000000",  # 10 USDC probe
              "fromAddress":waddr,"toAddress":waddr}
    u = FUSION_URL + "?" + urllib.parse.urlencode(params)
    try:
        req = urllib.request.Request(u, headers={"Authorization": key})
        d = json.loads(urllib.request.urlopen(req, timeout=60).read())
    except Exception as e:
        return None
    sw = d.get("swap") or {}
    dst = sw.get("dstAmount")
    return 10.0 / int(dst) if dst and int(dst) > 0 else None
def live_route_ready(ex, folio, buy, buyAmt, dst_quote, cost_usd, max_fee, log):
    """Live pre-bid route (review 2026-11-08T20:45Z blocker 2: funding and the bid must not be two
    transactions where the second can fail after the first spent the principal): prepare the
    funding leg of the SINGLE atomic fundSwapAndBid transaction the caller then sends. (a0) folio
    pin setup tx when the auction's folio is not pinned yet; (a1) the funding leg is MANDATORY (v5,
    review 2026-11-08T23:42Z blocker 1): quote the exact USDC->buyToken Fusion leg sized to the
    payment cap with taker = the
    executor and make sure the wallet's USDC allowance to the executor covers it (one small
    approve setup tx when short); nothing is sent here - fund = {usdcIn, minOutput (the quoted
    dstAmount), leg} rides inside the bid transaction, where a failed or under-delivering funding
    leg reverts the WHOLE route (the USDC stays in the wallet, worst case gas) and the callback may
    only pay the Folio from that fresh output (require(fundedOut >= bidAmount)). (b) after-gas
    margin gate (v4, review 2026-11-08T22:09Z blocker 1: the loss bound is enforced in USDC
    units): the venue's USDC output minus this round's USDC spend (both in USDC raw units) must
    exceed the signed gas cost, else no send; the bid carries minProfit = that margin, measured by
    the contract against its own USDC balance: require(usdcDelta >= usdcIn + minProfit) with the
    whole delta transferred to the owner in the same tx - the wallet's USDC ends higher than spent.
    Returns (ok, reason, min_profit, fund)."""
    try:
        sys_path_fix()
        from farmbot_signer import send
    except Exception as e:
        return False, "live: signer import failed " + str(e)[:60], 0, {"usdcIn":0,"minOutput":0,"leg":"0x"}
    waddr = wallet_addr()
    if not waddr: return False, "live: no signer wallet address", 0, None
    # (a0) folio pin: the constructor pins two folios; a new folio gets one owner-only setFolio tx first.
    try:
        if h(call(ex, PIN_SEL + addr_word(folio))[2:]) == 0:
            r = send(chain="ethereum", to=ex, data="0x"+SETFOLIO_SEL+addr_word(folio)+w(1), gas=200000, max_fee_per_gas=max_fee)
            if not r.get("ok"): return False, "live: setFolio send failed " + str(r.get("error"))[:60], 0, None
    except Exception as e:
        return False, "live: folio pin read failed " + str(e)[:60], 0, None
    # (a1) the funding leg is MANDATORY (v5, review 2026-11-08T23:42Z blocker 1): fundSwapAndBid
    # pulls exactly usdcIn USDC from the wallet, runs the taker=executor leg on the pinned swapper,
    # and reverts unless the buyToken balance rises by >= minOutput AND the payment fits in THAT
    # fresh output (require(fundedOut >= bidAmount) in the callback) - all inside the bid tx. The
    # "already funded" usdcIn = 0 route (a payment drawing unvalued on pre-funded inventory) is gone.
    fund = {"usdcIn": 0, "minOutput": 0, "leg": "0x"}
    fu = funding_quote(ex, buy, buyAmt, log)
    if fu is None: return False, "live: USDC->buyToken funding quote failed or under-delivers (key-gated, fail closed)", 0, None
    usdc_units = fu["usdcIn"]
    bal_w = relay_bal(USDC, waddr)
    if bal_w is None or bal_w < usdc_units: return False, "live: wallet USDC below funding cost", 0, None
    # the wallet must have approved the executor to pull this much USDC (one small approve tx when short).
    try:
        allow = h(call(USDC, "0xdd62ed3e"+addr_word(waddr)+addr_word(ex))[2:])  # allowance(address,address) (cast sig 2026-11-08)
    except Exception: return False, "live: USDC allowance read failed", 0, None
    if allow < usdc_units:
        r = send(chain="ethereum", to=USDC, data="0x095ea7b3"+addr_word(ex)+w(usdc_units), gas=60000, max_fee_per_gas=max_fee)
        log.write(json.dumps({"ts":int(time.time()),"event":"funding_approve","ok":bool(r.get("ok")),
                              "units":usdc_units,"tx":r.get("transactionHash")})+"\n")
        if not r.get("ok"): return False, "live: USDC approve send failed", 0, None
    fund = fu
    log.write(json.dumps({"ts":int(time.time()),"event":"funding_leg","usdcIn":usdc_units,
                          "minOutput":fund["minOutput"],"legLen":len(fund["leg"])//2-4})+"\n")
    # (b) after-gas margin gate (v4, review 2026-11-08T22:09Z blocker 1: the loss bound is enforced in
    # USDC units): the venue's USDC output for this round's sellToken (dst_quote, USDC raw units) minus the
    # USDC this round spends (fund["usdcIn"]) is the wallet's net payout - it must exceed the signed gas
    # cost, else no send. The bid carries minProfit = that margin in USDC raw units: the contract reverts
    # unless its own USDC balance delta >= usdcIn + minProfit and transfers the whole delta to the owner in
    # the same tx (src/FolioBidV3.sol fundSwapAndBid), so the WALLET's USDC ends higher than it spent.
    if dst_quote is None: return False, "live: quote dstAmount missing (fail closed)", 0, None
    margin_raw = int(dst_quote) - fund["usdcIn"]   # USDC raw units: wallet net payout of the round
    if margin_raw <= 0: return False, "live: USDC margin not positive (venue output <= spend, fail closed)", 0, None
    margin_usd = margin_raw / 1e6
    if margin_usd < cost_usd: return False, "live: margin %.4f USD below gas %.4f USD (fail closed)" % (margin_usd, cost_usd), 0, None
    return True, "live: funding leg prepared + margin above gas", margin_raw, fund
STATE = {}
def main():
    global STATE
    lgdir = os.path.join(os.path.dirname(__file__), "logs")
    log = open(os.path.join(lgdir, "opps.jsonl"), "a")
    st = None
    if os.path.exists(STATEF):
        st = json.load(open(STATEF))
        if not (isinstance(st, dict) and "from_block" in st and "v" in st): st = None
    if not st: st = {"v":2,"from_block":None,"exec":None,"auctions":{}}
    STATE = st
    if st["from_block"] is None: st["from_block"] = h(rpc(RELAY,"eth_blockNumber",[])) - 80000  # backfill ~2 days (burst was 64k blocks back)
    while True:
        try:
            head = h(rpc(RELAY,"eth_blockNumber",[]))
            now = int(time.time())
            headq = max(1, head - 50)  # public-node fallback heads lag the relay cache: toBlock > node head = -32602
            logs = rpc(RELAY,"eth_getLogs",[{"address":FOLIOS,"topics":[[OPENED_T0,BID_T0]],
                                              "fromBlock":hex(st["from_block"]),"toBlock":hex(headq)}])
            auctions = st["auctions"]
            for l in logs:
                f = l["address"].lower(); t0 = l["topics"][0]
                blk = h(l["blockNumber"])
                if t0 == OPENED_T0:
                    aid = h(l["topics"][2])
                    toks, prices, start, end = dec_opened(l["data"])
                    auctions[f+":"+str(aid)] = {"nonce":h(l["topics"][1]),"start":start,"end":end,
                        "tokens":toks,"pricesLow":prices,"pairs":{},"blk":blk,"simDone":False}
                else:  # AuctionBid: pair + decayed state at the bid block
                    aid = h(l["topics"][1]); sell = "0x"+l["topics"][2][-40:]; buy = "0x"+l["topics"][3][-40:]
                    a = auctions.get(f+":"+str(aid))
                    if a is None:  # opened before our scan: fetch its AuctionOpened (aid indexed at topic slot 2)
                        o = rpc(RELAY,"eth_getLogs",[{"address":f,"topics":[OPENED_T0,None,w(aid)],
                                "fromBlock":hex(max(14000000, blk-99000)),"toBlock":hex(headq)}])  # <=50k-block node cap, <=node head
                        if not o: continue
                        oo = o[-1]; toks2, pr2, s2, e2 = dec_opened(oo["data"])
                        a = auctions[f+":"+str(aid)] = {"nonce":h(oo["topics"][1]),"start":s2,"end":e2,
                             "tokens":toks2,"pricesLow":pr2,"pairs":{},"blk":h(oo["blockNumber"]),"simDone":False}
                    key = sell+"-"+buy
                    a["pairs"][key] = {"sell":h(l["data"][2:66]),"buy":h(l["data"][66:130]),"blk":blk}
                    if a.get("pricesLow"):  # audit trail: incumbent bid = decayed state at its block
                        ti = {t: i for i, t in enumerate(a["tokens"])}
                        try:
                            sd, bd = a["tokens"].index(sell), a["tokens"].index(buy)
                        except ValueError:
                            sd = bd = None
                        if sd is not None and bd is not None:
                            dlt = (h(l["data"][2:66])*a["pricesLow"][sd][0] - h(l["data"][66:130])*a["pricesLow"][bd][0])/1e39
                            log.write(json.dumps({"ts":now,"folio":f,"aid":aid,"sell":sell,"buy":buy,"src":"bidEvent",
                                "sellAvail":h(l["data"][2:66]),"liveBid":h(l["data"][66:130]),"blk":blk,
                                "deltaUsdCorridor":round(dlt,2)})+"\n")
            if len(auctions) > 200:  # prune settled scans
                st["auctions"] = auctions = {k: v for k, v in auctions.items() if v["blk"] > head - 40000}
            log.flush()
            # live-decayed getBid for open auctions with known pairs (<= 2 pairs per auction, <= 4 calls per poll)
            bid_calls = 0
            for k, a in list(auctions.items()):
                f, aid = k.split(":"); aid = int(aid)
                if a["start"] <= now <= a["end"]:
                    frac = (now - a["start"]) / max(1, a["end"] - a["start"])
                    for key, stt in list(a["pairs"].items())[:2]:
                        if bid_calls >= 4: break
                        sell, buy = key.split("-")
                        try: s0, b0, p0 = getbid(f, aid, sell, buy, 10**27)
                        except Exception as e:
                            log.write(json.dumps({"ts":now,"folio":f,"aid":aid,"sell":sell,"buy":buy,
                                                  "watch":"getBid reverted "+str(e)[:60]})+"\n"); continue
                        bid_calls += 1
                        if s0 <= 0: continue
                        ti_sell = a["tokens"].index(sell); ti_buy = a["tokens"].index(buy)
                        lowSellRaw = a["pricesLow"][ti_sell][0]; lowBuyRaw = a["pricesLow"][ti_buy][0]
                        # token decimals measured 18 on both basket sides (cast decimals() 2026-11-08)
                        size = min(s0, int(SIZE_USD * 1e66 / max(1, p0 * lowBuyRaw)))
                        if size <= 0: continue
                        bidamt = (size * p0 + 10**27 - 1) // 10**27  # ceil buyTok raw = sellSize x price
                        delta = (size * lowSellRaw - bidamt * lowBuyRaw) / 1e39  # corridor-low USD anchors
                        opp = {"ts":now,"folio":f,"aid":aid,"sell":sell,"buy":buy,"src":"getBid",
                               "sellAvail":s0,"price":p0,"frac":round(frac,3),"sellSize":size,
                               "liveBid":bidamt,"lowSellUsd":round(lowSellRaw/1e21,4),
                               "lowBuyUsd":round(lowBuyRaw/1e21,4),"deltaUsdCorridor":round(delta,2),
                               "block":head}
                        if frac >= BID_FRAC and not a.get("simDone"):
                            opp["sim"] = exec_sim(f, aid, sell, buy, size, bidamt, log, opened_blk=a["blk"],
                                                  lowSellRaw=lowSellRaw, lowBuyRaw=lowBuyRaw)
                            if "skipped" not in opp["sim"]:  # a real sim (ok or revert) ran: do not re-sim this auction
                                a["simDone"] = True         # a skip (stale fork, no executor) leaves the auction open for the next poll
                        log.write(json.dumps(opp)+"\n"); log.flush()
            st["from_block"] = headq + 1  # resume after what was scanned (head+1 would make fromBlock > toBlock)
            json.dump(st, open(STATEF,"w"))
        except Exception as e:
            print("poll error", repr(e), flush=True)
        time.sleep(POLL)
if __name__ == "__main__":
    main()
