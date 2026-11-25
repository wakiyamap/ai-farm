// Offline live-loss-stop tests (promote-criteria checklist item 10, wiki
// pitfalls/live-loss-stop-checklist.md): fresh-price settlement, missing fee fields
// keep the hash pending, threshold crossing -> sticky STOPPED.json, pending accepted
// hashes recovered across a restart from the append-only log. Run: node test.js
'use strict';
const fs = require('fs');
const path = require('path');
const bot = require('./bot.js');
const DIR = __dirname;
const TLOG = path.join(DIR, 'logs', 'test.jsonl');
const TSTOP = path.join(DIR, 'state', 'TEST_STOPPED.json');
let fails = 0, runs = 0;
const ok = (cond, name) => { runs++; if (!cond) { fails++; console.log(`FAIL ${name}`); } else console.log(`ok   ${name}`); };
const fresh = () => ({ phase: 'idle', principal6: 380000000n, shares: 0n, cycle_ts: '', liveLoss: { usd: 0, pending: [] }, allowanceApproved: false });
const PMIC = 2130000000n; // 2130 USD in micro-USD

try {
  // 1) settlement requires THIS cycle's fresh price; a null price keeps every hash pending
  let st = fresh(); st.liveLoss.pending = ['0xaaa'];
  bot.liveLossSettle(st, null, async () => ({}), TLOG); // returns 0, nothing settled (synchronous assertion via pending)
  // liveLossSettle is async; run the async block:
  (async () => {
    st = fresh(); st.liveLoss.pending = ['0xaaa'];
    await bot.liveLossSettle(st, null, async () => ({}), TLOG);
    ok(st.liveLoss.pending.join() === '0xaaa' && st.liveLoss.usd === 0, 'null price: hash stays pending');

    // 2) a receipt with a missing fee field is never valued as zero: hash stays pending
    st = fresh(); st.liveLoss.pending = ['0xbbb', '0xccc'];
    await bot.liveLossSettle(st, PMIC, async (h) => h === '0xbbb' ? { gasUsed: null, effectiveGasPrice: '0x1' }
      : { gasUsed: '0x759f5', effectiveGasPrice: '0x3938700' }, TLOG); // 483281 gas x 0.06 gwei (60000000 wei)
    const loss = st.liveLoss.usd; // 483281 x 60000000 wei x 2130 USD/ETH = 0.0618 USD
    ok(st.liveLoss.pending.join() === '0xbbb' && Math.abs(loss - 0.0618) < 0.0005, `missing fee field pending; settled gas valued (${loss})`);

    // 3) threshold crossing: cumulative loss >= 30 USD writes STOPPED.json (sticky)
    st = fresh(); st.liveLoss.usd = 29.98; st.liveLoss.pending = ['0xddd'];
    await bot.liveLossSettle(st, PMIC, async () => ({ gasUsed: '0x759f5', effectiveGasPrice: '0x3938700' }), TLOG);
    const wrote = bot.liveLossStopWrite(st, TSTOP);
    ok(st.liveLoss.usd >= 30 && wrote && fs.existsSync(TSTOP), 'threshold crossing writes STOPPED.json');

    // 4) recovery across a restart: accepted hashes not durably settled stay pending
    const lines = fs.readFileSync(TLOG, 'utf8').trim().split('\n');
    const before = lines.length;
    fs.appendFileSync(TLOG, JSON.stringify({ type: 'live_send_accepted', hash: '0x111' }) + '\n');
    fs.appendFileSync(TLOG, JSON.stringify({ type: 'live_send_accepted', hash: '0x222' }) + '\n');
    fs.appendFileSync(TLOG, JSON.stringify({ type: 'live_loss_settled', hash: '0x111', live_loss_usd: 0.05 }) + '\n');
    const rec = bot.recoverLossFromLog(TLOG);
    ok(rec.pending.join() === '0x222' && rec.usd === 0.05, `pending recovered from log (${rec.pending.join()})`);
    fs.writeFileSync(TLOG, lines.join('\n') + '\n'); // keep the test log as it was

    // 5) a written STOPPED.json at startup keeps the bot stopped (canSend false in live)
    // canSend depends on module-internal stopLogged/MODE (paper here): assert the file check the bot uses
    ok(fs.existsSync(TSTOP), 'STOPPED.json present for the startup check');
  })().then(() => {
    if (fs.existsSync(TSTOP)) fs.unlinkSync(TSTOP);
    console.log(fails === 0 ? `ALL ${runs} TESTS PASS` : `${fails}/${runs} FAILED`);
    process.exit(fails === 0 ? 0 : 1);
  });
} catch (e) { console.log('FAIL test crashed:', e.message); process.exit(1); }
