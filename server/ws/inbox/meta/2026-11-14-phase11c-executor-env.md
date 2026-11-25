# phase 11c: live bots now really get EXECUTOR_ADDR (human, 2026-11-14)

## What was wrong
- Role files and the gate's promote check (10e) say a live bot reads the executor address from
  the environment variable EXECUTOR_ADDR, else from state/executor.json.
- Nothing ever set that variable. bot@.service started run.sh with BOT_MODE, BOT_ID, RPC_LANE,
  RPC_RELAY_URL and SIGNER_SOCK only.
- A bot written as `process.env.EXECUTOR_ADDR || '<address deployed on the fork>'` passed the
  check, then ran live with the fork address. The signer refuses that address, so such a bot
  could never send. Found on morpho-nextblock-ethereum (reviewer note in inbox/live, 2026-11-13).
  gearbox-v3-watcher-ethereum has the same line (bot.js:76) and had the same environment.

## What changed
- bot@.service now starts /opt/farm/bin/bot-run, which reads state/executor.json, sets
  EXECUTOR_ADDR_<CHAIN> for every chain in it and EXECUTOR_ADDR when all chains have the same
  address, then runs run.sh. The file wins over a value already in the environment.
- Live bots with an executor were restarted by the installer. No redeployment, no gas.

## For the role files (meta decides the wording)
- A live period of a bot that started before 2026-11-14 with only the EXECUTOR_ADDR-or-fork
  pattern is not evidence about its opportunity: it could not send. This covers
  gearbox-v3-watcher-ethereum since its promotion. Do not close a lead on "live, zero sends"
  from that period.
- New bots: in live mode, exit with a clear message when the executor address is missing instead
  of falling back to a fork address. Multi-chain bots read EXECUTOR_ADDR_<CHAIN>.
- Reviewer, after a promote: the first lines of the live log must show the address in
  state/executor.json. If they do not, write to inbox/human at once (as was done here).
