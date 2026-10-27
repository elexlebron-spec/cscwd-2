"""Verify manuscript aggregate comparisons without raw records or dependencies."""
import argparse
import csv
import hashlib
import itertools
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--manifest',action='store_true',help='Also verify the release MANIFEST.sha256')
    args=parser.parse_args()
    manifest=ROOT/'MANIFEST.sha256'
    if args.manifest:
        assert manifest.exists(),'Release manifest is required for --manifest'
        for line in manifest.read_text().splitlines():
            expected,name=line.split('  ',1);p=(ROOT/name).resolve()
            assert p.is_relative_to(ROOT) and p.is_file()
            assert hashlib.sha256(p.read_bytes()).hexdigest()==expected,name
    rows=list(csv.DictReader((ROOT/'evidence/v9/all-comparisons.csv').open()))
    assert len(rows)==225
    sources={'M1':('evidence/revision-v7/M1/queries.json',999),
             'M3':('evidence/revision-v7/M3/queries.json',1409),
             'IT':('evidence/v8/UCI498/core-r1/queries.json',24918)}
    lookup={k:{r['query']:r for r in json.loads((ROOT/path).read_text())} for k,(path,_) in sources.items()}
    for r in rows:
        q=lookup[r['log']][int(r['query'])];v=q['models'][r['model']]
        assert int(r['source_gap'])==q.get('N_source_margin',q.get('C_source_margin'))
        assert [int(r['lower']),int(r['upper'])]==v['range']
        if not v['strict_priority_certified']:assert r['status']=='uncertified';continue
        if v['reversal_radius'] is None:assert r['status']=='infinite' and r['radius']=='';continue
        radius=int(r['radius']);assert radius==v['reversal_radius']
        assert abs(float(r['withdrawal_percent'])-100*radius/sources[r['log']][1])<1e-10
    expected=json.loads((ROOT/'evidence/v9/heuristics.json').read_text())
    for key,info in expected.items():
        log,model=key.split('_')
        sample=[r for r in rows if r['log']==log and r['model']==model and r['status'] in ('finite','infinite')]
        for label,column in [('source_gap','source_gap'),('certified_lower','lower')]:
            total=disagreements=0
            for a,b in itertools.combinations(sample,2):
                gap=int(a[column])-int(b[column])
                x=None if not a['radius'] else int(a['radius']);y=None if not b['radius'] else int(b['radius'])
                order=0 if x==y else 1 if x is None else -1 if y is None else (x>y)-(x<y)
                if gap and order:total+=1;disagreements+=gap*order<0
            assert (disagreements,total)==(info[label]['strict_disagreements'],info[label]['comparable_pairs'])
    curves=list(csv.DictReader((ROOT/'evidence/v9/cumulative-loss-curves.csv').open()))
    for q,threshold in [(2,4),(8,14)]:
        points=[r for r in curves if int(r['query'])==q]
        assert [int(r['withdrawals']) for r in points]==list(range(21))
        assert int(points[0]['residual_minimum'])==lookup['M1'][q]['models']['N']['range'][0]
        assert next(int(r['withdrawals']) for r in points if int(r['residual_minimum'])<0)==threshold
    print('PASS: 225 model/query rows, percentages, all gap-order comparisons and 42 aggregate curve points.')
    print('Scope: aggregate consistency only. Full raw-data reconstruction is documented in REPRODUCE.md.')


if __name__=='__main__':main()
