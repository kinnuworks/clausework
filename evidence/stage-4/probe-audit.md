# Stage 4 probe audit (examiner)

Revision audited: `4c5ea79` (`stage-4/`; builder 9334ea9 plus finisher UI), clean `git archive` export into a scratch directory.
Probes: `evidence/stage-4/probes/`, revealed unchanged in 62a743f. The recomputed seal matches v2 `d50cd243…4640`.
Compatibility sources: tags `stage-1-frozen` (fa79f76), `stage-2-frozen` (fbae59c) and `stage-3-frozen` (840eef4), each exported and run
as TK_S1_URL / TK_S2_URL / TK_S3_URL.

## Baseline
On the unmodified revision all **118/118 probes pass**. That includes the 40-scenario brute-force replan comparison, the
policy-capacity grid probe (O2), and the imports of stage-1, stage-2 and stage-3 exports into stage 4. The stage-3 export carries a
series with a moved occurrence and a cancelled one. No probe contradicted the specification, so there are no probe corrections.

## Planted defects (one per scratch copy; never in the repository)

| # | Family | Clause | Defect planted | Probes | Supplied checks (`check build … 4`) |
|---|---|---|---|---|---|
| D1 | best answer / optimiser order | S4-10 | Criteria 2 and 3 swapped: the rank vector decides before unused seats | **caught**: test_replan_matches_bruteforce | **missed** |
| D2 | simultaneous use / atomic apply | S4-30 | Apply serialisation switched off: an async gap between the stale check and the commit lets two competing plans both apply | **caught**: test_concurrent_applies (+ lifecycle) | **missed** |
| D3 | all or nothing / atomic apply | S4-27, S4-29 | Apply moves the bookings but does not record the closure ("records the closure and all assignments together") | **caught**: test_preview_apply_lifecycle | **missed** |
| D4 | repeated submission / counting | S4-21, S4-22 | A preview increments the restaurant revision | **caught**: 9 failed (revision counting, lifecycle, stale plan, concurrent applies, series amend, repair, stage-3 compat …) | **missed** |
| D5 | behaviour / series amend | S4-53 | Series amend does not skip exception occurrences | **caught**: 2 failed (skips-exceptions, stage-3 compat with a moved occurrence) | **missed** |

Supplied checks in scratch mode, on every copy: stage 1 "120 passed"; stage 2 "24 passed, 1 error" (the upgrade check, which needs the
preceding stage and cannot run in `check build` mode); stage 3 "7 passed"; stage 4 "6 passed". The supplied sample detected none of
the five.

## By family

| Family | Planted | Caught by probes | Caught by supplied checks |
|---|---|---|---|
| best answer (optimiser order) | 1 | 1 | 0 |
| simultaneous use (apply) | 1 | 1 | 0 |
| all or nothing (apply) | 1 | 1 | 0 |
| repeated submission / revision counting | 1 | 1 | 0 |
| behaviour (series amend) | 1 | 1 | 0 |
| **total** | **5** | **5** | **0** |

The probes missed no defect, so no new probe was needed.

## Weak spots
D1 and D3 are each caught by one probe. For D1 that probe runs 40 randomised scenarios, so the margin within it is wide. D3 is caught
only through the post-apply availability, create and explain checks in the lifecycle probe.

## Clean-up
Defect containers and images were removed, and the frozen-stage containers were stopped. The scratch copies stay under the system
temp dir (`examiner-s4-audit-*`), because the factory forbids recursive delete. None of them is in the repository.
