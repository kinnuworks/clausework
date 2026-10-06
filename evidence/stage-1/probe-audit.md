# Stage 1 probe audit (examiner)

Revision audited: `85374cb7105e85e8e085fc8e030dc63e7a76d538` (`stage-1/`), clean `git archive` export into a scratch
directory under the system temp dir. Probes: `evidence/stage-1/probes/` (seal 9901cc05…b993, revealed unchanged in cc0388f).

## Baseline

The unmodified revision passed all 53 probes (53 passed, 0 failed). No probe contradicted the specification on the
correct build, so `probe-corrections.md` was not needed.

## Planted defects (one at a time, each in its own scratch copy; never in the repository)

| # | Family | Clause | Defect planted | Probes | Supplied checks (`check build … 1`) |
|---|---|---|---|---|---|
| D1 | simultaneous use | S1-96 (overlap under concurrency) | Turned off the concurrency safety in `POST /reservations` by adding a 20 ms async gap between the occupancy check and the commit | **caught**: 7 failed (same-slot burst 50, overlapping-starts burst, idempotent burst, replay tests) | caught (stage 1: fail) |
| D2 | repeated submission + simultaneous use | S1-37 (concurrent identical key, exactly one 201) | Turned off idempotency serialisation by adding a 20 ms async gap between the receipt lookup and the run/record | **caught**: 2 failed (test_idempotent_burst, test_moves_idempotency burst) | **missed** (stage 1: pass) |
| D3 | all or nothing | S1-90 (moves: every move commits or nothing) | Moves applied item by item: each item checked and committed in turn, so earlier items persist when a later one fails | **caught**: 3 failed (swap tables, conflicts all-or-nothing, precedence) | **missed** (stage 1: pass) |
| D4 | time and calendar | S1-71 (fall back resolves to the first occurrence) | A repeated local time resolves to the second occurrence | **caught**: 4 failed (Berlin and NY fall-back, absolute-duration occupancy, reference availability) | caught (stage 1: fail) |
| D5 | behaviour / limits | S1-49 (half-open occupancy) | Overlap test made closed (`<=`), so a 19:00+90 booking now blocks 20:30 | **caught**: 16 failed | caught (stage 1: fail) |

## By family

| Family | Planted | Caught by probes | Caught by supplied checks |
|---|---|---|---|
| simultaneous use | 2 (D1, D2) | 2 | 1 |
| repeated submission | 1 (D2) | 1 | 0 |
| all or nothing | 1 (D3) | 1 | 0 |
| time and calendar | 1 (D4) | 1 | 1 |
| behaviour / limits | 1 (D5) | 1 | 1 |
| **total (5 defects)** | 5 | **5** | 3 |

The probes missed no defect, so the audit needed no new probe. The supplied sample misses both the concurrent-idempotency
mechanism (D2) and the moves atomicity mechanism (D3). Both are covered only by our probes.

## Weak spots (not planted, for the next stage)
- Order/precedence was not planted this round. The probes cover the precedence rules the spec states: idempotency before
  validation, auth before key, moves input order, and cutoff first. Untested by design: precedence between two different
  POST failures in one request, which the spec leaves unordered.
- D1 did not touch PATCH, so the PATCH burst probe (S1-68) passed under D1 as expected. It was not exercised against its
  own planted defect.

## Clean-up
Defect containers and images were removed. The scratch copies are only under the system temp dir
(`examiner-s1-audit-*`). They were left in place rather than recursively deleted, per the factory's no-recursive-delete rule.
None of them is in the repository.
