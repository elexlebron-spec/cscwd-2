# v10 component and retention analysis

Use the standalone artifact root. All prior models, populations and query
directions are unchanged. Read ASSUMPTION_V10_PROTOCOL.md and
ORDERING_BASIS_V10.md first. The source evidence does not validate execution order.

## Data-free checks

```sh
python3 reproducibility/check_v10.py --manifest
python3 -m unittest discover -s tests -v
```

Expected: 450 component rows, 113,580 independently enumerated bound comparisons
in the saved report, 14 new complete certificate replays, 360 independent
retention arithmetic checks, and 37 tests. The quick checker tests consistency
of saved aggregates; it does not repeat event-level enumeration without raw data.

## Full reconstruction

Follow REPRODUCE.md to fetch the hash-fixed M1 and M3 inputs and recreate their
cohorts. Generate the original T/N/F arrays at these exact paths (instead of the
example results/my-* paths in the older instructions):

```sh
python3 -m extensions.run_v7 --config configs/core_v7_M1.json --out results/revision-v7/M1/core-r1
python3 -m extensions.run_v7 --config configs/core_v7_M3.json --out results/revision-v7/M3/core-r1
mkdir -p results/revision-v10
cp evidence/v10/design-freeze.json results/revision-v10/design-freeze.json
python3 -m extensions.run_assumptions_v10 --dataset M1 --out results/revision-v10/M1
python3 -m extensions.run_assumptions_v10 --dataset M3 --out results/revision-v10/M3
python3 -m extensions.verify_assumptions_v10 --dataset M1
python3 -m extensions.verify_assumptions_v10 --dataset M3
python3 -m extensions.certificates_v10
```

Outputs are exclusive-created. Do not run twice into the same directories.
The runners check protocol, implementation, cohort and previous case-array hashes.
New finite P/W certificates retain every original index and check precedence,
scores, minimum count and unchanged other-case orders. The independent oracle
enumerates actual distinct events (50,000 full-case timestamp permutations cap),
not just merged resources. Larger cases remain covered by the exact solver but
are not claimed exhaustively enumerated.

To recreate effective coverage for all three logs, also recreate IT's cohort
as in REPRODUCE.md, then run python3 -m extensions.coverage_v10.

To inspect the original CSV release, download the linked ZIP in
ORDERING_BASIS_V10.md to data/provenance/v10/fluxicon-BPI-Challenge-2015.zip,
check its SHA256, and run python3 -m extensions.provenance_v10. Neither the
ZIP nor any downloaded event table is included in this public artifact.

## Interpretation

N and F remain conditional historical preprocessing scenarios. W removes
cross-subprocess and suffix order but still assumes within-subprocess ordinal
precedence. P has no demonstrated business chronology. All finite municipal
results require assumptions; no field experiment or process-owner verification
was performed. The original v9 gap curves remain available as conditional N
results. A minimum failure set is never labelled a sufficient validation list.
