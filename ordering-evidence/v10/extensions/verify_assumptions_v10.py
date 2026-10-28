"""Independent event-permutation oracle; no imports from optimization modules."""
import argparse
import csv
import datetime
import itertools
import json
import math
import re
from collections import Counter, defaultdict
from pathlib import Path


def main():
    p = argparse.ArgumentParser(); p.add_argument('--dataset', choices=['M1', 'M3'], required=True)
    a = p.parse_args(); run = Path('results/revision-v10')/a.dataset
    cfg = json.loads(Path('configs/core_v7_'+a.dataset+'.json').read_text())
    cases = defaultdict(list)
    for row in csv.DictReader(Path(cfg['cohort']).open()):
        row['time'] = datetime.datetime.fromisoformat(row['timestamp'])
        row['source_index'] = int(row['source_index'])
        match = re.fullmatch(r'(.+?)_(\d{3})(.*)', row['code'])
        # Missing code is permitted on singleton timestamp blocks. If it ever
        # occurs on a tied block, abort below rather than invent precedence.
        row['prefix'], row['ordinal'] = (match[1], int(match[2])) if match else (None, None)
        cases[row['case_id']].append(row)
    reports = json.loads((run/'queries.json').read_text())
    saved = json.loads((run/'case-bounds-private.json').read_text())
    pairs = [(tuple(q['edge_e']), tuple(q['edge_f'])) for q in reports]
    checked = Counter(); examples = 0
    for i, (case, events) in enumerate(cases.items()):
        groups = defaultdict(list)
        for ev in events:
            groups[ev['time']].append(ev)
        blocks = [groups[t] for t in sorted(groups)]
        assert all(len(b) == 1 or all(e['prefix'] is not None for e in b) for b in blocks)
        possibilities = math.prod(math.factorial(len(b)) for b in blocks)
        if possibilities > 50000:
            continue
        for model in ['P', 'W']:
            orders = []
            for block in blocks:
                valid = []
                for order in itertools.permutations(block):
                    positions = {ev['source_index']: j for j, ev in enumerate(order)}
                    precedences = ((x, y) for x, y in itertools.permutations(block, 2)
                        if (model == 'P' and x['prefix'] < y['prefix']) or
                        (model == 'W' and x['prefix'] == y['prefix'] and x['ordinal'] < y['ordinal']))
                    if all(positions[x['source_index']] < positions[y['source_index']] for x, y in precedences):
                        valid.append(order)
                orders.append(valid)
            lows = [math.inf]*len(pairs); highs = [-math.inf]*len(pairs)
            for choice in itertools.product(*orders):
                seq = [ev['resource'] for block in choice for ev in block]
                scores = Counter(zip(seq, seq[1:]))
                for q, (e, f) in enumerate(pairs):
                    d = scores[e]-scores[f]
                    lows[q] = min(lows[q], d); highs[q] = max(highs[q], d)
            for q in range(len(pairs)):
                assert saved[q]['case_ids'][i] == case
                assert saved[q]['bounds'][model][i] == [lows[q], highs[q]], (a.dataset, i, q, model)
                checked[model] += 1
        examples += 1
    result = dict(dataset=a.dataset, cases_enumerated=examples, total_cases=len(cases),
                  original_event_permutation_cap=50000, query_bound_checks=dict(checked),
                  optimizer_imported=False, all_passed=True)
    (run/'independent.json').write_text(json.dumps(result, indent=2))
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
