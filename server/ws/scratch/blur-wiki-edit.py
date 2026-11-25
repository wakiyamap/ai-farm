p='scratch/blur-wiki-draft.md'
s=open(p).read()
old='* Sizing: debt per fill p10 0.113, median 0.86, max 5.61 ETH - a farm bot with <=400 USD capital (0.195 ETH at 2057.24 USD/ETH, Chainlink feed `0x5f4ec3df9cbd43714fe2740f5e3616155c5b8419`) only funds the ~10 percent smallest fills; the measured interest on exactly that subpopulation is 0.00055 ETH/day = 1.13 USD/day gross, on the 1 USD/day decision line.'
new=("* Sizing: debt per fill p10 0.113, median 0.86, max 5.61 ETH - a farm bot with <=400 USD capital "
"(0.195 ETH at 2057.24 USD/ETH, Chainlink feed `0x5f4ec3df9cbd43714fe2740f5e3616155c5b8419`) only funds the "
"~10 percent smallest fills. CORRECTED 2026-11-12 run bc8f9221 (attempt 969): that sizing EV was computed with "
"the hold time capped at the 9000-block auction duration; the capped subpopulation's own fills were paid at a "
"median 3363 blocks, and re-running the verified rate x t_next formula on the capped fills gives 0.0057 ETH/30d "
"= 0.39 USD/day gross, not 0.00055 ETH/day. The L cap is worse than the EV line: the worst case per take is the "
"debt paid into an underwater lien (default -> seize of collateral below debt), so the enforceable 50 USD/tx loss "
"cap bounds debt at 0.024 ETH - 1 census fill/month with ~0 interest. And the float must sit in the executor as "
"Pool units (neither native nor USDC), so the 30 USD watchdog stop bounds the parked principal at 0.0146 ETH. "
"The class is whale-scale: it pays 18.4 USD/day across 37 incumbent winners at median lien 0.79-0.86 ETH = "
"1630-1770 USD principal per take.")
assert old in s, 'sizing line not found'
s=s.replace(old,new)
old2='* `deposit()` called from an executor holding 0.19 WETH (tx `0x269aeaaa4b39910329b1c433fa79e50ddcf89aef9672b2f3816603d0c80ba897`, status 1) left the WETH in the executor and credited **no** Pool balance: the mint path real users take is still unmeasured. An executor bot must solve Pool-injection + allowance-for-Blend before its take can pull from its own balance; verify the unwrap path before counting on a native sweep.'
new2=("* `deposit()` called from an executor holding 0.19 WETH (tx `0x269aeaaa4b39910329b1c433fa79e50ddcf89aef9672b2f3816603d0c80ba897`, "
"status 1) left the WETH in the executor and credited **no** Pool balance: that test sent no native value. "
"RESOLVED run e80ea7d3 (attempt 960): the mint path is the payable `deposit()` **with native value** - "
"`deposit{value: 0.19e18}` from the fork executor minted 190000000000000000 Pool units 1:1, and no allowance is "
"needed for Blend to pull from the executor (Blend moved the debt itself). A native sweep back out works "
"(fork-proven wallet delta +80690127848445 wei, attempt 966).")
assert old2 in s, 'deposit line not found'
s=s.replace(old2,new2)
s=s.replace('updated: 2026-11-11','updated: 2026-11-12')
open(p,'w').write(s)
print('draft edited ok')
