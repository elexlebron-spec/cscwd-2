# Case-order assumption dependence: v10 reproducibility artifact

Paper: *Auditing Case-Order Dependence in Resource-Adjacency Priorities*.

This revision corrects the interpretation of municipal order assumptions. A
2015 public release documents code sorting, and a fixed-case inspection
confirms that preprocessing convention. Neither supplies independent execution
order. P isolates cross-subprocess prefix sorting; W orders only ordinals
within a subprocess and permits cross-subprocess interleaving. All 90 original
municipal queries and both frozen populations remain unchanged.

Quick start (standard Python, no raw data):

```sh
python3 reproducibility/check_v10.py --manifest
python3 -m unittest discover -s tests -v
```

Read docs/REPRODUCE_V10.md for complete event-level reconstruction and
ORDERING_BASIS_V10.md for the limits of the evidence. The saved reports contain
450 component/query rows, effective ambiguity/exposure counts, 113,580 new
independent bound comparisons, 14 complete new P/W certificate checks, and 360
sufficient-retention arithmetic checks. The quick script checks aggregate
consistency; it does not rerun event-level experiments without the raw logs.

Key correction: q12's N range is [1,3], but W gives [-6,35]. Its one-case failure
witness is not a sufficient validation list: twenty N cases must be retained
when other cases use T. Validation of all assumed precedences remains
conditional and has not been performed with process owners.

Prior v9 query tables/figures and all historical protocols remain available.
REPRODUCE.md is the older base-data route; docs/REPRODUCE_V10.md adds the current
analysis. Do not infer that any v9 title or historical positive statement
validates the stronger business interpretation corrected in v10.

No raw event logs, real case identifiers, complete event permutations, private
author correspondence, or local machine paths are included. Data citations and
rights notices remain in DATA_NOTICES.md. No conference submission or stakeholder
contact is performed by these scripts.
