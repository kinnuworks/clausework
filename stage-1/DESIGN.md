# Design note — tablekeeper stage 1

## What was chosen

- **Node.js, standard library only.** No packages, so the image needs nothing
  at run time beyond the base image. Time zones come from the runtime's IANA
  database (`Intl`), which handles DST for every zone.
- **One in-memory `Store`** (`src/store.js`) holds users, token digests,
  restaurants, reservations and idempotency receipts.
- **One serialized write path.** Every reservation write (create, amend,
  cancel, batch move) is a synchronous function that validates against the
  current state and only then mutates it. Node runs JavaScript on one thread,
  so no two of these functions ever interleave: the check and the write are a
  single indivisible step. No locks are needed, and none can be forgotten.
- **Plan, then commit.** Amendments and batch moves first build the complete
  new records off to the side (`planAmendment`), check occupancy for all of
  them together (`checkOccupancy`), and only then write them.
- **Receipts in the same step as the write** (`src/idempotency.js`). The
  receipt lookup, the write and the receipt store run in one synchronous step.
- **Whole-state replacement.** Reset and import build a complete new `Store`
  and swap it in with a single assignment.

## Rules guaranteed by construction

| Rule | Why it holds |
|---|---|
| No two confirmed reservations overlap on a table, even under concurrency | Check and write happen in one uninterruptible synchronous step |
| A failed amendment or batch changes nothing; a batch is all-or-nothing | Nothing is written until every item is planned and the joint occupancy check passes |
| Concurrent identical idempotent requests take effect once; one 201, others 200 | The first stores its receipt before any other request runs |
| Failed requests leave the key reusable | Receipts are stored only after the handler returns successfully |
| Replays return the original response after later changes | The receipt holds its own copy of the response body |
| Reset/import are atomic and invalid input changes nothing | A new Store is fully validated and built before the swap |
| Existing tokens survive export/import | Only SHA-256 token digests are stored, and they are exported |
| Passwords are never stored in plaintext | scrypt with a random salt per user |

## Other decisions

- Precedence for writes: authentication (401), then `Idempotency-Key`
  (400/422), then body parsing (400), then the idempotency receipt (200/409),
  then field types (400), field values (422), lookups (404) and booking rules.
- Booking rules are checked in this order: cancelled (409), cutoff (409),
  field values (422), table (404), `invalid_local_time`, opening hours / slot
  grid, capacity, and finally occupancy (409 `table_unavailable`).
- Local times resolve to the first occurrence on fall-back nights; skipped
  times are rejected and never listed. Durations are absolute time.
- Export format: `{track, format_version: 1, state}` where `state` lists
  every record with its original ids, references, timestamps, password hashes,
  token digests and idempotency receipts (with the original response bodies).
