# Prompt - API Agent, Stage 4: propose the dependent task, prove the block

Give this to the agent session connected as `api-agent`. Run this stage
concurrently with (or shortly after) Schema Agent's proposal - the point is
to show the dependency holding *before* the migration is done, not after.

---

You are API Agent. Your task is to build an admin endpoint,
`GET /api/admin/metrics`, that reports rate-limit activity - counts of
requests and blocks per route. It depends on the `RateLimitEvent` table that
Schema Agent is (or will be) adding via a separate handoff.

Do this:

1. Get the migration handoff's id from Schema Agent's proposal (ask them, or
   read it from the approvals queue / `scripts/04_list_and_approve.py`
   output). You need this id, not a guess - don't invent one.
2. Call `handoff_create` for your own task, with `depends_on` set to that
   migration handoff's id. Subject/description should describe the
   endpoint: what it queries, what it returns, following this fork's
   existing route conventions (read `docs/decisions/0001-fork-conventions.md`
   and an existing controller, e.g.
   `app/src/app/routes/article/article.controller.ts`, before writing
   anything).
3. Immediately try to claim your own handoff with `handoff_claim`. **This
   should fail** with something like `DEPENDENCY_NOT_MET`, because the
   migration handoff isn't `COMPLETED` yet. That failure is the expected,
   correct result - report it as success-of-the-mechanism, not as an error
   you need to work around.
4. Also call `handoff_list_available` and confirm your new handoff is
   *absent* from the list. If it's present, the dependency isn't actually
   gating anything and you should say so.
5. Stop here. Do not start writing the endpoint code yet - you have nothing
   real to query against until the migration exists. Wait for a signal
   (from a human, or by polling `handoff_get` on the migration handoff)
   that it's `COMPLETED` before moving to the next prompt
   (`04-api-agent-build-endpoint.md`).

As always: report the actual tool responses you got, not what you expect
them to say. If step 3 unexpectedly succeeds, that's a real finding - surface
it, don't paper over it.
