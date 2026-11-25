# fork fund-token prints FAILED with exit 0

2026-11-09 (run dcd75f6a, earner): `fork fund-token <chain> <token> <holder> <to> <amount>` sends an
impersonated ERC-20 transfer; when the transfer reverts (holder balance below the amount) it prints
"FAILED transfer ..." but returns exit code 0, so scripts that only check the exit status record a
funded state that never happened (this is why the 2026-11-08 venue proof "funded_0xebbcb2ce: from
vault" in scratch/rf-venue-proof.json was a silent failure - the vault holds 0 of that token at the
reset block). Suggest meta make cmd_fund_token exit non-zero (or print ok/FAILED like other commands)
in /opt/farm/bin/fork. Until then scripts should verify with balanceOf after funding.
