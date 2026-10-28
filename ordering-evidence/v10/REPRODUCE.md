# Reproducing the ordering-evidence audit, v9

This artifact accompanies **How Much Ordering Evidence Supports a Collaboration
Ranking?** It separates aggregate inspection from full-data reproduction. All
case-withdrawal results are conditional on the declared ordering models; code
hints are not verified execution order. Read DATA_NOTICES.md before data reuse.

## 1. One-minute check without raw data

From the artifact root, Python 3.9+ standard library only:

```sh
python3 reproducibility/check_v9.py --manifest
python3 -m unittest discover -s tests -v
```

Expected: 225 log/model/query rows verified (135 distinct reference queries,
with N/F comparisons in each municipality), all percentages and diagnostic
counts, 42 aggregate curve points, and 33 unit tests. This verifies the supplied
aggregates against complete query tables; it is not a replacement for reconstructing
the original event records or independently checking every large-case extremum.

Main evidence files:

- evidence/v9/all-comparisons.csv: source gaps, exact joint ranges, radius/status,
  whole-case denominator and percentage for every query/model, including
  uncertified directions and infinite radii.
- evidence/v9/paper-table.md: all nine finite M1 N queries and q01 stable control.
- evidence/v9/heuristics.json: complete strict query-order disagreement counts
  and minimum-gap tie families, with no ID-based tie break.
- evidence/v9/cumulative-loss-curves.csv: q02 and q08 residual minima after
  the largest-loss withdrawals, for m=0 through 20.
- evidence/revision-v7/M1 and M3: complete original query tables and independent
  verification summaries; evidence/v8/UCI498: IT query tables and verification.

The comparison is post-results descriptive analysis, specified in
docs/COMPARISON_V9_PROTOCOL.md. No population, order model, radius or solver
budget was retuned. Existing source-query hashes remain in its provenance.

## 2. Recreate comparisons and figures

```sh
python3 -m extensions.compare_v9 --out results/my-comparison
python3 paper/make_comparison_v9.py
```

The first command needs only standard Python and the distributed aggregate
query files. The second requires matplotlib and uses published aggregate curve
points. It recreates Figure 1 as PNG/SVG; it does not infer any actual event
order. Table shares are minimum withdrawals divided by all 999 M1 core cases,
not by the number of positive-loss cases, and are not workload estimates.

## 3. Full raw-data reconstruction

Raw logs, actual case identifiers, normalized event tables and full permutations
are omitted. The following downloads are explicit user actions and require
network access. Each input is fixed by SHA256; municipal Git blobs are checked
by SHA1 too. Data citations and terms are in DATA_NOTICES.md. Run in a clean
artifact directory because preparation and result paths are exclusive-created.

### M1: original 999-case reserved cohort

```sh
python3 -m reproducibility.fetch_core --log M1
python3 -m reproducibility.prepare_m1_core
python3 -m extensions.run_v7 --config configs/core_v7_M1.json --out results/my-M1-core
python3 -m extensions.verify_v7 --run results/my-M1-core --raw data/raw/mirror-BPI_Challenge_2015.xes.gz --raw-sha256 d5847a409cec1de1b7382b59365aec6af8e53e1c2ac083201e7679c22a6ef525 --out results/my-M1-independent.json
```

Preparation recreates the unchanged hash-ordered split, global resource aliases
and cohort bytes; it does not rerun or reinterpret the earlier incident/loan
background studies. The cohort hash is guarded by configs/core_v7_M1.json.

### M3: all 1,409 cases

```sh
python3 -m reproducibility.fetch_core --log M3
python3 -m extensions.prepare_m3_v7
python3 -m extensions.run_v7 --config configs/core_v7_M3.json --out results/my-M3-core
python3 -m extensions.verify_v7 --run results/my-M3-core --raw data/raw/mirror-BPI_Challenge_2015_M3.xes.gz --raw-sha256 7ffc2552130921c6fbc0ffc6c519be56775a4352ea22b4ceba5db0f72bfa67d4 --out results/my-M3-independent.json
```

### IT: all 24,918 incidents

```sh
python3 -m reproducibility.fetch_core --log IT
python3 -m extensions.uci_v8 --raw data/provenance/v8/uci498.zip --out results/revision-v8/UCI498
python3 -m extensions.run_uci_v8 --config configs/core_v8_UCI498.json --out results/my-IT-core
python3 -m extensions.verify_uci_v8 --run results/my-IT-core --raw data/provenance/v8/uci498.zip --raw-sha256 6294e29a311647306bfdfc85783f7df66517c197b9cd49aa5ee36ba9c525d1d6 --out results/my-IT-independent.json
```

Five counter-conflict cases stay in the population and use T in both models.
The declared resource is the updater, not the assigned worker. Local timestamps
remain timezone-unspecified; no records are deduplicated. All 45 priorities
remain positive under T, and therefore no finite IT witness is expected.

### Regenerate the cumulative-loss plot data from local case minima

```sh
python3 -m extensions.compare_v9 --out results/my-comparison-from-raw --private-bounds results/my-M1-core/case-bounds-private.json
```

Compare the regenerated CSV to evidence/v9/cumulative-loss-curves.csv. The
published file contains only cumulative query minima, no case identifiers or
event sequences. Local bounds and witness files must not be added to the public
artifact. M1 has 18 full N/F certificates; M3 has 33; IT has zero. The independent
verifiers reconstruct raw records and replay those full finite certificates.
Per-case exhaustive coverage is recorded separately from complete witness replay.

## 4. Reproduction scope and machine requirements

The reported M1/M3/IT runs took about 21-36 seconds per measured process on an
Apple M4 with 16 GiB RAM; this is an observation, not a cross-machine guarantee.
Memory is process RSS, below 497 MiB in those runs; Python/JSON versions and
other machines may differ. No GPU, model endpoint, paid API or LLM order
prediction is used. Figure rendering optionally needs matplotlib; numerical
checks and experiment code use the standard library.

The original frozen numerical engine is unchanged. Exact count-state cap is
two million per block; unsupported work must remain UNKNOWN. Complete candidate
construction, score ties, self-transition handling and case boundaries are
preserved. Never replace joint signed optimization with independently attained
edge extrema. The dataset-specific generation/verification instructions above
are the core-paper path; historical background instructions are separate.
