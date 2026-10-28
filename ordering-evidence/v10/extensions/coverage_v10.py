"""Report effective ambiguity, including target-exposed mixed blocks."""
import csv
import datetime
import hashlib
import json
from collections import defaultdict
from pathlib import Path


def main():
    out = Path('results/revision-v10'); result = {}
    for label in ['M1', 'M3', 'UCI498']:
        cfg = json.loads(Path('configs/'+('core_v8_UCI498.json' if label == 'UCI498' else 'core_v7_'+label+'.json')).read_text())
        p = Path(cfg['cohort']); assert hashlib.sha256(p.read_bytes()).hexdigest() == cfg['cohort_sha256']
        cases = defaultdict(list)
        for row in csv.DictReader(p.open()):
            row['stamp'] = datetime.datetime.fromisoformat(row['timestamp'])
            cases[row['case_id']].append(row)
        qpath = ('evidence/v8/UCI498/core-r1/queries.json' if label == 'UCI498' else
                 'results/revision-v10/'+label+'/queries.json')
        queries = json.loads(Path(qpath).read_text())
        mixed = mixedcases = mixedrecords = tied = maxmixed = 0
        related = {r['query']: [0, set()] for r in queries}
        for ci, ev in enumerate(cases.values()):
            grouped = defaultdict(list)
            for e in ev: grouped[e['stamp']].append(e)
            blocks = [grouped[t] for t in sorted(grouped)]
            had = False
            for j, block in enumerate(blocks):
                tied += len(block) > 1
                rs = {e['resource'] for e in block}
                if len(rs) < 2: continue
                had = True; mixed += 1; mixedrecords += len(block); maxmixed = max(maxmixed, len(block))
                exposed = {(a, b) for a in rs for b in rs if a != b}
                if j:
                    exposed.update((e['resource'], b) for e in blocks[j-1] for b in rs if e['resource'] != b)
                if j+1 < len(blocks):
                    exposed.update((a, e['resource']) for a in rs for e in blocks[j+1] if a != e['resource'])
                for q in queries:
                    if {tuple(q['edge_e']), tuple(q['edge_f'])} & exposed:
                        related[q['query']][0] += 1; related[q['query']][1].add(ci)
            mixedcases += had
        result[label] = dict(cases=len(cases), events=sum(map(len, cases.values())), tied_blocks=tied,
            mixed_blocks=mixed, mixed_cases=mixedcases, mixed_records=mixedrecords, max_mixed_block=maxmixed,
            target_exposure_definition='Mixed T block with a candidate target edge internally or incident to an adjacent timestamp block; conservative exposure, not proven nonzero loss.',
            queries=[dict(query=q, exposed_blocks=v[0], exposed_cases=len(v[1])) for q, v in related.items()])
    (out/'effective-coverage.json').write_text(json.dumps(result, indent=2))
    print(json.dumps({k: {n: v for n, v in x.items() if n != 'queries'} for k, x in result.items()}, indent=2))


if __name__ == '__main__': main()
