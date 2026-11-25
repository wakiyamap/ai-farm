#!/usr/bin/env python3
import subprocess
sigs = ["Redemption(uint256,uint256,uint256,uint256,uint256)",
        "TroveOperation(uint256,uint8,uint256,uint256,uint256,int256,uint256,int256)",
        "TroveOperation(uint256,uint8,uint256,uint256,uint256,int256,uint256,int256,uint256)"]
for s in sigs:
    h = subprocess.run(["/opt/foundry/bin/cast", "keccak", s], capture_output=True, text=True).stdout.strip()
    print(h, s)
