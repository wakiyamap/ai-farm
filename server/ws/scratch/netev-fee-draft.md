---
type: pitfall
chains: [base, ethereum, arbitrum]
protocols: []
---
# Net-EV at the lead stage must subtract the measured inclusion fee

Conclusion: the gross-vs-gas check that closes a collector class at the lead stage
(`decisions/human/2026-11-07-aave2-dust-ev.md`, rule 3) is only valid with the
inclusion fee **measured today on the target chain**, not with an assumed
"realistic" one. On Base the difference is 40x: an assumed 0.2 gwei prices
1.52M gas at 0.68 USD, while the fee measured on 2026-11-07 was the protocol
floor 0.005 gwei - 0.017 USD for the same gas at ETH/USD ~2230. A class whose
gross per capture is cents is dead under the assumed fee and marginally alive
under the measured floor, and only the measured number is evidence.

## What was measured

- Base `baseFeePerGas` = 0.005 gwei (the floor) at explicit blocks
  54265844, 54264704, 54259712, 54198272, 54132736 (relay research lane,
  timestamp span 30 h; the moonwell-whale-base bot comment recorded 0.0052 gwei
  from `feeHistory` already on 2026-11-06, and its paper log priced gas with
  `fee_includable_gwei` 0.0072 on 2026-11-07T09:28Z).
- Gas-per-capture anchor: 1,518,435-1,520,989 gas used by the reviewer-verified
  moonwell whale executor proofs (fork reset 53786332).
- The per-gwei price of gas at 1.52M gas and ETH/USD 2230: 1 gwei of basefee
  costs 3.4 USD per capture. A gross of 0.043 USD (the measured whale proof
  profit) breaks even at 0.013 gwei - above the floor, far below any
  historically "realistic" estimate.

## Pitfall history

The 2026-11-06/07 dust closures (cv2-dust gross 0.012-0.034 vs 0.15 gas,
aave2-dust gross 0.025 vs 0.2+ gas) hold at any fee including the floor: those
classes are dead whatever the fee. The same arithmetic applied with an assumed
floor of 0.02 gwei or more instead of the measured 0.005 flipped the moonwell
whale verdict to "negative after gas at any realistic inclusion fee"
(review 71396b4d), while the measured floor fee makes the same captures net
positive by 0.02-0.03 USD. Same numbers, opposite verdict, only from the fee
basis - so write the measured fee, with block numbers, into the row.

Rule for future leads: subtract `gasUsed x today's measured baseFee x today's
ETH/USD` per batch; call a class dead only when it cannot cover gas at the
measured floor; and note when a class is positive only at the floor - it earns
at floor and loses at congestion.
