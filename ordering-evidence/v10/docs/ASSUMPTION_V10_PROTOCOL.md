# v10: provenance and component ablation of municipal ordering assumptions

Fixed 28 October 2026 before executing the new component analysis. This is a
post-results revision: all v9 results were already known. It is not preregistration.

The primary question is whether the municipal reversals depend on arbitrary
cross-subprocess or suffix ordering. Documentary evidence of a preprocessing
convention is distinct from evidence of actual execution order.

## Fixed populations and queries

Use unchanged M1 (999 cases) and M3 (1,409 cases) cohorts and all 45 original
N-source top-ten strict-score queries in each. Keep the original direction,
including noncertified directions. Do not select queries or cases by new outcome.
IT C and old T/N/F results remain unchanged controls. Check cohort and source
hashes before running. No additional raw-data exclusions or timestamp coarsening.

## Models

- T: timestamp precedence only.
- P: additionally order subprocess prefixes lexicographically inside each tie;
  events of the same prefix remain unordered. This is an unsupported convention.
- W: additionally order three-digit ordinals only within the same subprocess;
  different subprocesses freely interleave, suffix variants remain unordered.
  This uses the publisher's ordinal hint as a hypothesis, not an execution label.
- N: P and W together (the unchanged original numeric-code model).
- F: N plus full-string suffix order (unchanged original full-code convention).

Thus feasible sets satisfy F subset N subset W subset T and N subset P subset T.
P and W need not contain each other. Compare ranges, certification, positive-loss
case counts, minimum withdrawal and minimum sufficient retention counts. Differences
are conditional on the other components; do not claim additive/causal attribution.

## Exact computation and validation

Use the old solver unchanged for P. For W, use an exact dynamic program over
resource-category multiplicities in ordinal groups, permitting interleaving of
subprocess chains. At most 2,000,000 reachable count vectors per timestamp block;
exceeding the cap produces UNKNOWN. Carry endpoint states across all blocks.
Verify against independent enumeration of original event permutations on small
instances, checking legality and complete witnesses. Also compare T/N/F reproduced
bounds with their saved case-level arrays and independently enumerate every new
case-query whose timestamp permutation space is at most 50,000, without using
compressed resource sequences in the reference implementation.

For every exactly solved model/query publish aggregate min/max, positive-loss
cases, largest loss, strict reversal count, sufficient retention count and coverage.
Keep real case IDs, per-event tables and full orders private. Retain all UNKNOWNs.
Record source hashes, runtime, state cap, and all results.

## Sufficient retention is a separate question

From all-T, retaining A constraints on K gives minimum L_T + sum_{c in K} d(c).
The smallest descending-loss prefix whose value is positive is a minimum
equal-case-cost sufficient retention set. An empty set suffices if L_T > 0;
no set suffices if L_A <= 0. This is not the same set or count as a minimum
failure witness. Confirmation must cover *all assumed precedences* in each
retained case, not just an interesting pair of records. No human effort claim.

## Provenance and key case

Inspect the official dataset description, the original 2015 report and Fluxicon's
2015 release statement (which says its Disco project sorts ties by action code).
If the linked CSV release can be acquired, match code/timestamp/resource multisets
for the already-used C0261 case and inspect row order. Do not call a redistributed
CSV a workflow audit trail. Do not infer exact sorting direction or suffix policy
from a general statement unless observable in the release. Record failures.

Inspect raw dateFinished/planned fields for the existing case; preserve their
status as recorded/planned attributes, without inventing execution semantics.
No contact with authors/process owners and no stakeholder study is authorized.
If no independent execution evidence is available, change title and all substantive
claims to *ordering-assumption dependence*, and report the missing verification
as an unresolved empirical limitation.
