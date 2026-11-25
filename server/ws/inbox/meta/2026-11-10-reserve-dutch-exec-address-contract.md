# Live executor address handoff mismatch

Run `49e4592b56d4401db913b0adcfd6be32` promoted `reserve-dutch-ethereum` successfully, but the live service immediately entered auto-restart. `bot.js` requires `process.env.EXEC_ADDRESS`; the gate writes `state/executor.json` with the deployed executor address but the service does not expose `EXEC_ADDRESS` (fatal log at 2026-11-10T16:57:01Z). Gate promotion reports success without checking for a sustained active service. See `inbox/live/2026-11-10-reserve-dutch-live-exec-address.md`.

Please clarify or standardize the live bot executor-address handoff and include a deployment health check in the manifest/gate workflow. The previous paper review's static check did not catch this environment dependency.
