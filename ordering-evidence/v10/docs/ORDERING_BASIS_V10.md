# Ordering basis: what is verified, and what is not

28 October 2026. Distinguish provenance of an analysis convention from evidence
that a business execution actually followed it. No process-owner interview or
execution-audit record was obtained. No stakeholder contact was made.

| Component | Primary source | Supported meaning | Unsupported inference | Treatment |
|---|---|---|---|---|
| Recorded timestamps | Original XES / UCI records | Recorded clock values | Physical/causal truth, or unreliability of original row order | Retain strict timestamp precedence; T is an information envelope |
| Municipal subprocess prefix | 4TU M1/M3 dataset descriptions | Subprocess identity | Prefix lexical order gives execution chronology | Separate P ablation; never call it validated |
| Municipal three-digit ordinal | Same publisher descriptions | An ordering hint | Every within-tie instance obeys it | Separate W hypothesis allowing cross-subprocess interleaving |
| Suffix | No field-level execution semantics found | Part of the recorded code | Alphabetic/numeric suffix chronology | F sensitivity convention only |
| Full-code sorting in analysis | Original Fluxicon 2015 release statement; downloaded CSV | An actual preprocessing convention was used | Export rows are original workflow audit order | Convention provenance confirmed for the fixed case |
| IT sys_mod_count | UCI 498 field dictionary | Cumulative incident-update count | Physical task order or true handover | C as recorded-update evidence, with equal counts unordered and conflicts retained |

Primary sources:

- [M1 publisher record](https://doi.org/10.4121/uuid:a0addfda-2044-4541-a450-fdcc9fe16d17)
- [M3 publisher record](https://doi.org/10.4121/uuid:ed445cdd-27d5-4d77-a1f7-59fe7360cfbe)
- [Original tool-release statement, 8 May 2015](https://fluxicon.com/blog/2015/05/bpi-challenge-2015/)
- [Original challenge report](https://ais.win.tue.nl/bpi/2015/bpic2015_paper_3.pdf)
- [UCI 498 dictionary](https://doi.org/10.24432/C57S4H)

## Exact-case release inspection

The already-selected C0261 case, not selected anew by outcome, has 75 events.
The linked public CSV matches the original XES multiset on activity code,
resource, local wall-clock timestamp and English label. Its 37-event critical
tie is full-code nondecreasing. The CSV has no timezone, so this is a component
comparison with the raw local clock, not byte identity or an inferred UTC check.
Its per-case file order is not chronological before timestamp sorting.
The CSV is a derivative of the same XES and supplies no independent execution
sequence. Detailed aggregate checks are in evidence/v10/release-case-check.json.

Original public ZIP: https://files.fluxicon.com/Datasets/BPIC/BPI-Challenge-2015.zip

SHA256: 4ccd2eff858ffb1bf7fc4b88cdef02f1230686ba2fffe22720dfdecf03ad8ebb

The ZIP and raw event-level inspection remain private/local; this artifact does
not redistribute the records. The report above confirms provenance of the
convention, while business_execution_order_verified remains false.

## Correction to the old application interpretation

The q12 one-case failure witness does not supply a one-case sufficient validation
list. N certifies [1,3], whereas W gives [-6,35]; the positive guarantee requires
the extra prefix convention. Starting from T, a positive N guarantee requires
all twenty positive-loss cases. Validation must cover each retained case's full
assumed precedence. No such validation has been completed. Audit output therefore
states conditional assumptions and a metadata request, not a corrected business fact.
