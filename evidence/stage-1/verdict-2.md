# Stage 1 — verdict, round 2

**ACCEPT**: revision `fa79f76b173218d7035fa00f52494e37dcdd2a3f` (main), folder `stage-1/`, round 2.
Inspector, 2026-10-06. Round-1 failure F1 is fixed, and nothing that passed in round 1 has broken.

## Evidence gathered

| Step | Result |
|---|---|
| Clean copy | `git archive fa79f76 stage-1` exported to `/tmp/insp-s1r2-xael/`. `stage-1/` is identical at fa79f76 and at HEAD 1f9eb45 (empty diff). Change from 85374cb covers only `src/{idempotency,reservations,secrets,store}.js`. No nested .git, no symlinks, no HTML. |
| **F1 smallest input, re-run first** | `POST /reservations`, body `{"x":` + 3000×`[` + 3000×`]` + `}` → **422 validation_failed** ("restaurant_id is required"). The same nesting on `/reservation-moves` → 404 (unknown reference X; field ignored). Depths 3 000–100 000 for arrays, and nesting with all required fields present → 201/409 as expected, never 5xx. The container log has no errors. |
| Delivery rule 1 | PASS. Dockerfile, RUN.md and source are present, and the RUN.md command is unchanged. |
| `check build … /tmp/insp-s1r2-xael/stage-1 1` | stage 1: pass |
| `check run … 1 isolated` | stage 1 **120/120** passed, 0 failed. The stage-2 probe **FAILS**, as required. "claimed stage: 1 on the shipped checks". Report: band-work/checks/1006-065737-9671. |
| `check repo` | Only the 3 complaints that may be ignored (README.md, FACTORY.md, room.json). |
| Delivery rule 4 | PASS. No screens; the only `table_ids` is stage-1 `available_table_ids`; the stage-2 checks fail. |
| Delivery rule 5 | PASS. Run with `--cpus 2 --memory 2g`: healthy in about 1 s. `/health` works inside the container with `--network none`. 50 concurrent logins all return 200, 0.19 s in total. A reset with 402 seeded users takes 2.40 s (limit 10 s). |
| Delivery rule 6 | PASS. No credentials, and nothing is assigned to a name ending in KEY/TOKEN/SECRET/PASSWORD. |
| Examiner probes | The seal recomputes to `9901cc05…bd5b993`, which matches. **53/53 passed** against the clean-export container. The F1 probe the lead asked for is not yet in the probe set; my own re-run covers it. |

## Re-checks of the changed code (inspector r2.py)

- Replays with deep bodies still work. Same deep body → 200 with an identical body. A different deep body → 409. Reordered keys at the top level and nested → 200. A `\u0061` escape equal to `a` → 200. `1.0` vs `1` → 200 (same JSON value). A `1` vs `"1"` value change → 409.
- A flat 2-million-element array (3.9 MB) gets 201 in 0.92 s and its replay gets 200 in 0.68 s, both inside the 5 s limit.
- Moves precedence follows the examiner's ruling S1-97, in input order. [cancelled, unknown] → 409 reservation_cancelled. [unknown, cancelled] → 404. [own party 9, another owner's] → 422 party_exceeds_capacity. [own wrong-type table_id, unknown] → 400. [Anker, NY] → 422 validation_failed. A single-item move → 201.
- Seeded numeric `reference` → reset 422 validation_failed, and the previous state is unchanged (old token still works). Ruling on the builder's question: 422 is correct. §5 gives 422 for an out-of-range or invalid value in a fixture, the examiner ruled S1-07 the same way for fixture ids, and the shipped checks agree. Accepted.
- Hash format is `scrypt$4096$salt$key`. Passwords are still hashed, as §6 requires. Login works after export/import. An imported hash with N = 2^20 is refused at login (401) instead of using large amounts of memory.

## Clause rows

| id | clause (abridged) | result | evidence |
|---|---|---|---|
| S1-01 | GET /health -> 200 {"status": "ok"} | PASS | probes test_basics; supplied 120/120 |
| S1-02 | Replace all service state with the fixture … When reset returns 204, subsequent requests m… | PASS | probes test_basics; supplied 120/120 |
| S1-03 | This test endpoint … requires no authentication. | PASS | probes all; supplied 120/120 |
| S1-04 | Timestamps in responses are RFC 3339 with an explicit offset | PASS | probes test_reservations; supplied 120/120 |
| S1-05 | Unknown fields in a request body are ignored, never an error. | PASS | probes test_errors; supplied 120/120; F1 re-run on both write paths, depths 1 000–100 000 (r2.py, deep.py) |
| S1-06 | Unknown query parameters are ignored. | PASS | probes test_errors; supplied 120/120 |
| S1-07 | IDs are opaque strings of at most 64 characters … This limit also applies to IDs supplied … | PASS | probes test_errors; supplied 120/120 |
| S1-08 | Seeded users must be able to log in with the given password immediately. | PASS | probes test_basics; supplied 120/120; reset of 402 users then login; import then login (r2.py) |
| S1-09 | `reservations` may seed confirmed bookings, with the same fields as a POST /reservations b… | PASS | probes test_basics; supplied 120/120 |
| S1-10 | A day with no entry is closed" / "A closed day returns "slots": [] | PASS | probes test_reservations; supplied 120/120 |
| S1-11 | A booking must not be rejected solely because its start is in the past | PASS | probes test_cutoff; supplied 120/120 |
| S1-12 | slot_minutes — Bookings start on a grid of this many minutes from opening time | PASS | probes test_reservations; supplied 120/120 |
| S1-13 | Every 4xx and 5xx response carries this body: {"error": {"code": …, "message": …}} | PASS | probes all; supplied 120/120 |
| S1-14 | 400 malformed_request — Unparseable body, or a field of the wrong JSON type | PASS | probes test_errors; supplied 120/120 |
| S1-15 | invalid party_size values (including strings and booleans) and starts_at_local strings tha… | PASS | probes test_errors; supplied 120/120 |
| S1-16 | 422 validation_failed — A required field or query parameter is missing | PASS | probes test_errors; supplied 120/120 |
| S1-17 | An integer-valued query parameter is written as plain decimal digits: 1e9, 4.0 and +4 are … | PASS | probes test_errors; supplied 120/120 |
| S1-18 | Idempotency-Key 1 to 255 characters, otherwise 422 validation_failed | PASS | probes test_idempotency; supplied 120/120 |
| S1-19 | Requests must not produce 5xx responses, including under concurrent load. | PASS | probes test_concurrency; supplied 120/120; F1 re-run on both write paths, depths 1 000–100 000 (r2.py, deep.py) |
| S1-20 | 401 unauthenticated — Missing, malformed or unknown bearer token | PASS | probes test_basics; supplied 120/120 |
| S1-21 | POST /auth/signup -> 201 {user_id, display_name, token} | PASS | probes test_basics; supplied 120/120 |
| S1-22 | POST /auth/login -> 200 {user_id, display_name, token} | PASS | probes test_basics; supplied 120/120 |
| S1-23 | Email already registered → 409 email_taken | PASS | probes test_basics; supplied 120/120 |
| S1-24 | Password shorter than 8 characters → 422 | PASS | probes test_basics; supplied 120/120 |
| S1-25 | email not of the form local@domain → 422 | PASS | probes test_basics; supplied 120/120 |
| S1-26 | Wrong password or unknown email on login → 401 unauthenticated | PASS | probes test_basics; supplied 120/120 |
| S1-27 | Every other endpoint requires a bearer token, except /health, /_test/reset, the two above,… | PASS | probes test_basics; supplied 120/120 |
| S1-28 | Tokens do not expire. An account may have multiple valid tokens and concurrent sessions. | PASS | probes test_basics; supplied 120/120 |
| S1-29 | Concurrent signup with the same email" (derived from S1-23 + S1-19) | PASS | probes test_concurrency; supplied 120/120 |
| S1-30 | Header absent or empty → 400 missing_idempotency_key | PASS | probes test_idempotency; supplied 120/120 |
| S1-31 | The key is scoped to the authenticated user. | PASS | probes test_idempotency; supplied 120/120 |
| S1-32 | Replay: same key, same body → 200, body identical to the original response as a JSON value | PASS | probes test_idempotency; supplied 120/120 |
| S1-33 | Same key, different body → 409 idempotency_key_reuse | PASS | probes test_idempotency; supplied 120/120 |
| S1-34 | idempotency is resolved before endpoint-specific field validation or current-resource chec… | PASS | probes test_idempotency; supplied 120/120 |
| S1-35 | Key reused after the original request failed with 4xx → Treated as a first use | PASS | probes test_idempotency; supplied 120/120 |
| S1-36 | same key with the same body on a different path is a different request, not a replay | PASS | probes test_moves; supplied 120/120 |
| S1-37 | For concurrent identical requests with an unused key, exactly one returns 201. The others … | PASS | probes test_concurrency, test_moves; supplied 120/120 |
| S1-38 | A successful replay returns the original response, even after the resource changes or is c… | PASS | probes test_idempotency; supplied 120/120 |
| S1-39 | Precedence: authentication before idempotency ("After the body has been parsed as a JSON o… | PASS | probes test_idempotency; supplied 120/120 |
| S1-40 | GET /restaurants → {restaurants: [{id, name, timezone}]} | PASS | probes test_basics; supplied 120/120 |
| S1-41 | GET /restaurants/{id} … in the fixture's shape. 404 if unknown. | PASS | probes test_basics; supplied 120/120 |
| S1-42 | All three parameters are required; a missing one is 422 | PASS | probes test_errors; supplied 120/120 |
| S1-43 | Unknown `restaurant_id` on availability | PASS | probes test_errors; supplied 120/120 |
| S1-44 | A slot appears for every slot_minutes step from opens such that slot + reservation_duratio… | PASS | probes test_reservations, test_dst; supplied 120/120 |
| S1-45 | available_table_ids lists the tables … with capacity >= party_size and no overlapping conf… | PASS | probes test_dst; supplied 120/120 |
| S1-46 | starts_at_local is the full YYYY-MM-DDTHH:MM and goes into POST /reservations unchanged | PASS | probes test_reservations; supplied 120/120 |
| S1-47 | POST /reservations 201 shape | PASS | probes test_reservations; supplied 120/120 |
| S1-48 | reference is 6 to 12 characters of A-Z0-9, unique across all reservations, and never chang… | PASS | probes test_reservations, test_patch; supplied 120/120 |
| S1-49 | Two confirmed reservations must never occupy the same table at overlapping times … half-op… | PASS | probes test_reservations; supplied 120/120 |
| S1-50 | not on the slot grid → 422 not_on_slot_grid | PASS | probes test_reservations; supplied 120/120 |
| S1-51 | Slot outside opening hours, or the reservation would end after closes → 422 outside_openin… | PASS | probes test_reservations; supplied 120/120 |
| S1-52 | party_size exceeds the table's capacity → 422 party_exceeds_capacity | PASS | probes test_reservations; supplied 120/120 |
| S1-53 | Unknown restaurant, unknown table, or the table belongs to another restaurant → 404 not_fo… | PASS | probes test_reservations; supplied 120/120 |
| S1-54 | Retries and rejected requests must not create duplicate or partial bookings. | PASS | probes test_reservations; supplied 120/120 |
| S1-55 | GET /reservations — the caller's reservations, starts_at descending, confirmed and cancell… | PASS | probes test_reservations; supplied 120/120 |
| S1-56 | GET /reservations/{reference} … 404 if it is not the caller's | PASS | probes test_reservations; supplied 120/120 |
| S1-57 | cancel → 200 {status: cancelled} … Frees the table immediately | PASS | probes test_reservations; supplied 120/120 |
| S1-58 | Already cancelled → 200 with the current state | PASS | probes test_reservations; supplied 120/120 |
| S1-59 | Now is within cancellation_cutoff_minutes of starts_at, or later → 409 cutoff_passed | PASS | probes test_cutoff; supplied 120/120 |
| S1-60 | Cancel — Not the caller's reservation → 404 | PASS | probes test_reservations; supplied 120/120 |
| S1-61 | Any subset of table_id, starts_at_local, party_size | PASS | probes test_patch; supplied 120/120 |
| S1-62 | Validation is identical to POST /reservations | PASS | probes test_patch; supplied 120/120 |
| S1-63 | the same cutoff rule as cancel applies (409 cutoff_passed), measured against the current s… | PASS | probes test_cutoff; supplied 120/120 |
| S1-64 | A cancelled reservation is 409 reservation_cancelled | PASS | probes test_patch; supplied 120/120 |
| S1-65 | A successful amendment releases the old slot and reserves the new one together. | PASS | probes test_patch; supplied 120/120 |
| S1-66 | A failed amendment leaves the original booking and its occupancy unchanged. | PASS | probes test_patch; supplied 120/120 |
| S1-67 | reference and reservation_id survive a change | PASS | probes test_patch; supplied 120/120 |
| S1-68 | PATCH under contention (S1-49 "including during concurrent requests") | PASS | probes test_concurrency; supplied 120/120 |
| S1-69 | PATCH on another's / unknown reference | PASS | probes test_patch; supplied 120/120 |
| S1-70 | Local times in the skipped hour do not exist. They never appear in availability, and booki… | PASS | probes test_dst; supplied 120/120 |
| S1-71 | Fall back … Always resolve to the first occurrence … The slot appears once in availability | PASS | probes test_dst; supplied 120/120 |
| S1-72 | reservation_duration_minutes is absolute time … A 90-minute reservation starting at 01:30 … | PASS | probes test_dst; supplied 120/120 |
| S1-73 | Offsets must follow the IANA rules for the specified zone and date. | PASS | probes test_dst; supplied 120/120 |
| S1-74 | date is a local calendar date at the restaurant | PASS | probes test_dst; supplied 120/120 |
| S1-75 | Return 200 from export with a JSON object containing track: "tablekeeper", format_version:… | PASS | probes test_export_import; supplied 120/120 |
| S1-76 | Import takes that entire object and atomically replaces the service's state, returning 204… | PASS | probes test_export_import; supplied 120/120 |
| S1-77 | Preserve accounts and hashed-password login, existing bearer tokens, fixture configuration… | PASS | probes test_export_import; supplied 120/120; reset of 402 users then login; import then login (r2.py) |
| S1-78 | Failed request keys remain reusable. | PASS | probes test_export_import; supplied 120/120 |
| S1-79 | Import is replacement, not merge; repeating it restores the exported state without duplica… | PASS | probes test_export_import; supplied 120/120 |
| S1-80 | Import removes all previous destination data and credentials. | PASS | probes test_export_import; supplied 120/120 |
| S1-81 | Invalid JSON follows §5; missing fields, wrong track/version or an invalid state give 422 … | PASS | probes test_export_import; supplied 120/120 |
| S1-82 | Export is an atomic, read-only snapshot; subsequent source writes do not change it. | PASS | probes test_export_import; supplied 120/120 |
| S1-83 | Reset continues to clear all state, including imported state. | PASS | probes test_export_import; supplied 120/120 |
| S1-84 | moves contains 1..8 objects with distinct string references. Invalid shape or duplicate re… | PASS | probes test_moves; supplied 120/120 |
| S1-85 | Unknown/another owner's reference gives 404 not_found; different restaurants give 422 vali… | PASS | probes test_moves; supplied 120/120 |
| S1-86 | omitted fields retain their current values and unknown fields are ignored. The booking's i… | PASS | probes test_moves; supplied 120/120 |
| S1-87 | Cancelled bookings give 409 reservation_cancelled. Each booking's existing cutoff applies. | PASS | probes test_moves; supplied 120/120 |
| S1-88 | Non-occupancy errors use ordinary amendment codes and take precedence in input order, with… | PASS | probes test_moves; supplied 120/120 |
| S1-89 | An overlap among resulting bookings or with an unlisted booking gives 409 table_unavailabl… | PASS | probes test_moves; supplied 120/120 |
| S1-90 | Either every move commits or nothing changes: occupancy, reservation records and retry key… | PASS | probes test_moves; supplied 120/120 |
| S1-91 | On success return 201 with {"reservations": [...]} in input order, including unchanged ite… | PASS | probes test_moves; supplied 120/120 |
| S1-92 | Replays return that original response with 200, even after amendments or cancellations. | PASS | probes test_moves; supplied 120/120 |
| S1-93 | No-op moves retain all existing values. | PASS | probes test_moves; supplied 120/120 |
| S1-94 | Export/import preserves successful batch receipts as well as the resulting bookings. | PASS | probes test_export_import; supplied 120/120 |
| S1-95 | Moves under contention (S1-49 + §11 atomicity) | PASS | probes test_concurrency; supplied 120/120 |
| S1-96 | Two confirmed reservations must never occupy the same table at overlapping times, includin… | PASS | probes test_concurrency; supplied 120/120 |
| S1-97 | §11: "Every booking must belong to the caller and the same restaurant. Unknown/another own… | PASS | inspector r2.py: 5 precedence cases (ruling text) |

## Rulings on the builder's doubts
The rulings from round 1 on doubts 1–8 stand, and none of them blocks. New ruling: seeded invalid `reference` → 422 is accepted (see above).

## Observations (not blocking)
- O1 (round 1) is resolved by the move to input-order precedence, which matches ruling S1-97.
- O2 (round 1) is resolved: 402 seeded users reset in 2.40 s.
- O3 (round 1) is resolved: a seeded numeric reference is refused.
- O4. The structure is still clean: 13 modules, 1 141 lines, and the largest is store.js. `canonical()` is now iterative and readable. `moveBatch` is shorter than before. There are no special cases keyed to checks or sample values.
- O5. The examiner's probe set does not yet contain the F1 regression probe. It should be added before stage 2 is inspected, because the same rule applies to every later stage.
