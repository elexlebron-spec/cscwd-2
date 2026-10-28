"""Fixed-query component ablation; saved T/N/F arrays remain immutable."""
import argparse
import csv
import datetime
import hashlib
import json
import resource
import time
from collections import Counter, defaultdict
from pathlib import Path

from extensions.assumptions_v10 import p_blocks, solve_w, retain
from extensions.order_evidence import solve, radius, Unsupported
from src.core import cheap_edge_bounds
from src.io import timestamp_us
from src.study_data import make_blocks


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--dataset', required=True, choices=['M1', 'M3'])
    ap.add_argument('--out', required=True)
    args = ap.parse_args()
    root = Path('results/revision-v10')
    freeze = json.loads((root/'design-freeze.json').read_text())
    for name, expected in freeze['source_hashes'].items():
        assert digest(name) == expected, name
    label = args.dataset
    config = json.loads(Path('configs/core_v7_'+label+'.json').read_text())
    assert digest(config['cohort']) == config['cohort_sha256']
    old = Path('results/revision-v7')/label/'core-r1'
    assert digest(old/'case-bounds-private.json') == freeze['prior_bounds_sha256'][label]
    prior = json.loads((old/'case-bounds-private.json').read_text())
    queries = json.loads((old/'queries.json').read_text())
    cases = defaultdict(list)
    for row in csv.DictReader(Path(config['cohort']).open()):
        row['source_index'] = int(row['source_index'])
        row['time'] = timestamp_us(row['timestamp'])
        cases[row['case_id']].append(row)
    ids = list(cases)
    pp = [p_blocks(e) for e in cases.values()]
    cand = [set(cheap_edge_bounds([[e['resource'] for e in b] for b in make_blocks(ev, 'T')]))
            for ev in cases.values()]
    out = Path(args.out); out.mkdir(parents=True, exist_ok=False)
    records = []; bounds_private = []; stats = {}
    started = time.perf_counter()
    for query, oldbound in zip(queries, prior):
        qid = query['query']
        assert oldbound['case_ids'] == ids and oldbound['query'] == qid
        e, f = tuple(query['edge_e']), tuple(query['edge_f'])
        weights = {e: 1, f: -1}
        bounds = {k: oldbound['bounds'][k] for k in ['T', 'N', 'F']}
        for model in ['P', 'W']:
            values = []
            for i, ev in enumerate(cases.values()):
                if not ({e, f} & cand[i]):
                    values.append([0, 0]); continue
                try:
                    lo, hi, _ = (solve(pp[i], weights) if model == 'P' else
                                 solve_w(ev, weights, stats=stats))
                    values.append([lo, hi])
                except Unsupported:
                    values.append(None)
            bounds[model] = values
        report = dict(query=qid, edge_e=e, edge_f=f,
                      N_source_margin=query['N_source_margin'], models={})
        for model in ['T', 'P', 'W', 'N', 'F']:
            unknown = sum(b is None for b in bounds[model])
            if unknown:
                report['models'][model] = dict(status='UNKNOWN', unknown_cases=unknown)
                continue
            lows = [b[0] for b in bounds[model]]
            highs = [b[1] for b in bounds[model]]
            tl = [b[0] for b in bounds['T']]
            losses = [a-t for a, t in zip(lows, tl)]
            assert min(losses) >= 0
            rev = radius(lows, tl, -1) if sum(lows) > 0 else None
            keep = retain(lows, tl)
            report['models'][model] = dict(status='exact', lower=sum(lows), upper=sum(highs),
                certified=sum(lows) > 0, positive_loss_cases=sum(d > 0 for d in losses),
                max_case_loss=max(losses), total_loss=sum(losses),
                reversal_count=rev['count'] if rev else None,
                retention_count=keep['count'] if keep else None,
                retention_minimum=keep['minimum'] if keep else None)
        for i in range(len(ids)):
            for a, b in [('T', 'P'), ('T', 'W'), ('P', 'N'), ('W', 'N'), ('N', 'F')]:
                x, y = bounds[a][i], bounds[b][i]
                if x is not None and y is not None:
                    assert x[0] <= y[0] <= y[1] <= x[1], (qid, i, a, b, x, y)
        records.append(report)
        bounds_private.append(dict(query=qid, case_ids=ids, bounds=bounds))
        print(json.dumps(dict(dataset=label, query=qid, done=len(records))), flush=True)
    (out/'queries.json').write_text(json.dumps(records, indent=2))
    (out/'case-bounds-private.json').write_text(json.dumps(bounds_private))
    summary = dict(dataset=label, cases=len(ids), events=sum(map(len, cases.values())),
                   queries=len(records), seconds=time.perf_counter()-started,
                   peak_RSS_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
                   W_state_profile=stats, models={})
    for model in ['T', 'P', 'W', 'N', 'F']:
        vals = [r['models'][model] for r in records]
        exact = [v for v in vals if v['status'] == 'exact']
        certified = [v for v in exact if v['certified']]
        finite = [v['reversal_count'] for v in certified if v['reversal_count'] is not None]
        retained = [v['retention_count'] for v in certified]
        summary['models'][model] = dict(exact=len(exact), certified=len(certified),
            finite_reversals=len(finite), radii=sorted(finite),
            sufficient_retention_counts=sorted(retained),
            zero_retention=sum(v == 0 for v in retained))
    (out/'summary.json').write_text(json.dumps(summary, indent=2))
    print(json.dumps(summary, indent=2))


if __name__ == '__main__':
    main()
