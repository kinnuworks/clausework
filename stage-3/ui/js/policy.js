// Published booking policies (stage 3). The restaurant detail keeps its original fixture
// configuration, so seat counts for a searched date come from the policy in force that day.

// The policy for a local date: greatest effective_from not later than the date; ties go to
// the greatest policy_version. Null means the original rules (policy 0) apply.
export function selectPolicy(policies, date) {
  const eligible = (policies || []).filter((p) => p && typeof p.effective_from === "string" && p.effective_from <= date);
  eligible.sort((a, b) => (a.effective_from === b.effective_from
    ? (b.policy_version || 0) - (a.policy_version || 0)
    : (a.effective_from < b.effective_from ? 1 : -1)));
  return eligible[0] || null;
}

// The restaurant as it seats on that date: same tables and labels, the policy's capacities.
export function seatedAs(restaurant, policy) {
  const capacities = (policy && policy.capacities) || {};
  return {
    ...restaurant,
    tables: (restaurant.tables || []).map((t) =>
      (Number.isInteger(capacities[t.id]) ? { ...t, capacity: capacities[t.id] } : t)),
  };
}
