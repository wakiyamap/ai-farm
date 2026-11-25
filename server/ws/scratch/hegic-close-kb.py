import json
from pathlib import Path

root = Path('/srv/farm/ws/scratch')
target = 'hegic stakeandcover claimProfit'
evidence = (
    'Verified explorer source contracts/Pool/HegicStakeAndCover.sol: '
    'claimProfit() at lines 155-160 calls profitOf(msg.sender) and _withdraw; '
    'profitOf at lines 119-125 is shareOf(account)-startBalance[account], '
    'where shareOf is proportional to the caller\'s HEGIC deposit. '
    'At lines 163-175 _withdraw reduces that HEGIC balance and sends HEGIC '
    'to the contract admin while sending USDC to the caller. '
    'Paid tx 0xa39ed9f7ddf5265101b72a0573f1c19f2c1205f29fe2dabb5616b99322655fba '
    'transferred 659.455278207487333545 HEGIC from pool to admin '
    '0xf15968a096fc8f47650001585d23bee819b5affb and 17.579816 USDC '
    'from pool to caller 0x26a6dc267e276fded7b40251c8fc08b1b40df367. '
    'Fresh 0x1111111111111111111111111111111111111111 eth_call profitOf returned 0; '
    'claimProfit reverted "The claimable profit is zero". '
    'Raw outputs: scratch/hegic-{getter,profit-fresh,claim-fresh,paid-receipt}.json.'
)
(root / 'hegic-attempt.json').write_text(json.dumps({
    'chain': 'arbitrum', 'target': target, 'outcome': 'dead_end_recorded',
    'reason': 'No permissionless keeper reward. claimProfit realizes only the caller\'s own staked share and consumes HEGIC; fresh address has no claim. A bot cannot copy an incumbent claim or earn by claiming someone else\'s position. No executor or paper bot warranted. ' + evidence,
    'numbers': 'Paid tx: 17.579816 USDC out, 659.455278207487333545 HEGIC debited; this is not 17.58 USD of unencumbered profit. Gas used 115,423 (receipt 0x1c2df).'
}))
(root / 'hegic-lead-update.json').write_text(json.dumps({
    'chain': 'arbitrum', 'target': target, 'status': 'dead_end',
    'next_steps': 'Closed 2026-11-19: only revisit if Hegic adds a separate public reward paid to a third-party caller. ' + evidence
}))
old = json.loads((root / 'hegic-protocol-row.json').read_text())
(root / 'hegic-protocol-update.json').write_text(json.dumps({
    'chain': 'arbitrum', 'protocol': 'hegic', 'status': 'dead_end',
    'checked': old['checked'] + ' CORRECTION 2026-11-19: claimProfit payout is not free yield: it consumes the caller\'s HEGIC balance and sends those tokens to the admin; see attempts for this run. ' + evidence
}))
