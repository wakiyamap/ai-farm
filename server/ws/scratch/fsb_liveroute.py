def live_route_ready(ex, folio, buy, buyAmt, dst_quote, cost_usd, max_fee, log):
    """Live pre-bid route (review 2026-11-08T20:45Z blocker 2: funding and the bid must not be two
    transactions where the second can fail after the first spent the principal): prepare the
    funding leg of the SINGLE atomic fundSwapAndBid transaction the caller then sends. (a0) folio
    pin setup tx when the auction's folio is not pinned yet; (a1) if the executor's buyToken
    inventory is short of maxBuyAmount, quote the exact USDC->buyToken Fusion leg with taker = the
    executor and make sure the wallet's USDC allowance to the executor covers it (one small
    approve setup tx when short); nothing is sent here - fund = {usdcIn, minOutput (the quoted
    dstAmount), leg} rides inside the bid transaction, where a failed or under-delivering funding
    leg reverts the WHOLE route (the USDC stays in the wallet, worst case gas). (b) after-gas
    margin gate: quote margin valued at the quote's own implied USD price must exceed the signed
    gas cost, else no send; the bid carries minProfit = margin_raw, measured by the contract
    against the balance AFTER the funding leg (funding output is not bid profit).
    Returns (ok, reason, min_profit, fund)."""
    try:
        sys_path_fix()
        from farmbot_signer import send
    except Exception as e:
        return False, "live: signer import failed " + str(e)[:60], 0, {"usdcIn":0,"minOutput":0,"leg":"0x"}
    waddr = wallet_addr()
    if not waddr: return False, "live: no signer wallet address", 0, None
    # (a0) folio pin: the constructor pins two folios; a new folio gets one owner-only setFolio tx first.
    try:
        if h(call(ex, PIN_SEL + addr_word(folio))[2:]) == 0:
            r = send(chain="ethereum", to=ex, data="0x"+SETFOLIO_SEL+addr_word(folio)+w(1), gas=200000, max_fee_per_gas=max_fee)
            if not r.get("ok"): return False, "live: setFolio send failed " + str(r.get("error"))[:60], 0, None
    except Exception as e:
        return False, "live: folio pin read failed " + str(e)[:60], 0, None
    # (a1) executor inventory deficit -> prepare the funding leg (fundSwapAndBid pulls exactly
    # usdcIn USDC from the wallet, runs the taker=executor leg on the pinned swapper, and reverts
    # unless the buyToken balance rises by >= minOutput - all inside the bid transaction).
    fund = {"usdcIn": 0, "minOutput": 0, "leg": "0x"}
    bal_ex = relay_bal(buy, ex)
    if bal_ex is None: return False, "live: buyToken executor balance read failed", 0, None
    deficit = buyAmt - bal_ex
    usd_pu = fusion_quote_usd_per_unit(buy, log)  # USD per raw buyToken unit, from a 10-USDC probe quote
    if deficit > 0 and usd_pu is None: return False, "live: USDC->buyToken price quote failed (key-gated, fail closed)", 0, None
    if deficit > 0:
        usdc_units = int(deficit * usd_pu * 1e6) + 100  # ceil + 0.0001 USDC rounding allowance
        bal_w = relay_bal(USDC, waddr)
        if bal_w is None or bal_w < usdc_units: return False, "live: wallet USDC below funding cost", 0, None
        params = {"chain":"ethereum","fromToken":USDC,"toToken":buy,"fromAmount":str(usdc_units),
                  "fromAddress":ex,"toAddress":ex}   # taker = executor: the pull and the payout are the executor's
        u = FUSION_URL + "?" + urllib.parse.urlencode(params)
        try:
            req = urllib.request.Request(u, headers={"Authorization": fusion_key()})
            d = json.loads(urllib.request.urlopen(req, timeout=60).read())
        except Exception: return False, "live: funding quote failed", 0, None
        sw = d.get("swap") or {}
        fdata = sw.get("data") or ""
        dst_f = sw.get("dstAmount")
        if (sw.get("to") or "").lower() != SWAPPER or not fdata.startswith("0x") or not dst_f:
            return False, "live: funding swap shape", 0, None
        # the wallet must have approved the executor to pull this much USDC (one small approve tx when short).
        try:
            allow = h(call(USDC, "0xdd62ed3e"+addr_word(waddr)+addr_word(ex))[2:])  # allowance(address,address) (cast sig 2026-11-08)
        except Exception: return False, "live: USDC allowance read failed", 0, None
        if allow < usdc_units:
            r = send(chain="ethereum", to=USDC, data="0x095ea7b3"+addr_word(ex)+w(usdc_units), gas=60000, max_fee_per_gas=max_fee)
            log.write(json.dumps({"ts":int(time.time()),"event":"funding_approve","ok":bool(r.get("ok")),
                                  "units":usdc_units,"tx":r.get("transactionHash")})+"\n")
            if not r.get("ok"): return False, "live: USDC approve send failed", 0, None
        fund = {"usdcIn": usdc_units, "minOutput": int(dst_f), "leg": fdata}
        log.write(json.dumps({"ts":int(time.time()),"event":"funding_leg","usdcIn":usdc_units,
                              "minOutput":int(dst_f),"legLen":len(fdata)//2-4})+"\n")
    # (b) after-gas margin gate: the quote's expected payout must exceed the signed gas cost, else no send.
    if dst_quote is None: return False, "live: quote dstAmount missing (fail closed)", 0, None
    margin_raw = int(dst_quote) - buyAmt
    if margin_raw <= 0: return False, "live: quote margin not positive (dstAmount <= maxBuyAmount)", 0, None
    margin_usd = margin_raw * usd_pu
    if margin_usd < cost_usd: return False, "live: margin %.4f USD below gas %.4f USD (fail closed)" % (margin_usd, cost_usd), 0, None
    return True, "live: funding leg prepared + margin above gas", margin_raw, fund
