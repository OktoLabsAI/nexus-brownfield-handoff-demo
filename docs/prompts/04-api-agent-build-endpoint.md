# Prompt — API Agent, Stage 6: build the endpoint, now unblocked

Give this to API Agent after Schema Agent (or the claim-race winner) has
called `handoff_complete` on the migration handoff — confirm that happened
via `handoff_get` before starting; don't take it on faith from a chat
message.

---

The migration handoff is now `COMPLETED` — confirm this yourself with
`handoff_get` on that handoff id before doing anything else. Once confirmed:

1. Call `handoff_claim` on your own dependent handoff (from the previous
   stage). This should succeed now — if it's still denied, stop and report
   that as a real problem, don't retry blindly.
2. Build `GET /api/admin/metrics` for real:
   - `app/src/app/routes/admin/admin.controller.ts` — queries
     `RateLimitEvent` via `@prisma/client`, returns per-route request/block
     counts.
   - Register the route in `app/src/app/routes/routes.ts`, following the
     existing router-registration pattern.
   - Follow the existing auth convention (`jsonwebtoken`/`express-jwt`) if
     other admin-ish or protected routes in this codebase require it — check
     an existing protected route before deciding.
   - Write a test (`admin.metrics.spec.ts` or wherever this repo's other
     route specs live) that actually exercises the endpoint against
     `RateLimitEvent` rows, not just a smoke test.
3. Run the test suite (`nx test`, per this repo's `package.json` scripts)
   and confirm it passes — read the actual output, don't assume.
4. Call `handoff_complete` on your handoff with a `result` string describing
   the real files you touched and confirmation the tests pass.

Same rule as every other stage: the `result` you report to `handoff_complete`
has to match what's actually on disk. If you're not sure a file was written
correctly, read it back before completing the handoff.
