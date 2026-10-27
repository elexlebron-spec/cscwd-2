"""Save and independently check a source/lexical reversal, without optimality claims."""
import csv
import json
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path


def main():
    cases = defaultdict(list)
    with open('results/dev2015-audit/dev.csv') as f:
        for row in csv.DictReader(f):
            cases[row['case_id']].append(row)
    # Selected after development inspection; report as an illustrative witness.
    e, f = ('R0015', 'R0006'), ('R0006', 'R0017')
    totals, witness = {}, []
    def instant(row):
        return datetime.fromisoformat(row['timestamp']).astimezone(timezone.utc)
    for mode in ['source', 'lex']:
        total = Counter()
        for case, rows in sorted(cases.items()):
            groups = defaultdict(list)
            for row in rows:
                groups[instant(row)].append(row)
            ordered = []
            for t in sorted(groups):
                block = groups[t]
                if mode == 'lex':
                    block = sorted(block, key=lambda r: r['resource'])
                ordered.extend(block)
            ids = [int(r['source_index']) for r in ordered]
            # Independent feasibility and objective verification from event IDs.
            index = {int(r['source_index']): r for r in rows}
            assert len(ids) == len(index) and set(ids) == set(index)
            replay = [index[i] for i in ids]
            times = [instant(r) for r in replay]
            assert times == sorted(times)
            count = Counter((a['resource'], b['resource']) for a, b in zip(replay,replay[1:])
                            if a['resource'] != b['resource'])
            total.update(count)
            witness.append({'mode':mode,'case_id':case,'event_source_indices':ids,
                            'edge_e_count':count[e],'edge_f_count':count[f]})
        totals[mode] = {'edge_e_count':total[e], 'edge_f_count':total[f], 'difference':total[e]-total[f]}
    assert totals['source']['difference'] > 0 > totals['lex']['difference']
    out = Path('results/dev2015-witness');out.mkdir(exist_ok=False)
    with (out/'orders.jsonl').open('x') as target:
        for record in witness: target.write(json.dumps(record)+'\n')
    summary = {'edge_e':e,'edge_f':f,'counts':totals,'cases':len(cases),
               'status':'strict_reversal_with_two_valid_witnesses',
               'scope':'timestamp-only block permutations; no causal or optimality claim',
               'selection':'illustrative pair selected after development inspection'}
    (out/'summary.json').write_text(json.dumps(summary,indent=2))
    print(json.dumps(summary,indent=2))


if __name__ == '__main__':
    main()
