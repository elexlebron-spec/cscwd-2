# v8: source semantics, non-municipal replication, and release audit

Fixed 28 October 2026 before downloading or inspecting UCI 498 event rows.
The v4-v7 populations, code, outputs and protocols remain historical evidence.

## Source choice and stopping rule

Select only UCI Incident management process enriched event log, DOI
10.24432/C57S4H. The publisher documents sys_mod_count as incident updates
until that moment, sys_updated_at as the system-update timestamp, and
sys_updated_by as the updater generating the log record. This is stronger
source support than municipal code hints. BPI 2014 activity numbers and BPI
2017 UUIDs are not selected: their temporal semantics have not been established.
Do not switch datasets or choose a second resource field after seeing rankings.
Retain a null or failed replication. Download the official UCI archive, preserve
bytes and SHA256, and keep all source records, including exact duplicates.

## Fixed population and models

Use all incidents, not a ranking-selected sample. A whole incident is ineligible
only if its identifier, sys_updated_by, sys_updated_at or nonnegative integer
sys_mod_count is absent/invalid. Report raw and excluded cases/events, including
each exclusion reason and overlapping reasons. Resource is the record updater,
not assigned_to or assignment_group. Parse timestamps as day/month/year H:M
(also accept an explicit seconds component); do not invent a timezone. Use the
same local clock representation within every case.

T: timestamps alone, all orders within equal timestamps.
C: refine each timestamp block by ascending sys_mod_count; equal counts remain
unordered. Strictly earlier timestamps retain precedence. If a case contains a
counter contradiction across strictly different timestamps (an earlier record
has a larger count), mark its counter evidence unsupported and use T for that
entire case in BOTH T and C; do not delete it. Preserve repeated counts, duplicate
rows and all original indices. No sorting by resource IDs. No inferred lifecycle
precedence, activity-name sequence or counter interpolation. C concerns recorded
updates, not physical work or causal handover.

## Queries and computation

Construct the complete candidates from within/adjacent blocks. Select the C
source top-ten cutoff union including all score ties, and query every strictly
different-score pair oriented from higher to lower C source score. Also report
top-five pair membership. Same objective D=W(e)-W(f), self transitions zero,
case boundaries retained. Use the unchanged v6 multiplicity solver with the same
2,000,000-count-vector cap. UNKNOWN remains UNKNOWN. Compute minima/maxima,
case losses, both thresholds (0 and -1), and every finite strict-reversal paired
witness. Unwithdrawn cases must have identical orders in both witnesses. Report
all query directions, zero-loss outcomes and base-model noncertifications.

Independent verification must reconstruct rows, blocks, counters, candidates and
query selection without the runner's block builder; enumerate cases with at
most 10,000 distinct resource orders, check every covered case-query bound,
and replay all full paired witnesses including m-1 minimality. Report coverage.
Run three fresh sequential measured processes, including all finite certificate
generation; exclude acquisition/parsing and independent verification as in v7.
No MC, resampling or significance test is necessary for this descriptive addition.

## Municipal semantics and rights

Read publisher descriptions and the 2015 original report. Distinguish explicitly
supported code hints from unsupported subprocess/suffix execution precedences.
Count code inversions across strictly different timestamps by case/subprocess
for M1 and M3 as a diagnostic, not a ground-truth test inside timestamp ties.
Do not promote heuristics to validated business order. If source support is
insufficient, retain N/F only as conditional sensitivity scenarios and base
operational recommendations on timestamp-only outcomes. No process-owner or
author attestation is manufactured.

Retrieve the complete 4TU dataset terms (not the CC0 metadata/terms-document
license), record exact source, version/date, hashes and clause-level actions.
Check official file MD5 when available against each mirror. UCI CC BY 4.0 is
reviewed separately. Do not redistribute raw logs or full event/case sequences.
Before any optional public release, build and inspect an allowlisted package
with citations/rights notices and no private identifiers. No public upload or
submission is authorized by this protocol.

## Author review

Agent checks cover numerical provenance, citations, wording, signature consistency,
data notices and reproducibility. They do not constitute the author's scientific
approval. Provide a concrete Chinese review sheet tied to the final PDF hash;
leave human review pending until the user explicitly supplies it. Affiliation,
email and Chinese name use the user's supplied details; English transliteration
is provisional until the author confirms it. Preserve the AI-assistance disclosure.
