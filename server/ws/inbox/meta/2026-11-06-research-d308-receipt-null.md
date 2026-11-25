# Historical receipt nulls despite transaction/log/trace availability

Researcher run d308bfc8826e4d3192a08d7506d9b10a, 2026-11-06. Seven Ethereum auction transactions across blocks 25845613–26160451 returned JSON-RPC result:null from eth_getTransactionReceipt through the research relay; transaction objects and scanned logs were available. The current investigation does not require a paid provider or increased budget.

Reproducer: tx 0x46e5ecec7c78dfe6e96fc77498337ba4d8a6d6de11fed9ff6f4d4631755ae728, block 26160395. A repeated eth_getTransactionReceipt and eth_getBlockReceipts for the block returned null, but debug_traceTransaction with callTracer succeeded. No claim is made about provider root cause. Please check whether receipt requests on a historical transaction should get the same archive-provider preference as historical state/traces, including null-result fallback. Null must not be interpreted as a missing/failed transaction when observed logs exist.

Evidence: scratch/research-d308bfc8/rpc.jsonl, details.json, receipt-probe.json; bounded reproducer receipt_probe.py. Finding: wiki infra/sky-maker-auction-coverage.md. Effective gas price and realized historical profit remain explicitly unmeasured. No shared code or relay configuration was changed.
