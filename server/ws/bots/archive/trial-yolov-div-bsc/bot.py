#!/usr/bin/env python3
"""trial: YoloVerse dividend trigger on BSC. The YoloVerse helper contract's triggerDivRewards() is public, can
run once every 28,800 blocks (YOLOV.getNextDivBlock(); the first block that passes is next + 1) and pays its caller
a fixed 2,400 YOLOV "gas refund" (2,256 after the token's own 4 pct burn and 2 pct fee). One transaction through the
DivTrigger executor does: triggerDivRewards() -> the YOLOV received sold for WBNB on the PancakeSwap V2 YOLOV / WBNB
pair -> unwrap -> BNB to the bot wallet, and reverts unless the BNB gained is at least minProfit.
Timer bot: the due block is known 3.6 hours ahead. It sleeps towards it, polls the head for the last seconds,
simulates the exact transaction with the block number overridden to the due block, and sends LEAD blocks before it."""
import sys
sys.path.append('/opt/farm/lib')
import datetime
import json
import os
import time
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
MODE = os.environ.get('BOT_MODE', 'paper')
RELAY = os.environ['RPC_RELAY_URL'].rstrip('/')
LANE = os.environ.get('RPC_LANE', 'paper')
CHAIN = 'bsc'

# Addresses (README "Addresses": each read from the chain with a getter of the contract before it).
KEEPER = '0x97f9388f389e1bb3019935b7939eee50163d9624'   # YoloVerse helper: triggerDivRewards(), YOLOV_ADDRESS() = YOLOV
YOLOV = '0xd084c5a4a621914ed2992310024d2438dfde5bfd'    # symbol() YOLOV; getNextDivBlock(), lastDivRewBlock()
PAIR = '0x526a03728156aea4af6051e47d52e99a818bc087'     # YOLOV.getPairAddress() = KEEPER.getPair(): PancakeSwap V2 WBNB / YOLOV
WBNB = '0xbb4cdb9cbd36b01bd1cbaebf2de08d9173bc095c'     # YOLOV.WBNB_ADDRESS()
PAIR_FEE_BPS = 25                                        # PancakeSwap V2 swap fee 0.25 pct

# Selectors and the topic, all from `cast sig` / `cast keccak`.
SEL_RUN = '0xd5bd8c8a'          # run(address,bytes4,address,address,address,uint256,uint256)
SEL_TRIGGER = '0x6c755687'      # triggerDivRewards()
SEL_NEXT = '0xffe389f8'         # getNextDivBlock()
SEL_LAST = '0x659e00a8'         # lastDivRewBlock()
TOPIC_GAS_SPENT = '0x6266daabc53631f12d8e4c5b6f1e9abd6e8d7874163fa0e341509fbd582b44ff'   # GasSpent(address,address,uint256,uint256,uint256)

PAPER_EXEC = '0x00000000000000000000000000000000000d1771'   # code-override address, paper only
PAPER_OWNER = '0xc0ffee0000000000000000000000000000000321'  # owner baked into the fork deployment's runtime code
EXEC = os.environ.get('EXECUTOR_ADDR_BSC') or os.environ.get('EXECUTOR_ADDR')
if MODE == 'live' and not EXEC:
    raise SystemExit('EXECUTOR_ADDR_BSC or EXECUTOR_ADDR required in live mode')
RUNTIME_FILE = HERE / 'executor-runtime.hex'

BLOCK_S = 0.45                    # BSC block time (measured from timestamps: 28,801 blocks in 12,965 s)
TIGHT_BLOCKS = 40                 # poll the head every POLL_S for the last this many blocks (18 s)
POLL_S = 0.25
LEAD_DEFAULT = 5                  # send when head >= due - LEAD; adjusted from each send's landing block
                                  # (wiki methods/timer-first-block-send.md: the signer alone took 1.25 s = about 3 blocks here)
LEAD_MIN, LEAD_MAX = 1, 12
PLAN_BLOCKS = 12                  # simulate this many blocks before the send point
SENDS_PER_WINDOW = 2              # the second one block after the first; an early or late one reverts "Not time yet !"
GAS_LIMIT = 900_000               # fork: a won run uses 669,733 gas, a "Not time yet !" revert 48,151
GAS_USED_REF = 670_000
BID_SHARE = 0.25                  # the most the bot bids: this share of the simulated gross, as gas price x GAS_USED_REF
MIN_TIP_WEI = 100_000_000         # 0.1 gwei (the two public incumbents pay 0.05 and 0.0501 gwei)
MAX_TIP_WEI = 800_000_000         # 0.8 gwei: never sign above this
BNB_REF_USD = 1200.0              # conservative (about 580 USD on 2026-11-22): overstates every gas bound
MAX_TX_USD = 0.95
CU_CAP = 60_000
CU_COST = {'eth_call': 26, 'eth_getBlockByNumber': 20, 'eth_getTransactionReceipt': 20, 'eth_blockNumber': 10,
           'eth_getLogs': 75}

LOG = HERE / 'logs' / 'bot.jsonl'
STATE = HERE / 'state' / 'cu.json'
LEAD_FILE = HERE / 'state' / 'lead.json'


class ReadBudgetExceeded(Exception):
    pass


def log(event, **fields):
    LOG.parent.mkdir(exist_ok=True)
    with LOG.open('a') as f:
        f.write(json.dumps({'ts': round(time.time(), 3), 'ev': event, **fields}, separators=(',', ':')) + '\n')


def rpc(method, params, raw=False):
    day = datetime.datetime.now(datetime.timezone.utc).date().isoformat()
    try:
        budget = json.loads(STATE.read_text())
    except Exception:
        budget = {'day': day, 'cu': 0}
    if budget.get('day') != day:
        budget = {'day': day, 'cu': 0}
    budget['cu'] += CU_COST.get(method, 26)
    if budget['cu'] > CU_CAP:
        raise ReadBudgetExceeded(f'{CU_CAP} CU/day cap')
    STATE.parent.mkdir(exist_ok=True)
    STATE.write_text(json.dumps(budget))
    body = json.dumps({'jsonrpc': '2.0', 'id': 1, 'method': method, 'params': params}).encode()
    req = urllib.request.Request(f'{RELAY}/{CHAIN}?lane={LANE}', body, {'content-type': 'application/json'})
    with urllib.request.urlopen(req, timeout=40) as resp:
        ans = json.load(resp)
    if raw:
        return ans
    if 'error' in ans:
        raise RuntimeError(f'{method}: {str(ans["error"])[:300]}')
    return ans['result']


def w(n):
    return format(n, '064x')


def a(addr):
    return addr.lower().removeprefix('0x').zfill(64)


def run_calldata(min_profit):
    """run(keeper, selector, token, pair, wrapped, pairFeeBps, minProfit); bytes4 is left-aligned in its word."""
    return (SEL_RUN + a(KEEPER) + SEL_TRIGGER.removeprefix('0x').ljust(64, '0') + a(YOLOV) + a(PAIR) + a(WBNB)
            + w(PAIR_FEE_BPS) + w(min_profit))


def owner():
    import farmbot_signer
    result = farmbot_signer.my_address()
    address = result['address'] if isinstance(result, dict) else result
    if not isinstance(address, str) or len(address) != 42:
        raise RuntimeError('signer my_address returned no address')
    return address


def executor():
    return EXEC if MODE == 'live' else PAPER_EXEC


def gain_of(min_profit=1, as_block=None, at='latest'):
    """BNB gain (wei) of run() as an eth_call of the exact transaction on the state of `at`, with block.number
    overridden to `as_block` when given (the due block is in the future). 0 and the error text when it reverts
    (not due, already taken, or NoProfit)."""
    ex = executor()
    tx = {'from': owner() if MODE == 'live' else PAPER_OWNER, 'to': ex, 'data': run_calldata(min_profit),
          'gas': hex(GAS_LIMIT)}
    state = {ex: {'code': RUNTIME_FILE.read_text().strip()}} if MODE == 'paper' else {}
    params = [tx, at, state]
    if as_block is not None:
        params.append({'number': hex(as_block)})
    ans = rpc('eth_call', params, raw=True)
    if 'error' in ans:
        return 0, str(ans['error'])[:200]
    return int(ans['result'], 16), None


def uint_call(to, sel):
    return int(rpc('eth_call', [{'to': to, 'data': sel}, 'latest']), 16)


def head_number():
    return int(rpc('eth_blockNumber', []), 16)


def read_lead():
    try:
        return min(LEAD_MAX, max(LEAD_MIN, int(json.loads(LEAD_FILE.read_text())['lead'])))
    except Exception:
        return LEAD_DEFAULT


def write_lead(lead):
    LEAD_FILE.parent.mkdir(exist_ok=True)
    LEAD_FILE.write_text(json.dumps({'lead': min(LEAD_MAX, max(LEAD_MIN, lead))}))


def winner_of(due):
    """Who took the reward that became due at block `due`: block, tx index, caller, tx hash (None while untaken)."""
    last = uint_call(YOLOV, SEL_LAST)
    if last < due:
        return None
    logs = rpc('eth_getLogs', [{'address': KEEPER, 'fromBlock': hex(last), 'toBlock': hex(last),
                                'topics': [TOPIC_GAS_SPENT]}])
    if not logs:
        return {'block': last, 'tx_index': None, 'caller': None, 'hash': None}
    lg = logs[-1]
    return {'block': last, 'tx_index': int(lg['transactionIndex'], 16), 'caller': '0x' + lg['data'][26:66],
            'hash': lg['transactionHash']}


def plan(due, head):
    """Simulate the exact transaction as of the due block and decide the bid. Returns None (nothing to do) or a
    dict with gross, tip, max_fee, cap and min_profit, all in wei."""
    gross, err = gain_of(1, due if head < due else None)
    if not gross:
        log('check', due_block=due, head=head, result='nothing', error=err)
        return None
    tip = min(MAX_TIP_WEI, max(MIN_TIP_WEI, int(BID_SHARE * gross / GAS_USED_REF)))
    max_fee = tip                                      # BSC base fee is 0; the signed price is the whole bid
    cap = GAS_LIMIT * max_fee                          # the most this send can cost, wei
    cap_usd = cap / 1e18 * BNB_REF_USD
    out = {'gross': gross, 'tip': tip, 'max_fee': max_fee, 'cap': cap, 'min_profit': max(cap, gross // 2)}
    log('opportunity', due_block=due, head=head, gross_wei=gross, tip_wei=tip, cap_wei=cap, cap_usd=round(cap_usd, 4),
        gas_limit=GAS_LIMIT, bid_share_of_gross=round(tip * GAS_USED_REF / gross, 4))
    if cap_usd >= MAX_TX_USD:
        log('opportunity_skip', reason='usd_cap', cap_usd=cap_usd)
        return None
    if gross <= cap:                                   # send only when expected gross > this send's gas cap
        log('opportunity_skip', reason='gross_not_above_gas_cap', gross_wei=gross, cap_wei=cap)
        return None
    return out


def send_one(p):
    import farmbot_signer
    t0 = time.time()
    reply = farmbot_signer.send(CHAIN, EXEC, run_calldata(p['min_profit']), 0, GAS_LIMIT, p['max_fee'],
                                max_priority_fee_per_gas=p['tip'])
    tx_hash = reply.get('txHash') if isinstance(reply, dict) else None
    if not tx_hash:
        log('signer_reject', reply=reply)
    else:
        log('sent', hash=tx_hash, signer_s=round(time.time() - t0, 3))
    return tx_hash


def settle(due, lead, p, sent):
    """Receipts of this window's sends, the winner, one send_result line per send, and the next LEAD."""
    receipts = {}
    for _ in range(25):
        time.sleep(1.0)
        for h, _ in sent:
            if h not in receipts:
                r = rpc('eth_getTransactionReceipt', [h])
                if r:
                    receipts[h] = r
        if len(receipts) == len(sent):
            break
    try:
        win = winner_of(due)
    except ReadBudgetExceeded:
        raise
    except Exception as e:
        log('winner_lookup_error', error=str(e)[:160])
        win = None
    first_landing = None
    for h, head_at_send in sent:
        r = receipts.get(h)
        if not r:
            log('send_result', hash=h, result='unknown', due_block=due, lead=lead, head_at_send=head_at_send,
                gas_used=None, winner_block=win and win['block'])
            continue
        block, status, used = int(r['blockNumber'], 16), int(r['status'], 16), int(r['gasUsed'], 16)
        if first_landing is None:
            first_landing = block
        why = None if status else ('early' if block < due else 'late' if (win and block > win['block']) else 'outbid_same_block')
        log('send_result', hash=h, result='won' if status else 'lost', lost_why=why, gas_used=used, gas_limit=GAS_LIMIT,
            tip_wei=p['tip'], cap_wei=p['cap'], gas_cost_wei=used * int(r['effectiveGasPrice'], 16),
            expected_gross_wei=p['gross'] if status else 0, min_profit_wei=p['min_profit'], due_block=due, lead=lead,
            head_at_send=head_at_send, send_block=block, tx_index=int(r['transactionIndex'], 16),
            winner_block=win and win['block'], winner_tx_index=win and win['tx_index'],
            winner_caller=win and win['caller'])
    if first_landing is not None:                      # aim the first send at the due block itself
        if first_landing < due:
            write_lead(lead - 1)
        elif first_landing > due:
            write_lead(lead + min(3, first_landing - due))


def window(due):
    """Tight poll up to the due block, fire LEAD blocks before it (or at once when it is already due and untaken)."""
    lead = read_lead()
    p, sent, fired_at = None, [], None
    deadline = time.time() + TIGHT_BLOCKS * BLOCK_S * 3 + 30
    while time.time() < deadline:
        head = head_number()
        if p is None and head >= due - lead - PLAN_BLOCKS:
            p = plan(due, head)                        # simulate ahead, so the send itself waits on nothing
            if p is None:
                return
            continue
        if p is not None and head >= due - lead and fired_at is None:
            fired_at = head
            if MODE == 'paper':
                log('paper_sim', result='success', due_block=due, head=head, lead=lead, gross_wei=p['gross'],
                    min_profit_wei=p['min_profit'], tip_wei=p['tip'], cap_wei=p['cap'], gas_limit=GAS_LIMIT)
                break
            h = send_one(p)
            if not h:
                return
            sent.append((h, head))
        elif fired_at is not None and head > fired_at and len(sent) < SENDS_PER_WINDOW and head <= due:
            h = send_one(p)
            if h:
                sent.append((h, head))
            fired_at = head
        if sent and (len(sent) >= SENDS_PER_WINDOW or head > due):
            break
        time.sleep(POLL_S)
    if MODE == 'paper':
        if p is None:
            return
        time.sleep(20)                                 # who took it, and how many blocks after it was due
        win = winner_of(due)
        log('paper_outcome', due_block=due, winner_block=win and win['block'], winner_tx_index=win and win['tx_index'],
            winner_caller=win and win['caller'], winner_hash=win and win['hash'],
            blocks_after_due=(win['block'] - due) if win else None)
        return
    if sent:
        settle(due, lead, p, sent)


def main():
    """Timer loop. Every relay read is inside the try that catches the bot's CU cap."""
    if MODE == 'paper' and not RUNTIME_FILE.exists():
        raise SystemExit('missing executor-runtime.hex (paper code override)')
    log('start', mode=MODE, executor=executor(), keeper=KEEPER, token=YOLOV, pair=PAIR, lead=read_lead())
    done_due = 0
    while True:
        try:
            due = uint_call(YOLOV, SEL_NEXT) + 1       # first block in which triggerDivRewards() passes
            head = head_number()
            left = due - head
            if due == done_due and left <= 0:          # this window was handled and is still untaken: look again later
                log('wait', due_block=due, head=head, note='handled_untaken')
                time.sleep(120)
                done_due = 0                           # still untaken after two minutes: one more look
                continue
            if left > TIGHT_BLOCKS:
                nap = max(1.0, (left - TIGHT_BLOCKS + 10) * BLOCK_S * 0.9)
                if nap > 60:
                    log('wait', due_block=due, head=head, blocks_left=left, sleep_s=round(nap))
                time.sleep(min(nap, 3600))
                continue
            window(due)
            done_due = due
            time.sleep(5)
        except ReadBudgetExceeded as e:
            log('read_budget', error=str(e))
            now = datetime.datetime.now(datetime.timezone.utc)
            time.sleep(86400 - (now.hour * 3600 + now.minute * 60 + now.second) + 5)   # to 00:00 UTC
        except Exception as e:
            log('loop_error', error=str(e)[:250])
            time.sleep(15)


if __name__ == '__main__':
    if len(sys.argv) > 2 and sys.argv[1] == '--selftest':
        # one simulated look on the state of block <parent> as if mined in <parent + 1> (paper override), no loop
        parent = int(sys.argv[2])
        print(json.dumps({'parent': parent, 'gain': gain_of(1, parent + 1, hex(parent))}))
    else:
        main()
