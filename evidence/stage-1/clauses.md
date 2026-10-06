# Stage 1 clause register — Tablekeeper reservations

Source: `tablekeeper/spec/stage-1.md`. Written by examiner from the specification alone.
Families: BEH behaviour, ERR refusal/error reporting, ORD order/precedence, AON all-or-nothing,
SIM simultaneous use, REP repeated submission, TIME time/calendar, LIM limits, COMPAT compatibility
with earlier output, BEST best possible answer, PRES presentation.
"RULING" marks a clause where the text was ambiguous; the reading chosen and why are stated.
Probe file per clause in brackets.

## Runtime and conventions

| id | quoted text | family | how a check discriminates |
|---|---|---|---|
| S1-01 | "GET /health -> 200 {"status": "ok"}" | BEH | exact body. [test_basics] |
| S1-02 | "Replace all service state with the fixture … When reset returns 204, subsequent requests must see only that fixture. Repeated resets are supported." | BEH | reset A (user+booking), reset B: user of A cannot log in (401), booking gone, restaurants list = B only. [test_basics] |
| S1-03 | "This test endpoint … requires no authentication." | BEH | reset with no Authorization → 204. [all] |
| S1-04 | "Timestamps in responses are RFC 3339 with an explicit offset" | PRES | `starts_at`, `ends_at`, `created_at` parse with tzinfo present; offset equals IANA offset (+02:00 Berlin in Sept). [test_reservations] |
| S1-05 | "Unknown fields in a request body are ignored, never an error." | BEH | POST /reservations with extra `"foo":1` → 201; signup with extra field → 201. [test_errors] |
| S1-06 | "Unknown query parameters are ignored." | BEH | availability with `&x=1` → 200 same as without. [test_errors] |
| S1-07 | "IDs are opaque strings of at most 64 characters … This limit also applies to IDs supplied in reset fixtures." | LIM, RULING | RULING: a reset fixture containing a 65-char id is a field out of range → 422 `validation_failed` (§5 "values exceeding a stated maximum or length"); 64-char id accepted (204). Returned ids ≤ 64 chars. [test_errors] |

## Model / fixture

| id | quoted text | family | discriminator |
|---|---|---|---|
| S1-08 | "Seeded users must be able to log in with the given password immediately." | BEH | login of fixture user → 200 with token. [test_basics] |
| S1-09 | "`reservations` may seed confirmed bookings, with the same fields as a POST /reservations body plus id, reference and user_id." | BEH, RULING | seeded booking visible to its user by reference with status confirmed, blocks availability, `reservation_id` equals fixture `id` (RULING: identities are not regenerated). [test_basics] |
| S1-10 | "A day with no entry is closed" / "A closed day returns "slots": []" | BEH | availability on a Wednesday (no entry) → `slots: []`; booking → 422 outside_opening_hours. [test_reservations] |
| S1-11 | "A booking must not be rejected solely because its start is in the past" | TIME | POST for a past date on grid in hours → 201. [test_cutoff] |
| S1-12 | "slot_minutes — Bookings start on a grid of this many minutes from opening time" | BEH | restaurant opens 17:15 slot 45: 18:45 accepted, 18:30 (on a midnight-anchored 30-grid, not on the opening-anchored 45-grid) → 422 not_on_slot_grid. Careless reading anchors at midnight. [test_reservations] |

## Errors (§5) — apply to every entry point, now and later

| id | quoted text | family | discriminator |
|---|---|---|---|
| S1-13 | "Every 4xx and 5xx response carries this body: {"error": {"code": …, "message": …}}" | PRES | every error probe asserts `error.code` and string `error.message`. [all] |
| S1-14 | "400 malformed_request — Unparseable body, or a field of the wrong JSON type" | ERR | body `{` → 400; body `[1]` (not an object) → 400; `restaurant_id: 5` → 400; signup `email: 5` → 400. [test_errors] |
| S1-15 | "invalid party_size values (including strings and booleans) and starts_at_local strings that are not a bare local YYYY-MM-DDTHH:MM are 422 validation_failed. Other wrong JSON types follow the rule below." | ERR, ORD, RULING | party_size `"4"`, `true`, `2.5`, `0`, `-1` → 422; starts_at_local `…T19:00:00`, `…T19:00Z`, `…T19:00+02:00`, `2026-02-30T19:00`, `…T25:00` → 422 validation_failed. RULING: `starts_at_local: 123` (not a string) is a wrong JSON type → 400 malformed_request, because the special rule is stated only for strings. Careless: 400 for party_size "4". [test_errors] |
| S1-16 | "422 validation_failed — A required field or query parameter is missing" | ERR | POST without table_id → 422; availability without date → 422. [test_errors] |
| S1-17 | "An integer-valued query parameter is written as plain decimal digits: 1e9, 4.0 and +4 are 422" | ERR | party_size=`1e9`, `4.0`, `+4`, `abc`, `0` → 422; `04`?? not probed. [test_errors] |
| S1-18 | "Idempotency-Key 1 to 255 characters, otherwise 422 validation_failed" | LIM | 255 chars → 201; 256 chars → 422 (both write paths). [test_idempotency] |
| S1-19 | "Requests must not produce 5xx responses, including under concurrent load." | ERR, SIM | every probe asserts < 500; bursts of 50. [test_concurrency] |
| S1-20 | "401 unauthenticated — Missing, malformed or unknown bearer token" | ERR | no header / `Token x` / `Bearer bogus` → 401 on GET /reservations, POST /reservations, cancel, PATCH, moves. [test_basics] |

## Authentication (§6)

| id | quoted text | family | discriminator |
|---|---|---|---|
| S1-21 | "POST /auth/signup -> 201 {user_id, display_name, token}" | BEH | shape; token usable immediately. [test_basics] |
| S1-22 | "POST /auth/login -> 200 {user_id, display_name, token}" | BEH | shape; same user_id as signup. [test_basics] |
| S1-23 | "Email already registered → 409 email_taken" | ERR | second signup same email → 409; fixture user's email → 409. [test_basics] |
| S1-24 | "Password shorter than 8 characters → 422" | LIM | 7 chars → 422, 8 chars → 201. [test_basics] |
| S1-25 | "email not of the form local@domain → 422" | ERR | `nope`, `@x`, `a@` → 422. [test_basics] |
| S1-26 | "Wrong password or unknown email on login → 401 unauthenticated" | ERR | both → 401. [test_basics] |
| S1-27 | "Every other endpoint requires a bearer token, except /health, /_test/reset, the two above, and … GET /restaurants, GET /restaurants/{id} and GET /availability" | BEH | public endpoints 200 without token; protected 401 without. [test_basics] |
| S1-28 | "Tokens do not expire. An account may have multiple valid tokens and concurrent sessions." | BEH | login twice → both tokens work after the second login. [test_basics] |
| S1-29 | "Concurrent signup with the same email" (derived from S1-23 + S1-19) | SIM | burst of 20 identical signups → exactly one 201, rest 409 email_taken. [test_concurrency] |

## Idempotency (§7) — applies to POST /reservations and POST /reservation-moves

| id | quoted text | family | discriminator |
|---|---|---|---|
| S1-30 | "Header absent or empty → 400 missing_idempotency_key" | ERR | absent and `""` → 400; nothing created. [test_idempotency] |
| S1-31 | "The key is scoped to the authenticated user." | REP | Ada and Bob same key, different bodies → both 201. [test_idempotency] |
| S1-32 | "Replay: same key, same body → 200, body identical to the original response as a JSON value" | REP | second POST → 200, json equal; one reservation in list. Key order/whitespace changed → still replay. [test_idempotency] |
| S1-33 | "Same key, different body → 409 idempotency_key_reuse" | REP | → 409; no new reservation. [test_idempotency] |
| S1-34 | "idempotency is resolved before endpoint-specific field validation or current-resource checks … even when that new body would otherwise be invalid" | ORD | used key + body with party_size 0 / unknown restaurant → 409 idempotency_key_reuse (careless: 422/404). [test_idempotency] |
| S1-35 | "Key reused after the original request failed with 4xx → Treated as a first use" | REP | key used on a 422 request and on a 409 table_unavailable request, then reused with a valid body → 201. [test_idempotency] |
| S1-36 | "same key with the same body on a different path is a different request, not a replay" | REP, RULING | RULING: key namespace is (user, method, path). Key used on /reservations then on /reservation-moves → 201 not 409. [test_moves] |
| S1-37 | "For concurrent identical requests with an unused key, exactly one returns 201. The others return 200 with the same body. The operation takes effect only once." | SIM, REP | burst of 30 identical → one 201, 29 × 200 equal bodies, exactly one reservation. Same for moves. [test_concurrency, test_moves] |
| S1-38 | "A successful replay returns the original response, even after the resource changes or is cancelled. It makes no further state changes." | REP | book, cancel, replay → 200 with status confirmed (original); reservation remains cancelled; after PATCH replay shows original values. [test_idempotency] |
| S1-39 | Precedence: authentication before idempotency ("After the body has been parsed as a JSON object and the caller authenticated, idempotency is resolved") | ORD, RULING | no token + no key → 401 (RULING: idempotency resolution happens after authentication). Unparseable body + valid token + no key → not probed (unordered by text). [test_idempotency] |

## Restaurants and availability (§8)

| id | quoted text | family | discriminator |
|---|---|---|---|
| S1-40 | "GET /restaurants → {restaurants: [{id, name, timezone}]}" | PRES | exact ids/names/timezones of fixture. [test_basics] |
| S1-41 | "GET /restaurants/{id} … in the fixture's shape. 404 if unknown." | PRES, ERR | fields equal fixture (opening_hours, tables id/label/capacity); unknown → 404 not_found. [test_basics] |
| S1-42 | "All three parameters are required; a missing one is 422" | ERR | each missing → 422. [test_errors] |
| S1-43 | Unknown `restaurant_id` on availability | ERR, RULING | RULING: 404 not_found (§5 "No such resource"). [test_errors] |
| S1-44 | "A slot appears for every slot_minutes step from opens such that slot + reservation_duration_minutes <= closes" | BEH, LIM | Thu 18:00–23:00, 30/90: slots 18:00…21:30 (8); 21:30 present (ends exactly 23:00), 22:00 absent. [test_reservations, test_dst] |
| S1-45 | "available_table_ids lists the tables … with capacity >= party_size and no overlapping confirmed reservation, in fixture order. A slot with no available table still appears" | BEH, BEST | party 2 → [t_1, t_2, t_3]; party 3 → [t_2]; party 99 → all slots with []; reference model compared on every slot of every probed date × party sizes 1..5. [test_dst] |
| S1-46 | "starts_at_local is the full YYYY-MM-DDTHH:MM and goes into POST /reservations unchanged" | BEH | every listed slot with a table is bookable by echoing it. [test_reservations] |

## Reservations (§8)

| id | quoted text | family | discriminator |
|---|---|---|---|
| S1-47 | POST /reservations 201 shape | PRES | all fields; status confirmed; ends_at = starts_at + duration. [test_reservations] |
| S1-48 | "reference is 6 to 12 characters of A-Z0-9, unique across all reservations, and never changes" | PRES, LIM | regex `^[A-Z0-9]{6,12}$`; 40 references distinct; unchanged after PATCH/moves/cancel. [test_reservations, test_patch] |
| S1-49 | "Two confirmed reservations must never occupy the same table at overlapping times … half-open interval … A 90-minute booking at 19:00 therefore does not overlap a booking starting at 20:30." | BEH, LIM | 19:00 then 20:30 same table → 201; 19:30 and 18:00 → 409 table_unavailable; other table same time → 201. [test_reservations] |
| S1-50 | "not on the slot grid → 422 not_on_slot_grid" | ERR | 19:15 → 422. [test_reservations] |
| S1-51 | "Slot outside opening hours, or the reservation would end after closes → 422 outside_opening_hours" | ERR, LIM | 17:30, 22:00 (ends 23:30 > 23:00), 23:00, closed Wednesday → 422; Friday 22:00 → 201. [test_reservations] |
| S1-52 | "party_size exceeds the table's capacity → 422 party_exceeds_capacity" | ERR | party 3 on t_1 (cap 2) → 422; party 2 → 201. [test_reservations] |
| S1-53 | "Unknown restaurant, unknown table, or the table belongs to another restaurant → 404 not_found" | ERR | each → 404. [test_reservations] |
| S1-54 | "Retries and rejected requests must not create duplicate or partial bookings." | AON, REP | after every rejection GET /reservations count unchanged and availability unchanged. [test_reservations] |
| S1-55 | "GET /reservations — the caller's reservations, starts_at descending, confirmed and cancelled alike … empty list is {"reservations": []}" | BEH, ORD | 3 bookings created out of order → descending by instant; cancelled included; other user's excluded; new user → []. [test_reservations] |
| S1-56 | "GET /reservations/{reference} … 404 if it is not the caller's" | ERR | Bob reading Ada's → 404 not_found; unknown → 404. [test_reservations] |
| S1-57 | "cancel → 200 {status: cancelled} … Frees the table immediately" | BEH | availability offers slot again; rebooking → 201. [test_reservations] |
| S1-58 | "Already cancelled → 200 with the current state" | REP | second cancel → 200 cancelled. [test_reservations] |
| S1-59 | "Now is within cancellation_cutoff_minutes of starts_at, or later → 409 cutoff_passed" | TIME | booking ~45–60 min from now with cutoff 120 → 409; past booking → 409; booking ≥4h45 ahead → 200. Status unchanged after refusal. [test_cutoff] |
| S1-60 | "Cancel — Not the caller's reservation → 404" | ERR | Bob cancelling Ada's → 404; booking still confirmed. [test_reservations] |

## PATCH (§8)

| id | quoted text | family | discriminator |
|---|---|---|---|
| S1-61 | "Any subset of table_id, starts_at_local, party_size" | BEH, RULING | change each alone → 200 (RULING: success status 200, body = reservation shape); omitted fields kept. [test_patch] |
| S1-62 | "Validation is identical to POST /reservations" | ERR | party "3", 0 → 422 validation_failed; off-grid → not_on_slot_grid; 22:00 Thu → outside_opening_hours; party 3 on t_1 → party_exceeds_capacity; table of other restaurant → 404; bad local format → 422; overlap → 409 table_unavailable. [test_patch] |
| S1-63 | "the same cutoff rule as cancel applies (409 cutoff_passed), measured against the current start time" | TIME, ORD | near booking moved far ahead → 409; far booking moved to within cutoff → 200 (careless reading checks the new time). [test_cutoff] |
| S1-64 | "A cancelled reservation is 409 reservation_cancelled" | ERR | → 409. [test_patch] |
| S1-65 | "A successful amendment releases the old slot and reserves the new one together." | AON | shifting 19:00→19:30 on the same table (overlapping its own old interval) → 200; old slot then offered in availability. [test_patch] |
| S1-66 | "A failed amendment leaves the original booking and its occupancy unchanged." | AON | after each failure GET returns identical record; availability identical. [test_patch] |
| S1-67 | "reference and reservation_id survive a change" | COMPAT | equal before/after; created_at unchanged. [test_patch] |
| S1-68 | PATCH under contention (S1-49 "including during concurrent requests") | SIM | 10 bookings concurrently PATCHed to the same free table/slot → exactly one 200, others 409, losers unchanged. [test_concurrency] |
| S1-69 | PATCH on another's / unknown reference | ERR | → 404 not_found. [test_patch] |

## Time and DST (§9)

| id | quoted text | family | discriminator |
|---|---|---|---|
| S1-70 | "Local times in the skipped hour do not exist. They never appear in availability, and booking one is 422 invalid_local_time." | TIME | Berlin 2026-03-29 and New York 2026-03-08: 02:00 and 02:30 absent; booking 02:30 → 422 invalid_local_time; 01:30 → +01:00 / -05:00, 03:00 → +02:00 / -04:00. [test_dst] |
| S1-71 | "Fall back … Always resolve to the first occurrence … The slot appears once in availability" | TIME | Berlin 2026-10-25 02:30 → `+02:00`; New York 2026-11-01 01:30 → `-04:00`; no duplicate starts_at_local. Careless: second occurrence or duplicated slots. [test_dst] |
| S1-72 | "reservation_duration_minutes is absolute time … A 90-minute reservation starting at 01:30 on a fall-back night … ends_at will read 02:00, not 03:00" | TIME | NY 01:30 → ends_at `2026-11-01T02:00:00-05:00`; Berlin 02:30 → `03:00:00+01:00`; Berlin spring 01:30 → `04:00:00+02:00`; NY spring 01:30 → `04:00:00-04:00`. Occupancy in absolute time: after NY 01:30 booking, 02:00 EST slot still free (wall-clock reading would block it). [test_dst] |
| S1-73 | "Offsets must follow the IANA rules for the specified zone and date." | TIME, BEST | every slot's `starts_at` compared to zoneinfo reference for all four transition days plus ordinary days. [test_dst] |
| S1-74 | "date is a local calendar date at the restaurant" | TIME | slots carry that date in starts_at_local. [test_dst] |

## Export / import (§10)

| id | quoted text | family | discriminator |
|---|---|---|---|
| S1-75 | "Return 200 from export with a JSON object containing track: "tablekeeper", format_version: 1 and state" | PRES | exact keys/values; no auth. [test_export_import] |
| S1-76 | "Import takes that entire object and atomically replaces the service's state, returning 204. It must accept an unchanged export" | COMPAT | reset to a different fixture, import → 204. [test_export_import] |
| S1-77 | "Preserve accounts and hashed-password login, existing bearer tokens, fixture configuration, reservations, references, all completed idempotent request bodies and original responses. Identities, statuses and timestamps must not be regenerated." | COMPAT | after import: old token works; password login works; restaurants/detail equal; each reservation equal field-for-field incl. created_at; cancelled stays cancelled; POST and moves replays → 200 identical original bodies; same key different body → 409. [test_export_import] |
| S1-78 | "Failed request keys remain reusable." | COMPAT | key used on a 422 before export → 201 after import. [test_export_import] |
| S1-79 | "Import is replacement, not merge; repeating it restores the exported state without duplicating anything." | COMPAT, REP | import twice → same reservation list, same restaurants list. [test_export_import] |
| S1-80 | "Import removes all previous destination data and credentials." | COMPAT | token/user/reservation created after export → 401 / login 401 / 404 after import. [test_export_import] |
| S1-81 | "Invalid JSON follows §5; missing fields, wrong track/version or an invalid state give 422 validation_failed without changing the destination." | ERR, AON, RULING | `{` → 400 malformed_request; missing state/track/format_version, track "x", format_version 2, state "garbage"/42 → 422 (RULING: §10's specific rule overrides §5's wrong-type 400 for `state`); destination unchanged afterward. [test_export_import] |
| S1-82 | "Export is an atomic, read-only snapshot; subsequent source writes do not change it." | COMPAT | export E, write more, import E → later writes absent. Export twice without writes → equal content of observable state. [test_export_import] |
| S1-83 | "Reset continues to clear all state, including imported state." | BEH | after import, reset → imported token 401. [test_export_import] |

## Atomic reservation moves (§11)

| id | quoted text | family | discriminator |
|---|---|---|---|
| S1-84 | "moves contains 1..8 objects with distinct string references. Invalid shape or duplicate references gives 422 validation_failed." | ERR, LIM, RULING | [] / 9 items / duplicates / missing moves / moves "x" / item without reference / reference 5 → 422 (RULING: "invalid shape" covers wrong types inside the body, so 422 not 400). 8 items accepted. [test_moves] |
| S1-85 | "Unknown/another owner's reference gives 404 not_found; different restaurants give 422 validation_failed. No token gives 401." | ERR | each. [test_moves] |
| S1-86 | "omitted fields retain their current values and unknown fields are ignored. The booking's identity, owner and creation time never change." | BEH | swap tables → reservation_id, reference, created_at unchanged, owner still sees them. [test_moves] |
| S1-87 | "Cancelled bookings give 409 reservation_cancelled. Each booking's existing cutoff applies." | ERR, TIME | each. [test_moves] |
| S1-88 | "Non-occupancy errors use ordinary amendment codes and take precedence in input order, with cutoff errors preceding other changes for that booking." | ORD, RULING | [A party 9 → party_exceeds_capacity, B cancelled] → 422 party_exceeds_capacity; reversed → 409 reservation_cancelled; [near booking with party 0] → 409 cutoff_passed; [A → occupied slot, B party 9] → 422 (RULING: non-occupancy errors outrank table_unavailable regardless of position). [test_moves] |
| S1-89 | "An overlap among resulting bookings or with an unlisted booking gives 409 table_unavailable. Unchanged listed bookings retain their occupancy." | BEH | swap of tables between A and B → 201 (sequential application would fail: discriminator); swap of times on one table → 201; both to the same slot → 409; onto unlisted → 409; [A no-op, B → A's interval] → 409. [test_moves] |
| S1-90 | "Either every move commits or nothing changes: occupancy, reservation records and retry keys." | AON | after any failure all listed records identical, availability identical, the key is reusable (201 with a valid body). [test_moves] |
| S1-91 | "On success return 201 with {"reservations": [...]} in input order, including unchanged items." | PRES, ORD | order equals input order (given reverse of creation order). [test_moves] |
| S1-92 | "Replays return that original response with 200, even after amendments or cancellations." | REP | replay after cancel → 200 identical original. [test_moves] |
| S1-93 | "No-op moves retain all existing values." | BEH | [{reference}] → 201, record identical. [test_moves] |
| S1-94 | "Export/import preserves successful batch receipts as well as the resulting bookings." | COMPAT | covered in S1-77 probe. [test_export_import] |
| S1-95 | Moves under contention (S1-49 + §11 atomicity) | SIM | 20 concurrent moves batches from different users each targeting the same free slot → exactly one 201. [test_concurrency] |

## Simultaneous use (§1 "including during concurrent requests")

| id | quoted text | family | discriminator |
|---|---|---|---|
| S1-96 | "Two confirmed reservations must never occupy the same table at overlapping times, including during concurrent requests." | SIM | 50 simultaneous POSTs (two users, distinct keys) for the same table/slot → exactly one 201, 49 × 409; 48 simultaneous POSTs at 8 different start times on one table → accepted set pairwise non-overlapping, each refusal overlaps an accepted booking (some serial order explains it), availability agrees. [test_concurrency] |

## Rulings summary
S1-07, S1-09, S1-15, S1-36, S1-39, S1-43, S1-61, S1-81, S1-84, S1-88 — reasons inline above.
Not probed because the text orders nothing: precedence between different POST /reservations
failures on one request (e.g. off-grid + over-capacity), the exact cutoff boundary instant.

## Rulings added after the seal

| id | quoted text | family | ruling |
|---|---|---|---|
| S1-97 | §11: "Every booking must belong to the caller and the same restaurant. Unknown/another owner's reference gives 404 not_found; different restaurants give 422 validation_failed." … "Non-occupancy errors use ordinary amendment codes and take precedence in input order, with cutoff errors preceding other changes for that booking." | ORD, RULING | Requested by lead at 06:55. Two phases. (1) Whole-body shape: `moves` is 1..8 objects with distinct string references, else 422. (2) Items in input order. The first item with any non-occupancy error decides the response. Within one item the order is: unknown or foreign reference 404, then restaurant differs from the batch's 422, then cancelled 409 `reservation_cancelled`, then cutoff 409 `cutoff_passed`, then the ordinary PATCH field codes. `table_unavailable` is decided only after every item passes. So [own cancelled booking, unknown reference] gives 409 `reservation_cancelled`, and [unknown reference, own cancelled booking] gives 404. Why: a 404 on a reference is the ordinary amendment code PATCH returns, so it is a non-occupancy error, and the text orders all non-occupancy errors by input position. It sets no batch-wide pass that runs first. |
