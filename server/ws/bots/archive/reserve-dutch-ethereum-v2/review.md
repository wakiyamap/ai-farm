decision: fix
run_id: d66440c3e53c44b5a5260c171709cd5b
reviewed_at: 2026-11-10T18:30:00Z
next_review_at: on resubmission after the executor and manifest are consistent
kb_attempt: attempts:832

The current submission is not deployable. `manifest-check` fails: `executor_args` has 2 words, while the current artifact constructor has 3 (`leg3Variant_`, `repayMode_`, `payoutVariant_`). The current artifact's deployed runtime is 6,842 bytes and differs from the pinned 6,099-byte `executor-runtime.hex`; `bot.js` checks that exact runtime in live mode, so the service would fail closed even after deployment. The Solidity source and artifact changed during this review, while the manifest and runtime pin still describe the older ETH+ payout version. No fork reproduction was run because the manifest failed the required first gate.

The manifest also lists a fork executor address and seven protocol addresses in `allowed_contracts`. This executor bot sends transactions only to its gate-deployed executor; set `allowed_contracts: []` as required by the current common instructions and `decisions/human/2026-11-11-executor-bots-funds.md` item 1. Update the manifest's constructor note and fork evidence for the exact final artifact. Then reproduce a profitable bid that credits **native ETH or USDC** to the bot wallet and a pre-settlement guard revert that returns principal, using the current artifact and 1,050,000-gas send cap. The latest recorded native payout attempt (`attempts:831`) reverted on its reverse leg; the current new payout selector has no successful proof in the manifest. Profit paid as ETH+ does not count toward X, the sweep, or the watchdog.

Paper detection is running: `logs/bot.jsonl` heartbeats advance from Ethereum block 26386202 at 18:07Z to 26386309 at 18:28Z with `active:0` and no error in those records. The latest ledger revenue settlement is block 26383398, before this v2 paper service started, so there is no new detection miss shown by these logs. Gate state was unfrozen, daily loss 5.14 USD. No promotion attempted.

Hashes at this review (SHA256): manifest `7ba959e04e73c42d04aa64cb5f6cba9bcbfca81757007b10c0be61bb5c5d2c79`; bot.js `7686342b494ca736e91b02772e942d01dd6c4c800854e9a4c2a0854c6731e51d`; run.sh `64d6cfea63c5db762cca048a9953f7a5bcf7cedb1b98f996e7a289e39d96389d`; executor source `dae48837c275b960f8171ddd6766cdbbe93bc0ecae661a25a7c8236374cb49cc`; artifact `4a03318d0d7db62df05aa534f4c0271927e4ee29ab3e54abb1822eb344ff6852`; runtime pin `1a90504badf0a23ca86805bd265c714e4e13950d7c4b25b50ab1a48d4a2aaca3`.

---

decision: fix

# Sent back by live-operator (run b9341ee958cf475eac5a04f629444514, 2026-11-10 ~17:05Z)

Code: the live copy is in `bots/archive/reserve-dutch-ethereum/` (the live-operator's shell could not copy files here). The earner should copy `bot.js`, `run.sh`, `manifest.yaml`, `executor-runtime.hex` and the contract source from there into this directory and make the fix below.

## What happened
- Promoted ~16:56Z (run 49e4592b). Gate deployed the executor `0x9abb8601e8352db4ee7a3ca35d1898775deee0ef` (tx 0x5fc20232961750847624c2528d0389a0a7b3b8486e5d3f13f9690e29a571d098) and funded 30 USD.
- The service crash-looped every ~20 s from 16:57:01Z: `fatal: live mode needs EXEC_ADDRESS and a signer address (exec=0x...d0c0 ...)`. It sent no bids.
- I ran `gate stop` at ~17:03Z. The gate swept 0.01229 ETH back. The realized loss is about 5.1 USD (executor deploy gas).

## Diagnosis
`bot.js` line 115/254/449 read `process.env.EXEC_ADDRESS`. The gate passes the deployed executor as **`EXECUTOR_ADDR`**, the variable every other live bot reads (moonwell-whale-base, gearbox-v3-watcher-ethereum, morpho-watcher-ethereum, franken-dutch-ethereum). It also writes the address to `state/executor.json`.

## Required fix
- Read `process.env.EXECUTOR_ADDR` and fall back to `state/executor.json` → `.ethereum.address`. In live mode, refuse to start if neither one is a valid 0x40-hex address. Never fall back to the sim address.
- Prefer franken-dutch-ethereum's pattern: check the deployed code at that address (eth_getCode) against the expected runtime before sending anything.
- Paper test: start with `MODE=live`-style env parsing in a unit check (no signer) that sets EXECUTOR_ADDR and asserts the bot picks it up.
- Note: a re-promotion deploys a new executor, so it costs the deploy gas again (~5 USD).
