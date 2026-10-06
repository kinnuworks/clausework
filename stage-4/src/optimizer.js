'use strict';
// Seating-plan search (stage 4). Exhaustive depth-first search over every
// considered booking's feasible options, with bounds on the first two
// objectives. Among feasible plans it minimizes, in order: bookings whose
// table set changes, total unused seats, then the option-rank vector in
// booking order. Pure: it reads only its arguments.

const sameSet = (a, b) => a.length === b.length && a.every((id) => b.includes(id));

function compareRanks(a, b) {
  for (let i = 0; i < a.length; i++) if (a[i] !== b[i]) return a[i] - b[i];
  return 0;
}

// bookings: [{ current, party, seats(ids), allowed(ids), start_ms, end_ms }]
// options:  [{ ids, rank }] — singles in fixture order, then declared pairs.
// -> [{ ids, changed }] per booking, or null when no plan is feasible.
function bestPlan(bookings, options) {
  const candidates = bookings.map((b) => options
    .filter((o) => b.seats(o.ids) >= b.party && b.allowed(o.ids))
    .map((o) => ({ ids: o.ids, rank: o.rank, changed: !sameSet(o.ids, b.current), unused: b.seats(o.ids) - b.party }))
    .sort((x, y) => x.changed - y.changed || x.unused - y.unused || x.rank - y.rank));
  const clash = (i, x, j, y) => bookings[i].start_ms < bookings[j].end_ms && bookings[j].start_ms < bookings[i].end_ms &&
    x.ids.some((id) => y.ids.includes(id));
  let best = null;
  const chosen = [];
  function visit(i, moved, unused) {
    if (best && (moved > best.moved || (moved === best.moved && unused > best.unused))) return;
    if (i === bookings.length) {
      const ranks = chosen.map((c) => c.rank);
      if (!best || moved < best.moved || unused < best.unused || compareRanks(ranks, best.ranks) < 0) {
        best = { moved, unused, ranks, picks: [...chosen] };
      }
      return;
    }
    for (const c of candidates[i]) {
      if (chosen.some((p, j) => clash(j, p, i, c))) continue;
      chosen.push(c);
      visit(i + 1, moved + (c.changed ? 1 : 0), unused + c.unused);
      chosen.pop();
    }
  }
  visit(0, 0, 0);
  return best && { moved: best.moved, unused: best.unused, picks: best.picks.map((p) => ({ ids: p.ids, changed: p.changed })) };
}

module.exports = { bestPlan };
