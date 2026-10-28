"""Reconstruct and independently check every new P/W failure certificate."""
import csv
import itertools
import json
import re
from collections import Counter, defaultdict
from pathlib import Path

from extensions.assumptions_v10 import p_blocks, solve_w, retain
from extensions.order_evidence import solve, radius
from src.io import timestamp_us
from src.study_data import make_blocks


def validate(order, events, model):
    ids = [e['source_index'] for e in events]
    assert len(order) == len(ids) and set(order) == set(ids)
    pos = {v: i for i, v in enumerate(order)}
    bytime = defaultdict(list)
    for e in events: bytime[e['time']].append(e)
    lastmax = -1
    for t in sorted(bytime):
        block = bytime[t]
        assert min(pos[e['source_index']] for e in block) > lastmax
        lastmax = max(pos[e['source_index']] for e in block)
        if model == 'T': continue
        for a, b in itertools.permutations(block, 2):
            if len(block) == 1: continue
            x = re.fullmatch(r'(.+?)_(\d{3})(.*)', a['code'])
            y = re.fullmatch(r'(.+?)_(\d{3})(.*)', b['code'])
            required = (x[1] < y[1] if model == 'P' else x[1] == y[1] and int(x[2]) < int(y[2]))
            if required: assert pos[a['source_index']] < pos[b['source_index']]


def main():
    for label in ['M1', 'M3']:
        cfg = json.loads(Path('configs/core_v7_'+label+'.json').read_text())
        cases = defaultdict(list)
        for r in csv.DictReader(Path(cfg['cohort']).open()):
            r['source_index'] = int(r['source_index']); r['time'] = timestamp_us(r['timestamp'])
            cases[r['case_id']].append(r)
        ids = list(cases); run = Path('results/revision-v10')/label
        reports = json.loads((run/'queries.json').read_text())
        bounds = json.loads((run/'case-bounds-private.json').read_text())
        allchecks = []; arithmetic = 0
        with (run/'witnesses-private.jsonl').open('x') as stream:
            for report, b in zip(reports, bounds):
                e, f = tuple(report['edge_e']), tuple(report['edge_f'])
                weights = {e: 1, f: -1}
                tl = [v[0] for v in b['bounds']['T']]
                for model in ['P', 'W', 'N', 'F']:
                    if report['models'][model]['status'] != 'exact': continue
                    al = [v[0] for v in b['bounds'][model]]
                    losses = sorted((av-tv for av, tv in zip(al, tl)), reverse=True)
                    # Independent arithmetic implementation, without retain/radius.
                    restoration = next((i for i in range(len(losses)+1) if sum(tl)+sum(losses[:i]) > 0), None)
                    assert restoration == report['models'][model]['retention_count']
                    arithmetic += 1
                    count = report['models'][model]['reversal_count']
                    if model not in ['P', 'W'] or count is None: continue
                    rev = radius(al, tl, -1); selected = set(rev['indices'])
                    baseline_total = negative_total = 0
                    for i, (case, ev) in enumerate(cases.items()):
                        base = (solve_w(ev, weights, witness=True) if model == 'W' else
                                solve(p_blocks(ev), weights, witness=True))
                        changed = solve([[(x['source_index'], x['resource']) for x in block]
                                         for block in make_blocks(ev, 'T')], weights, witness=True) if i in selected else base
                        for value, policy in [(base, model), (changed, 'T' if i in selected else model)]:
                            validate(value[2], ev, policy)
                            rs = {x['source_index']: x['resource'] for x in ev}
                            score = sum(weights.get((rs[a], rs[b]), 0) for a, b in zip(value[2], value[2][1:]))
                            assert value[0] == score
                        assert base[0] == b['bounds'][model][i][0]
                        assert changed[0] == b['bounds']['T' if i in selected else model][i][0]
                        baseline_total += base[0]; negative_total += changed[0]
                        stream.write(json.dumps(dict(query=report['query'], model=model, case_id=case,
                            retained=i not in selected, baseline=base[2], negative=changed[2]))+'\n')
                    assert baseline_total > 0 and negative_total == rev['minimum'] < 0
                    assert baseline_total-sum(losses[:count-1]) >= 0
                    allchecks.append(dict(query=report['query'], model=model, withdrawal_count=count,
                                          baseline_margin=baseline_total, negative_margin=negative_total,
                                          all_other_case_orders_identical=True))
        (run/'certificates.json').write_text(json.dumps(dict(witnesses=allchecks, independent_retention_arithmetic_queries=arithmetic), indent=2))
        print(label, len(allchecks), 'new complete certificates and', arithmetic, 'retention counts checked', flush=True)


if __name__ == '__main__': main()
