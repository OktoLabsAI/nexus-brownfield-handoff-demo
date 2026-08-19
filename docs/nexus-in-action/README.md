# Nexus in action — screenshots

Not yet captured for this scaffold. Once you run the walkthrough end to end,
save real screenshots here (PNG, descriptive filenames) covering:

- `approval-queue.png` — the pending `handoff_create` call sitting in the
  dashboard's approvals queue, SQL + Schema Agent's reasoning visible
- `claim-race.png` — both agents' `handoff_claim` attempts on the
  now-approved migration handoff, one accepted, one rejected, timestamps
  close enough to show it wasn't sequential
- `dependency-denial.png` — API Agent's early `handoff_claim` attempt on its
  own handoff, denied with the dependency error
- `recovery.png` — the killed session's replacement reading `handoff_get`/
  event history and finishing

Reference them from the main `README.md`'s "Nexus in Action" section once
they exist.
