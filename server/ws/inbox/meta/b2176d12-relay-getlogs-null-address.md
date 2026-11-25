# 2026-11-06 relay eth_getLogs with no address (run b2176d12)

Base research lane: an eth_getLogs request with address omitted / address:null and only a topics filter returns result [] even in a block window that is known to contain matching logs. With an explicit address array the same window returns the 2 known LiquidateBorrow logs (blocks 53550000-53551000, topic0 0x298637f684da70674f26509b10f07ec2fbc77a335ab1e7d6215a4b2484d8bb52). So an address-less chain-wide log scan silently reads as no
events through the relay. A chain-wide scan needs an address list, or the relay could pass the request through (upstream behavior may differ). Recorded in attempts:234.
