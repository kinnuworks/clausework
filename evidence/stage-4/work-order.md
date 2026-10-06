# Stage 4 work order — tablekeeper (from lead)

## Context
- Result repository (git, branch main): /Users/kinnu/hackathon4/band-work/result-b . Do not edit mandates/. Write only inside the repo and in uniquely named scratch dirs under the system temp dir.
- Stage folder: /Users/kinnu/hackathon4/band-work/result-b/stage-4/ — starts as an unchanged copy of the FROZEN stage-3/ (tag stage-3-frozen); remove any nested .git; commit the copy unchanged first, then extend. stage-1/, stage-2/ and stage-3/ are frozen: never touch them again.
- Spec file (same text pasted below): /Users/kinnu/hackathon4/dark-factory-wearedevs/tablekeeper/spec/stage-4.md . stage-1.md, stage-2.md and stage-3.md (same directory) still apply in full — every earlier rule must still hold.
- This work order is committed at evidence/stage-4/work-order.md.
- Hard stop for the whole run is 09:00 local. Stage 4 window ends 08:52.

## Delivery rules
1. Each stage folder is a complete service that builds on its own: a Dockerfile, a RUN.md with the command that builds and starts it, and the source.
2. stage-4/ starts as a copy of stage-3/. Remove any nested .git directory from a copy.
3. Each folder is judged against every stage's checks up to its own number. A stage that breaks an earlier stage counts for nothing (stage-4 must pass stage 1, 2, 3 AND 4 checks).
4. Each folder holds that stage's solution and nothing from a later stage: stage 4 is the last stage. Never weaken, slow down or break correct behaviour to satisfy this rule.
5. Run-time: no outbound network; fonts, scripts and styles inside the image. Limits: 2 vCPU, 2 GiB, healthy within 60 s, 50 concurrent requests, 5 s/request (10 s reset).
6. Public repo. No credentials. No literal value assigned to a name ending in KEY, TOKEN, SECRET or PASSWORD in a Dockerfile or config file. No symlinks or submodules.
7. Supplied checks are a sample (~21% of stage 4's real suite). Build to the specification.

Cross-cutting rules from stage 1 (error body and code precedence, input validation, who may do what, idempotent replays, all-or-nothing writes, concurrency) apply to everything stage 4 adds: replans (preview), plan apply, closures, series amend. Existing availability, confirmation and lookup screens must reflect an applied plan.

Export compatibility: stage-4 must import exports from frozen stages 1-3 (including imported series with moved and cancelled occurrences); receipts, histories and retries stay valid.

## Check commands (black box; never open their source)
- Dev:       /Users/kinnu/hackathon4/factory/bin/check run tablekeeper /Users/kinnu/hackathon4/band-work/result-b 4
- Judging:   /Users/kinnu/hackathon4/factory/bin/check run tablekeeper /Users/kinnu/hackathon4/band-work/result-b 4 isolated
- Scratch:   /Users/kinnu/hackathon4/factory/bin/check build tablekeeper /path/to/folder 4
- Repo scan: /Users/kinnu/hackathon4/factory/bin/check repo tablekeeper /Users/kinnu/hackathon4/band-work/result-b  (ignore missing README.md, FACTORY.md, room.json)
- Line that matters: "claimed stage: 4 on the shipped checks" (there is no stage-5 probe).
- Tooling: /Users/kinnu/hackathon4/dark-factory-wearedevs/.venv/bin/python (pytest, httpx, playwright+chromium). Docker on PATH.

## Full specification text — stage-4.md

# Tablekeeper — Stage 4: seating changes and recurring amendments

Extends all earlier stages, including stage-1 atomic reservation moves, stage-2 table
combinations and stage-3 policies and recurring agreements. All earlier requirements apply.

## Seating changes after a table closure

When a table becomes unavailable, a manager can review a proposed seating arrangement
before applying it. Customers must keep their booking times, party sizes and accepted terms.
No new screens are required. Existing availability, confirmation and lookup screens must
reflect an applied plan.

`POST /restaurants/{id}/replans` requires a manager and an idempotency key. Body:

```json
{"table_id": "t_2", "from": "2026-09-28T18:00:00+02:00",
 "to": "2026-09-28T23:00:00+02:00"}
```

The instants have explicit offsets and `from < to`; invalid interval is 422
`validation_failed`, unknown table 404. The proposed closure is the half-open interval
`[from,to)`. Consider every confirmed booking at this restaurant overlapping that interval.
Other bookings retain their assignments.
Planning must support up to 6 tables, 4 declared pairs and 6 considered bookings; larger
inputs may return 422 `planning_limit`. Each considered booking must retain its reference,
owner, party size, start, end and accepted terms. Assign it a single or a declared pair with
enough capacity under **its own accepted terms**, without conflicts with fixed bookings,
other assignments, previously applied closures or the proposed closure. Diners' cancellation
cutoffs do not prevent an operator repair. No booking may disappear or be cancelled.

Among feasible plans minimize, in order:

1. Number of bookings whose table set changes.
2. Total unused seats across all considered bookings (capacity minus party size).
3. The vector of option ranks in ascending reservation-reference order. Singles are ranked
   first in fixture order, then pairs in declared order, starting at 0.

Returns 201:

```json
{"plan_id": "opaque", "restaurant_revision": 4,
 "closure": {"table_id": "t_2", "from": "...", "to": "..."},
 "assignments": [{"reference": "ABC12345", "table_ids": ["t_1"], "changed": true}],
 "moved_count": 1, "unused_seats": 0}
```

Assignments include every considered booking in reference order. A restaurant revision starts
at 0 after reset and increments once for each successful new booking, real amendment,
cancellation, policy publication or plan application. No-op writes, failures, previews and
replays do not increment it. Preview stores only a plan: no closure, occupancy, reservation
revision or history changes. No feasible plan gives 409 `no_feasible_plan`, changing nothing.

`POST /restaurants/{id}/replans/{plan_id}/apply`, body `{}`, requires a manager and an
idempotency key. Return 201 with `{"plan_id": "...", "restaurant_revision": 5,
"reservations": [...]}`; reservations include every considered booking in reference order.
Unknown plan or one from another restaurant is 404. Any intervening restaurant revision
invalidates the plan: 409 `stale_plan`, changing nothing. A plan already applied under a
different key gives 409 `plan_already_applied`; replay of the successful key returns the
original response with 200, even after later changes. Application is atomic.

Application records the closure and all assignments together. Each moved booking increments
its revision once and gains one `reassigned` history entry with a `table_ids` change and
`plan_id`; accepted terms and times remain identical. Unmoved bookings gain nothing. The
restaurant revision increments once for the **whole plan**. Closures thereafter exclude
singles and pairs from availability and reject creates/amendments with 409 `table_unavailable`.
In explanations, `no_overlap` is false for a closure as for a conflicting booking.

Concurrent applications must not leave partially moved bookings. A closure at another
restaurant does not invalidate this plan.

## Amend recurring reservations

`POST /series/{series_id}/amend` is an owner-only idempotent write. Unknown or another owner's
series is 404; no token is 401. Body:

```json
{"expected_revision": 3, "from_index": 2, "local_time": "20:00"}
```

Revision must be a positive integer; from_index an integer in 0..count-1; local_time exactly
HH:MM in 00:00..23:59. Booleans are invalid integers. Invalid input gives 422
`validation_failed`; a mismatched series revision gives 409 `stale_revision` before any
occurrence's cutoff or booking validation. Unknown fields are ignored.

Consider indices at or after from_index, excluding cancelled occurrences and those marked
exception. Change their clock time on their original scheduled local dates, retaining each
reference, owner, party size and current table selection. A change with identical
resulting fields is a no-op and retains its terms. Each real change checks its old accepted
cutoff, then adopts the policy for its resulting start date, just like an individual PATCH.

The resulting occurrences must not conflict with unchanged occurrences, other bookings
or applied closures. On failure, histories, idempotency records and all revisions remain
unchanged. Non-occupancy errors take precedence in occurrence-index order; otherwise an
occupancy conflict returns `table_unavailable`.

On success return 201 with the current series response. Each changed occurrence gains one
ordinary changed history entry and one reservation revision. The series and restaurant
revisions each increase once for the entire operation if anything changed. Series amendments
do not mark exceptions. All-no-op or empty eligible sets succeed without changing revisions.
Replay returns the original response with 200 even after further edits or cancellations.

Seating repairs may move series occurrences. They preserve their exception flags, scheduled
dates, identities and accepted terms. Each affected series revision increases once per plan
application if at least one member moved.
Concurrent amendments from the same expected revision may not both make a real change.

A stage-4 service must accept exports produced by the same team's stages 1–3. These
operations must support imported series, including moved and cancelled occurrences.
Earlier booking and series receipts, histories and retries remain valid.
