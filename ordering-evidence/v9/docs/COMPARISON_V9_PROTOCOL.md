# v9: margin versus ordering-evidence dependence

28 October 2026. This is a post-results descriptive extension. The v6-v8
queries/radii have already been examined; this document fixes the new summaries
before calculating them and does not claim preregistration or a fresh test set.
No new raw source, cohort, model, radius, optimization or query selection is added.

1. Use every exact query in each existing M1 N/F, M3 N/F and IT C result.
   Retain uncertified orientations separately; compute comparative diagnostics
   only among positive base certificates because those have the stated radius
   interpretation. Missing/UNKNOWN results cannot silently enter as infinity.
2. For each row report reference-source score difference, exact joint lower
   margin, strict-reversal radius and its percentage of the fixed case population.
   Infinity remains infinity, not 100%; already-uncertified is a separate status.
3. The main table includes ALL nine finite M1 N queries, ordered by original
   query number, plus q01, the first timestamp-stable query in that fixed order.
   The table is an illustrative complete subset, not an independent validation.
4. The fixed two counterexamples already highlighted by the user are q02
   (lower margin 36, radius 4) and q08 (16, 14). Obtain their sorted case-loss
   prefixes from the unchanged private case minima; publish only aggregate
   residual margins for withdrawals 0 through 20, no case IDs/individual orders.
   Check each crossing against the saved radius and the preceding prefix.
5. Cheap gap heuristics: ascending reference-source gap and ascending certified
   lower margin. Count strict pairwise disagreements with ascending radius over
   every certified query in each log/model; count only pairs having strictly
   different gaps AND radii. Treat infinity as larger than finite. Report tied
   gap groups and the complete minimum-gap selection family. Never break ties
   by resource/query ID. No tuned fragility threshold, selected budget, training,
   statistical significance, or performance-superiority claim is introduced.
6. Preserve all old inputs/results. Independently recompute the table arithmetic,
   inversion counts, percentages and cumulative minima. Run existing tests once;
   do not rerun the full numerical solver merely for prose/table changes.
7. Compress historical acquisition and permission details in the paper, retaining
   source semantics, denominators, unknowns, exploratory status and limits.
   Put detailed provenance/licence actions in the artifact. No inaccessible
   local file path, invented public URL or claimed DOI may substitute for a
   reviewer-accessible repository. Prepare a versioned, allowlisted standalone
   research artifact and release text before any public publication step.
8. Keep the user's v8 review confirmation bound to its original PDF hash.
   English spelling/author details persist; v9 changes are listed for delta review.
   No new author attestation, conference submission or external message is inferred.
