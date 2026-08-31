# Prompt - winning agent, Stage 5: apply the migration for real

Give this to whichever agent identity won `scripts/05_claim_race.py` - check
the script's output for `outcome: claimed` before starting; don't assume it
was Schema Agent just because Schema Agent proposed it.

---

You won the claim on the migration handoff. It's yours to apply - for real
this time, not the proposal draft from stage 1.

1. Call `handoff_get` on the handoff id and re-read the SQL/reasoning from
   its `description`. Confirm it matches what you (or the other agent)
   proposed - don't apply something you haven't actually read.
2. In `app/`, add the Prisma model to `schema.prisma` and generate the real
   migration:
   ```
   npx prisma migrate dev --name add_rate_limit_event
   ```
   This requires the Postgres from `docker-compose.yml` to be running and
   `DATABASE_URL` set (see `.env.example`).
3. Confirm on disk that `app/src/prisma/migrations/<timestamp>_add_rate_limit_event/migration.sql`
   exists and its contents are real - don't just trust the command's exit
   code, actually read the generated file back.
4. Optionally record the applied SQL as an artifact for the record (not
   policy-gated): call `artifact_put` with the migration SQL, or use
   `scripts/07_complete_and_unblock.py --record-artifact --sql-file <path>`.
5. Call `handoff_complete` on the migration handoff (or run
   `scripts/07_complete_and_unblock.py`) with a `result` string that
   describes exactly what you did and where - the real file path, not a
   generic "migration applied" statement.

Do not call `handoff_complete` before step 2–3 are actually true on disk.
The whole point of this stage is that the coordination call and the real
work match - verify the file exists before you claim it does.
