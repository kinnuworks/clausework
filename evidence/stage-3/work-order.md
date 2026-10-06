# Stage 3 work order — tablekeeper (from lead)

## Context
- Result repository (git, branch main): /Users/kinnu/hackathon4/band-work/result-b . Do not edit mandates/. Write only inside the repo and in uniquely named scratch dirs under the system temp dir.
- Stage folder: /Users/kinnu/hackathon4/band-work/result-b/stage-3/ — starts as an unchanged copy of the FROZEN stage-2/ (tag stage-2-frozen); remove any nested .git; commit the copy unchanged first, then extend. stage-1/ and stage-2/ are frozen: never touch them again.
- Spec file (same text pasted below): /Users/kinnu/hackathon4/dark-factory-wearedevs/tablekeeper/spec/stage-3.md . stage-1.md and stage-2.md (same directory) still apply in full — every earlier rule must still hold.
- This work order is committed at evidence/stage-3/work-order.md.
- Hard stop for the whole run is 09:00 local. Stage 3 window ends 08:38.

## Delivery rules
1. Each stage folder is a complete service that builds on its own: a Dockerfile, a RUN.md with the command that builds and starts it, and the source.
2. stage-3/ starts as a copy of stage-2/. Remove any nested .git directory from a copy.
3. Each folder is judged against every stage's checks up to its own number. A stage that breaks an earlier stage counts for nothing (stage-3 must pass stage 1, 2 AND 3 checks).
4. Each folder holds that stage's solution and nothing from a later stage: no stage-4 features (no replans/closures/plan apply, no POST /series/{id}/amend, no restaurant_revision in responses). Never weaken, slow down or break correct behaviour to satisfy this rule.
5. Run-time: no outbound network; fonts, scripts and styles inside the image. Limits: 2 vCPU, 2 GiB, healthy within 60 s, 50 concurrent requests, 5 s/request (10 s reset).
6. Public repo. No credentials. No literal value assigned to a name ending in KEY, TOKEN, SECRET or PASSWORD in a Dockerfile or config file. No symlinks or submodules.
7. Supplied checks are a sample (~11% of stage 3's real suite). Build to the specification.

Cross-cutting rules from stage 1 (error body and code precedence, input validation, who may do what, idempotent replays, all-or-nothing writes, concurrency) apply to everything stage 3 adds: explain, history, decision, policies, expected_revision, series. The stage-2 screens must keep working (grid follows policies).

Export compatibility: stage-3 must import exports from frozen stage-1 and stage-2 (tokens, references, receipts, retries stay valid; imported reservations can be adopted into a series; seeded/imported bookings start at revision 1 under policy 0).

## Check commands (black box; never open their source)
- Dev:       /Users/kinnu/hackathon4/factory/bin/check run tablekeeper /Users/kinnu/hackathon4/band-work/result-b 3
- Judging:   /Users/kinnu/hackathon4/factory/bin/check run tablekeeper /Users/kinnu/hackathon4/band-work/result-b 3 isolated
- Scratch:   /Users/kinnu/hackathon4/factory/bin/check build tablekeeper /path/to/folder 3
- Repo scan: /Users/kinnu/hackathon4/factory/bin/check repo tablekeeper /Users/kinnu/hackathon4/band-work/result-b  (ignore missing README.md, FACTORY.md, room.json)
- Line that matters: "claimed stage: 3 on the shipped checks". Stage 4 checks run as a probe and should FAIL.
- Tooling: /Users/kinnu/hackathon4/dark-factory-wearedevs/.venv/bin/python (pytest, httpx, playwright+chromium). Docker on PATH.

## Full specification text — stage-3.md

# Tablekeeper — Stage 3: booking policies, history and recurring reservations

The requirements from stages 1 and 2 continue to apply, with the additions below.
Numbered section references such as §5 and §7 refer to `stage-1.md`.

Restaurants can publish dated booking policies. Diners can see why a table is unavailable,
view their reservation history and arrange recurring bookings.

## Availability explanations

Whether a table is available for a slot is decided by two rules, each independent of the other:

| Rule | Holds when |
|---|---|
| `capacity` | `party_size` is at most the table's `capacity` |
| `no_overlap` | no confirmed reservation on that table overlaps the slot's interval |

A table is available exactly when both hold. `available_table_ids` is unchanged in meaning.

```http
GET /availability?restaurant_id=r_anker&date=2026-09-24&party_size=4&explain=true
```

`explain` is optional. Its only accepted value is `true`; any other value, including `false`,
`1` and the empty string, is 422 `validation_failed`. **Without it the response keeps stage
1's shape** — no explanation fields appear. Published policies can change the slot values.

With it, every slot carries one further field:

```json
{ "starts_at_local": "2026-09-24T18:00",
  "starts_at": "2026-09-24T18:00:00+02:00",
  "available_table_ids": ["t_2"],
  "explain": [
    { "table_id": "t_1", "policy_version": 0, "available": false,
      "rules": [ { "rule": "capacity", "holds": false },
                 { "rule": "no_overlap", "holds": true } ] },
    { "table_id": "t_2", "policy_version": 0, "available": true,
      "rules": [ { "rule": "capacity", "holds": true },
                 { "rule": "no_overlap", "holds": true } ] }
  ] }
```

1. **Every table of the restaurant appears exactly once**, available or not, in fixture order —
   the same order `available_table_ids` uses.
2. **Both rules are reported for every table**, in the order above. A rule that holds is
   reported holding; a table excluded by both reports both false. No rule may be omitted.
3. **`available` is true exactly when both rules hold**, and the `table_id`s whose `available`
   is true are exactly `available_table_ids`, in the same order.
4. A closed day still returns `"slots": []`, and a slot with no available table still appears —
   now with a full `explain` for every table.

## Reservation history

```http
GET /reservations/{reference}/history
```

The reservation's own record, oldest first. Only its owner may read it; anyone else, signed in
or not, gets the same 404 `not_found` that §8 gives for a reservation that is not theirs. A
cancelled reservation still has its history.

The example below shows the event fields; every entry also carries `revision` and
`accepted_terms` as specified under “Policies and accepted terms”.

```json
{ "reference": "ABC12345",
  "entries": [
    { "seq": 1, "at": "2026-09-17T12:00:00+02:00", "event": "created",
      "changes": [ { "field": "table_id", "from": null, "to": "t_2" },
                   { "field": "starts_at_local", "from": null, "to": "2026-09-24T19:00" },
                   { "field": "party_size", "from": null, "to": 4 } ] },
    { "seq": 2, "at": "2026-09-17T12:05:00+02:00", "event": "changed",
      "changes": [ { "field": "table_id", "from": "t_2", "to": "t_3" } ] },
    { "seq": 3, "at": "2026-09-17T12:09:00+02:00", "event": "cancelled", "changes": [] } ]
}
```

1. **`seq` starts at 1 and increases by exactly 1**, so the order is total even when two writes
   land in the same second. Entries are returned in `seq` order, which is also `at` order.
2. **`created` names all three fields**, each with `"from": null`.
3. **`changed` names only the fields that actually changed**, in the order `table_id`,
   `starts_at_local`, `party_size`. A `PATCH` that sets a field to the value it already has
   changed nothing: it still succeeds, and it records **no entry at all**.
4. **`cancelled` carries an empty `changes`**, and nothing follows it.
5. Replaying an idempotent `POST /reservations` records nothing — a replay returns the original
   response and does not re-run the operation (§7).

## Existing screens

No new screens are required for explanations or history. The availability grid continues
to follow the stage-2 rules.

## Policies and accepted terms

Restaurants may now declare `manager_user_ids` in their reset fixture (default `[]`). Only
these users may publish policies. Unknown restaurant is 404;
an authenticated non-manager is 403 `forbidden`; no token is 401. This extends stage 1's
minimal permissions; managers do not gain access to other diners' private lookup/history.

`POST /restaurants/{id}/policies` requires an idempotency key, with stage 1's replay rules.
It accepts a **complete policy**, not a patch:

```json
{
  "effective_from": "2026-09-28",
  "slot_minutes": 30,
  "reservation_duration_minutes": 120,
  "cancellation_cutoff_minutes": 60,
  "opening_hours": [{"weekday": "mon", "opens": "18:00", "closes": "23:00"}],
  "capacities": {"t_1": 2, "t_2": 4, "t_3": 6}
}
```

Returns 201 with the supplied policy plus `policy_version`, an integer starting at 1 and
increasing by one per restaurant. Failed writes and replays allocate no version. Policy 0
is the original fixture's rules and applies before any published policy. Policies are
immutable. Publication order may differ from effective-date order. For a booking's **local
start date**, choose the greatest `effective_from` not later than that date; ties choose
the greatest `policy_version`. A new same-date policy supersedes the old one for future
decisions, without changing any accepted reservation. Effective dates may be in the past;
publication never retroactively edits a booking.

All fields above are required. `effective_from` is an actual `YYYY-MM-DD` date; grid and
duration are integers 1..1440; cutoff is an integer 0..10080; booleans are not integers.
Opening hours follow stage 1 and contain no duplicate weekdays. `capacities` names **exactly**
the restaurant's table ids with integer capacities 1..100. Invalid policy is 422
`validation_failed`, with no version or state change. Table ids, labels, timezone and
declared combinations cannot be changed by a policy. Unknown fields are ignored.

`GET /restaurants/{id}/policies` is public and returns `{"policies": [...]}` in publication
order, omitting policy 0. The ordinary restaurant detail still returns its original fixture
configuration. Availability and booking decisions use the selected policy, not that detail.
With `explain=true`, each table explanation additionally identifies its `policy_version`.

Every reservation response gains `revision` (1 at creation) and `accepted_terms`:

```json
{"policy_version": 0, "slot_minutes": 30,
 "reservation_duration_minutes": 90, "cancellation_cutoff_minutes": 120,
 "opening_hours": [{"weekday": "mon", "opens": "18:00", "closes": "23:00"}],
 "capacities": {"t_1": 2, "t_2": 4, "t_3": 6}}
```

These are a snapshot of the entire selected policy, excluding `effective_from`. Seeded
bookings start at revision 1 under policy 0. Responses to old idempotency keys remain the
original response, including the original revision and terms.

- A policy publication does not change existing bookings, their end times, or their history.
- Cancel checks the accepted cutoff, against the current start.
- A real diner amendment (time, tables or party size) checks the old accepted cutoff first,
  then validates **all** resulting fields against the policy applicable to the resulting start
  date. It atomically replaces accepted terms and end time and increments revision once.
- A no-op amendment retains terms, end time and revision and records no history. It still
  requires a confirmed, editable booking.
- Failed amendments change nothing. Cancel increments revision once; repeated cancel does not.
- `PATCH` optionally accepts `expected_revision`. A positive integer differing from the current
  revision gives 409 `stale_revision` before cutoff/validation; invalid type/range gives 422.
  Omission retains stage 1 semantics. Two concurrent amendments using one revision: at most one
  real change succeeds. Unrelated unknown fields remain ignored.

Each history entry additionally carries the reservation's resulting `revision` and complete
`accepted_terms`. Old entries never acquire newer terms. `GET /reservations/{reference}/decision`
returns `{"reference": "...", "revision": 1, "accepted_terms": {...}}` for the current booking,
including after cancellation, with history's owner-only 404 rule. History and decision return
404 even without authentication, resolving the exception to stage 1's general 401 rule.

## Recurring reservations

`POST /series` adopts an existing reservation as occurrence zero of a recurring agreement.
An idempotency key is required. Body:

```json
{"anchor_reference": "ABC12345", "count": 8, "interval_weeks": 1}
```

The anchor must belong to the caller, be confirmed and satisfy its accepted cancellation
cutoff. Unknown or another owner's anchor gives 404 `not_found`; cancelled gives 409
`reservation_cancelled`; already adopted gives 409 `already_in_series`. `count` is an integer
2..12 including the anchor; `interval_weeks` is an integer 1..4. Invalid values, including
booleans, give 422 `validation_failed`. No token gives 401.

Occurrence zero is the anchor itself: its reference, identity, revision, terms, history,
timestamps and original idempotent response remain unchanged. Occurrence i starts on the
anchor's local calendar date plus i × interval_weeks × 7 days, at the same local clock time.
Each generated occurrence independently selects its date's policy, including duration and
capacity, and obeys ordinary opening, DST and occupancy rules. A nonexistent local time
rejects the entire adoption with `invalid_local_time`; repeated times use stage 1's first
occurrence rule. Generated occurrences use the anchor's party size and table selection.
No partial series, reservations, histories, counters or idempotency claim survive failure.
The first failing occurrence in index order determines the ordinary booking error.

Return 201:

```json
{"series_id": "opaque", "revision": 1, "interval_weeks": 1,
 "occurrences": [{"index": 0, "reference": "ABC12345", "exception": false,
                  "reservation": {"...": "ordinary reservation response"}}]}
```

The array includes all count occurrences in index order. Each has a distinct ordinary
reservation reference; references and indices never change when dates or tables change.
Occurrences appear in ordinary reservation lists, occupy tables, and have ordinary histories.
`GET /series/{series_id}` returns this shape with current reservation states. Only the owner
may read it: another user or no token gives 404 `not_found`.

A real individual PATCH permanently marks that occurrence as `exception: true` and increments
the series revision once; a no-op or failure changes neither. Cancellation increments the
series revision once, retaining the cancelled occurrence, but does not mark it as an
exception; repeated cancel does nothing.
Cancelling the anchor does not cancel its siblings. Ordinary cutoff and revision checks still
apply. Adoption increments the restaurant revision once for the whole operation. Replays
return the original series response, even after later changes, and change no counter.
Series creation adds one idempotent write path. Unknown fields are ignored.

A stage-3 service must accept exports produced by the same team's stage-1 or stage-2
service. Adoption must work on reservations imported this way. Existing confirmation links,
sessions and original booking retries remain valid.

## Combined-table history

Stage 3's accepted terms apply to combinations too; capacity is the sum of the **selected
policy's** capacities. In history, retain stage-3 fields for single-to-single operations.
For a creation of a pair, replace the `table_id` change by `table_ids` (from null to the pair).
For a change involving a pair, use `table_ids` (complete before/after lists) instead of
`table_id`. Table-set order is the declared combination order. A reversed input pair names
the same set and is not an amendment on its own. Policy selection, revision and replay rules
are unchanged.

## Collective moves under policies and agreements

Each real change in `POST /reservation-moves` uses individual PATCH semantics: check the
old accepted cutoff, then adopt the resulting date's policy. Per-move `expected_revision`
is optional and follows PATCH validation and stale-revision rules. A no-op retains its
terms and history. All resulting bookings must satisfy amendment and occupancy rules;
failure leaves every booking unchanged. Every changed booking gains one revision and
changed history entry; the restaurant revision increases once for the whole batch.
Each affected series revision increases once,
and each changed series occurrence becomes a permanent diner exception. A
failed batch or replay changes no revisions, histories or exception flags.
