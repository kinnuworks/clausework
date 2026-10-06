# Portability: the same mandates on a different problem

Half of the judging asks whether another team could point these mandates at something
else. We did.

**Problem:** the event's `toy` track, a shared counter with a one-button page. It has
nothing in common with a reservation system except that both are written specifications.

**Mandates:** byte-identical to [`../mandates/`](../mandates/). Combined hash
`1ee13e2593a36454151e464a607f034363a37bca7a52f1f1f04eb4f9820fcfaa`, from

```sh
cd mandates && find . -type f -name '*.md' | sort | xargs shasum -a 256 | shasum -a 256
```

**Run:** room `e6295487…`, 6 Oct 2026, 06:21–06:33 IST, twelve minutes before the
tablekeeper run in this repository was dispatched. One dispatch
([`../kit/dispatch-rehearsal.md`](../kit/dispatch-rehearsal.md)), stages 1 and 2, no
further human input.

| | Toy | Tablekeeper (this repository) |
|---|---|---|
| Mandate hash | `1ee13e25…cfaa` | `1ee13e25…cfaa` |
| Seats | the same five | the same five |
| Stages asked / frozen | 2 / 2 | 4 / 4 |
| Human messages | 1 | 1 |
| Wall-clock | 11 min | 74 min |
| Room events | 406 | 2,056 |
| Tokens, API-equivalent | 7.8 M, $5.05 | 136.0 M, $52.23 |

Files: [`toy-room.json`](toy-room.json) is the full room download;
[`toy-ledger.md`](toy-ledger.md) is the lead's own record; [`toy-usage.md`](toy-usage.md)
is per-seat token use.

Two things did not go to plan in the toy run and are recorded in the ledger: the lead
skipped the planted-defect audit for a stage to save time, and one seat started a
background job, which failed and shows as the room's single error event.

An earlier rehearsal with a first version of the mandates, and the three fixes it led to,
are described in [`../FACTORY.md`](../FACTORY.md) §8 and published with the first full run
at https://github.com/kinnuworks/clausework-tablekeeper (`portability/`).
