# Stage 1 — verdict, round 1

**REJECT** — revision `85374cb7105e85e8e085fc8e030dc63e7a76d538` (main), folder `stage-1/`, round 1.
Inspector, 2026-10-06. One blocking failure (F1); everything else passes.

## Evidence gathered

| Step | Result |
|---|---|
| Clean copy | `git archive 85374cb stage-1` into `/tmp/insp-s1r1-8gH6/`. `stage-1/` is byte-identical between 85374cb and HEAD 533befd (empty diff). Contents: Dockerfile, RUN.md, package.json, .dockerignore, DESIGN.md, src/ (13 modules, 1 190 lines total). No nested .git, no symlinks. |
| Delivery rule 1 (Dockerfile, RUN.md, source) | PASS. RUN.md command `docker build -t tablekeeper-stage-1 . && docker run --rm -e PORT=8080 -p 8080:8080 tablekeeper-stage-1` builds and serves. |
| `check build … /tmp/insp-s1r1-8gH6/stage-1 1` | stage 1: pass |
| `check run … 1 isolated` | stage 1 **120/120 passed** (health_reset_auth 12, reservations 37, restaurants_availability 18, retries_time_input 20, sample 20, seeded_state 13). Stage-2 probe **FAILS** as required. "claimed stage: 1 on the shipped checks". Report: band-work/checks/1006-064903-7625. |
| `check repo` | only the 3 ignorable complaints (README.md, FACTORY.md, room.json). |
| Delivery rule 4 (no later-stage work) | PASS. No HTML/screens; the only `table_ids` is stage-1 `available_table_ids`. Stage-2 checks fail. |
| Delivery rule 5 (limits, offline) | PASS. Run with `--cpus 2 --memory 2g`: healthy after 1 s. With `--network none`, `/health` from inside the container returns `{"status":"ok"}`. 50 concurrent logins all 200 in 1.1 s. |
| Delivery rule 6 (no secrets) | PASS. Dockerfile ENV: NODE_ENV, PORT, UV_THREADPOOL_SIZE only. |
| Examiner probes | Seal recomputed over `evidence/stage-1/probes/`: `9901cc054295a7e96df96056def4de9258c12f2f537e3dfabdd60843bdd5b993` — **matches** seal.txt. Run against the clean-export container: **53/53 passed**. |
| Own attack | scripts `/tmp/insp-s1r1-attack/{attack,deep,min}.py`; findings below. |

## Failures (blocking)

### F1 — deeply nested JSON in an ignored field gives 500 on both idempotent write paths
- **Clauses:** S1-19 / §5 "Requests must not produce 5xx responses, including under concurrent load." and S1-05 / §3.4 "Unknown fields in a request body are ignored, never an error."
- **Smallest input** (6 KB, valid JSON, valid token and key):
  `POST /reservations`, `Authorization: Bearer <valid>`, `Idempotency-Key: k1`, body `{"x":` + 3000 × `[` + 3000 × `]` + `}`
- **What happened:** `500 {"error":{"code":"internal_error",…}}`. Container log: `RangeError: Maximum call stack size exceeded at canonical (/app/src/idempotency.js:23)`. The recursive `canonical()` used for "same body" comparison overflows at nesting depth ≈ 2 560. Same 500 on `POST /reservation-moves` with body `{"moves":[{"reference":"X"}],"x":` + 3000 × `[` + 3000 × `]` + `}`, and with nested objects (`{"a":` × 3000). Nesting 1 000 is fine (201). PATCH, reset and import with the same nesting do not fail (they never canonicalise).
- **What the clause requires:** a non-5xx response. Here the unknown field `x` must be ignored, so the first body is a normal request missing required fields → `422 validation_failed` (or 201 when the required fields are also present).

## Clause rows

| id | clause (abridged) | result | evidence |
|---|---|---|---|
| S1-01 | GET /health -> 200 {"status": "ok"} | PASS | probes test_basics; supplied 120/120 |
| S1-02 | Replace all service state with the fixture … When reset returns 204, subsequent requests m… | PASS | probes test_basics; supplied 120/120 |
| S1-03 | This test endpoint … requires no authentication. | PASS | probes all probes; supplied 120/120 |
| S1-04 | Timestamps in responses are RFC 3339 with an explicit offset | PASS | probes test_reservations; supplied 120/120 |
| S1-05 | Unknown fields in a request body are ignored, never an error. | **FAIL** | inspector attack F1 (below); probes pass but do not cover nesting |
| S1-06 | Unknown query parameters are ignored. | PASS | probes test_errors; supplied 120/120 |
| S1-07 | IDs are opaque strings of at most 64 characters … This limit also applies to IDs supplied … | PASS | probes test_errors; supplied 120/120 |
| S1-08 | Seeded users must be able to log in with the given password immediately. | PASS | probes test_basics; supplied 120/120 |
| S1-09 | `reservations` may seed confirmed bookings, with the same fields as a POST /reservations b… | PASS | probes test_basics; supplied 120/120 |
| S1-10 | A day with no entry is closed" / "A closed day returns "slots": [] | PASS | probes test_reservations; supplied 120/120 |
| S1-11 | A booking must not be rejected solely because its start is in the past | PASS | probes test_cutoff; supplied 120/120 |
| S1-12 | slot_minutes — Bookings start on a grid of this many minutes from opening time | PASS | probes test_reservations; supplied 120/120 |
| S1-13 | Every 4xx and 5xx response carries this body: {"error": {"code": …, "message": …}} | PASS | probes all probes; supplied 120/120 |
| S1-14 | 400 malformed_request — Unparseable body, or a field of the wrong JSON type | PASS | probes test_errors; supplied 120/120 |
| S1-15 | invalid party_size values (including strings and booleans) and starts_at_local strings tha… | PASS | probes test_errors; supplied 120/120 |
| S1-16 | 422 validation_failed — A required field or query parameter is missing | PASS | probes test_errors; supplied 120/120 |
| S1-17 | An integer-valued query parameter is written as plain decimal digits: 1e9, 4.0 and +4 are … | PASS | probes test_errors; supplied 120/120 |
| S1-18 | Idempotency-Key 1 to 255 characters, otherwise 422 validation_failed | PASS | probes test_idempotency; supplied 120/120 |
| S1-19 | Requests must not produce 5xx responses, including under concurrent load. | **FAIL** | inspector attack F1 (below); probes pass but do not cover nesting |
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
| S1-77 | Preserve accounts and hashed-password login, existing bearer tokens, fixture configuration… | PASS | probes test_export_import; supplied 120/120 |
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

## Rulings on the builder's declared doubts (none blocks)

1. **Write error order** 401 → key 400/422 → body parse 400 → receipt 200/409 → types 400 → values 422 → 404 → booking rules: consistent with §7 ("after the body has been parsed … and the caller authenticated, idempotency is resolved before field validation or current-resource checks"). The order of key-check vs body-parse is not stated; accepted.
2. **Booking rule order** invalid_local_time → hours/grid → capacity → table_unavailable; before-opening and off-grid → outside_opening_hours: not ordered by the spec; the grid is defined "from opening time", so a time outside the hours has no grid. Accepted.
3. **PATCH/moves** cancelled → cutoff → fields: matches §11 "cutoff errors preceding other changes for that booking". Wrong JSON type inside a moves item → 400 follows §5; bad moves shape → 422 follows §11. Accepted.
4. **Cutoff passed when now ≥ starts_at − cutoff**: "within … or later" read inclusively; accepted (boundary instant not probed).
5. **PATCH {} → 200 unchanged**: "any subset" includes the empty subset. Accepted (still subject to cancelled/cutoff checks, which it applies).
6. **Case-insensitive emails**: not stated; accepted, non-blocking.
7. **Seeded reservations validated for capacity and overlap, not hours/grid**: overlap follows §1's invariant; capacity is a reasonable reading; past/off-hours seeds stay accepted. Accepted.
8. **Wrong method on a known path → 404**: no 405 is specified; 404 with the error body is consistent with §5. Accepted.

## Observations (not blocking)

- O1. `POST /reservation-moves` with `[{cancelled booking}, {unknown reference}]` → 404, i.e. ownership of all items is checked before item 1's `reservation_cancelled`. §11 "take precedence in input order" could be read either way; the examiner's S1-88 ruling does not cover 404 vs per-item errors. Logged only.
- O2. Reset hashes every seeded password with scrypt (N=16384): 50 users 1.1 s, 200 users 5.2 s on 2 vCPU. A fixture of ~400 users would exceed the 10 s reset timeout. No fixture size is stated.
- O3. A seeded reservation with a numeric `reference` (123456) is accepted (the regex test coerces it to a string); it should be a string per §8.
- O4. Fall-back/spring-forward spot checks (New York 2026-11-01: slots 01:00/01:30 at −04:00 listed once; 01:30 booking ends 02:00−05:00; adjacent 02:00 EST booking accepted, half-open) all correct.
- O5. Structure is clean: 13 small modules (largest store.js 227 lines), clear names, no dead code, no special cases keyed to checks or sample values.

## For round 2
Re-run first: F1 smallest input on both write paths. Ask: examiner to add F1 (nesting depth 3 000 in an unknown field, both idempotent paths, expect < 500) to the probes.
