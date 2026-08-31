# Prompt - API Agent, Stage 7: recovery after a killed session

This one is different from the others: it's meant to be given to a
**brand-new agent session** that has none of the context from stage 6 - no
chat history, no memory of what it (or rather, its predecessor identity) was
doing. That's the entire point of the stage.

Setup (do this yourself, outside the agent session, before starting):

1. Have API Agent claim its endpoint-building handoff and start work (or
   just run `python3 scripts/08_kill_and_recover.py start --handoff-id hof_...`
   directly instead of going through an agent session for this half).
2. Once it's `CLAIMED`, kill the process/session for real - not an idle
   timeout, an actual process termination (Ctrl+C, `kill`, closing the
   terminal). Confirm nothing is still running before continuing.

Then, in a **fresh** agent session (new conversation, new process, same
`api-agent` credentials), give it this:

---

You are API Agent. You have no memory of any prior session - treat this as
your first message in this workspace. There may be work already claimed
under your identity from a session that no longer exists. Find out what it
is before doing anything else:

1. You don't know any handoff IDs yet. Call `handoff_list_available` and
   also check what's currently claimed under your identity - if there's no
   direct "list my claims" tool, use `event_get`/`event_cursor` on the
   `handoff` stream to find the most recent `handoff.claimed` event for
   `api-agent` and pull its `handoff_id` from there.
2. Call `handoff_get` on that handoff id. Read its current state, its
   description, and anything in its result/notes fields.
3. Replay the event history for it via `event_get`/`event_cursor` to
   reconstruct what happened before you existed as this session - what was
   claimed, when, and whether any partial work was recorded.
4. Cross-reference against the actual filesystem: does
   `app/src/app/routes/admin/admin.controller.ts` already exist? Is it
   complete? Don't assume the prior session finished or didn't - check.
5. Finish the task for real (following `04-api-agent-build-endpoint.md` for
   whatever's left undone), then call `handoff_complete`.

Everything you know about this task has to come from Nexus's own record or
the actual filesystem - not from an assumption about what a previous session
"probably" did.
