# Stage 3 probe audit (examiner)

Revision audited: `bc172db4482789aae8b7f8895fe10ea93c6e7a95` (`stage-3/`), clean `git archive` export into a scratch directory.
Probes: `evidence/stage-3/probes/`, revealed unchanged in fcf32b9. The recomputed seal matches `c19fc8cf…46a6`.
Compatibility sources: tags `stage-1-frozen` (fa79f76) and `stage-2-frozen` (fbae59c), each exported and run as TK_S1_URL / TK_S2_URL.

## Baseline
On the unmodified revision all **101/101 probes pass**, including both export-compatibility probes (stage-1 → 3 and stage-2 → 3,
each followed by adopting an imported booking). No probe contradicted the specification, so there are no probe corrections.

## Planted defects (one per scratch copy; never in the repository)

| # | Family | Clause | Defect planted | Probes | Supplied checks (`check build … 3`) |
|---|---|---|---|---|---|
| D1 | repeated submission | S3-13 | A no-op PATCH is treated as a real change: revision +1 and an empty `changed` history entry | **caught**: 5 failed (history rules, combined history, moves under policies, series exceptions, stage-1 no-op move) | **missed** |
| D2 | order / precedence | S3-38 | `expected_revision` is checked after the cancelled and cutoff checks instead of before them | **caught**: 1 failed (test_accepted_cutoff_rules) | **missed** |
| D3 | all or nothing | S3-55 | Series adoption commits each generated occurrence as it goes, so a later occurrence's failure leaves partial bookings | **caught**: 1 failed (test_adopt_atomic_and_first_failure) | **missed** |
| D4 | best answer / time | S3-26 | A tie between policies on the same effective date picks the LOWER policy_version | **caught**: 1 failed (test_policy_selection) | **missed** |
| D5 | presentation | S3-02 | explain reports the rules in reverse order (no_overlap, capacity) | **caught**: 3 failed (explain shape and reference, closed day, policy explain) | caught (stage 3: 1 failed) |

Supplied checks in scratch mode: stage 1 "120 passed" and stage 2 "24 passed, 1 error" on every copy. The error is the upgrade
check, which needs the preceding stage and cannot run in `check build` mode; it errors the same way on the stage-2 baseline. Stage 3
"7 passed" on D1–D4; D5 fails `test_explain_accounts_for_every_table`.

## By family

| Family | Planted | Caught by probes | Caught by supplied checks |
|---|---|---|---|
| repeated submission | 1 | 1 | 0 |
| order / precedence | 1 | 1 | 0 |
| all or nothing | 1 | 1 | 0 |
| best answer / time | 1 | 1 | 0 |
| presentation | 1 | 1 | 1 |
| **total** | **5** | **5** | **1** |

The probes missed no defect, so no new probe was needed.

## Weak spots
D2, D3 and D4 are each caught by exactly one probe. The stage-4 set, already sealed, carries these probes unchanged and adds no
second variant for them. Stage 3's simultaneous-use mechanism (synchronous handlers) was not switched off this round. The same
mechanism was switched off in the stage-1 audit, and the stage-3 burst probes (policy versions, adoption, expected_revision) carry
the same detection.

## Clean-up
Defect containers and images were removed. The scratch copies stay under the system temp dir (`examiner-s3-audit-*`), because the
factory forbids recursive delete. None of them is in the repository.
