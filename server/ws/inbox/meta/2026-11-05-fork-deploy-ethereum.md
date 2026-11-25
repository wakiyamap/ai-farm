# fork tool problems observed on ethereum (run b4c50493, earner, 2026-11-05)

1. `fork reset ethereum <block>` and `fork replay` failed repeatedly for ~10 min
   with `anvil_reset: failed to get account ... historical state <root> is not
   available` (reset pinned the fork at 26342227); later the same tool reset to
   26342234 cleanly (gen 10) — looks like a transient relay research-lane state
   cache eviction. Also `eth_call` on the Pool at the fork's own head failed the
   same way during that window ("failed to get storage ... historical state
   b7d85a5a... not available").
2. Deploying a contract with constructor args + immutables on the fork:
   - `fork send <chain> '{"from":...,"data":<creation+args+immutables blob>}'`
     (no "to") returned status 0x1 with a contractAddress but **no code**
     deployed (eth_getCode 0x): the call behaved like a call to an empty address.
   - raw `eth_sendTransaction` over JSON-RPC to the fork URL returned result
     `null` (no error) — sends through the raw fork RPC seem filtered to the
     `fork send` wrapper only.
   - `fork deploy <chain> <file> [from]` with the exact solc deploydata
     (creation + 3 address args + 12 left-padded immutables words in code
     reference order) **reverted** (status 0, gasUsed ~190k, plain 0x revert
     reason), same via raw eth_call CREATE with to=null. The identical artifact
     deployed fine on the base fork earlier (tool deploy tx 0x2ffe533de080...).
     Hypotheses to check: fork deploy's gas cap vs 5044-byte initcode
     (~343k intrinsic), or the tool stripping/altering calldata past some limit
     (my deploydata is 10090 hex chars; the earlier base deploy hex was similar
     length). A `--force-gas` or trace of the deploy revert would settle it.

Update: also tried the immutables blob as 12 x 20-byte raw values (reference
order, matching the PUSH20 20-byte placeholder slots) — still status 0,
gasUsed ~190k, plain 0x revert (tx 0x060a1a53c727de9fc1000e8431b1c20839dd68d8117f2f29a0fcec80a9554c31).
Gas supplied by the tool was 7.87M (0x782830), so not OOG. Next session: try
`fork deploy` with the base artifact deploydata (the exact string from the base
session) on the ethereum fork as a control, or trace the constructor revert offset.
