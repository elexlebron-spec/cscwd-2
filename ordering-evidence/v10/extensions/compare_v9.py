"""Post-results descriptive comparison; no optimization or population changes."""
import argparse
import csv
import hashlib
import itertools
import json
import math
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
SOURCES=[('M1',999,'evidence/revision-v7/M1/queries.json',['N','F']),
         ('M3',1409,'evidence/revision-v7/M3/queries.json',['N','F']),
         ('IT',24918,'evidence/v8/UCI498/core-r1/queries.json',['C'])]


def disagreement(rows,key):
    comparable=disagree=tied_gap=tied_radius=0
    for a,b in itertools.combinations(rows,2):
        x,y=a[key],b[key]
        u=math.inf if a['radius'] is None else a['radius']
        v=math.inf if b['radius'] is None else b['radius']
        tied_gap+=x==y;tied_radius+=u==v
        if x==y or u==v:continue
        comparable+=1;disagree+=(x<y)!=(u<v)
    least=min(r[key] for r in rows) if rows else None
    family=[dict(query=r['query'],radius=r['radius']) for r in rows if r[key]==least]
    return dict(comparable_pairs=comparable,strict_disagreements=disagree,
                equal_gap_pairs=tied_gap,equal_radius_pairs=tied_radius,
                minimum_gap=least,minimum_gap_selection_family=family)


def main():
    p=argparse.ArgumentParser();p.add_argument('--out',required=True)
    p.add_argument('--private-bounds',help='Local M1 case bounds; only cumulative aggregate output is written')
    a=p.parse_args();out=Path(a.out);out.mkdir(parents=True,exist_ok=False)
    rows=[];sources={}
    for label,n,name,models in SOURCES:
        path=ROOT/name;sources[name]=hashlib.sha256(path.read_bytes()).hexdigest()
        for r in json.loads(path.read_text()):
            for model in models:
                if r['status']!='exact':
                    rows.append(dict(log=label,model=model,query=r['query'],status='unknown'));continue
                info=r['models'][model];cert=info['strict_priority_certified'];rad=info['reversal_radius'] if cert else None
                rows.append(dict(log=label,model=model,query=r['query'],edge_e='>'.join(r['edge_e']),
                                 edge_f='>'.join(r['edge_f']),cases=n,
                                 source_gap=r.get('N_source_margin',r.get('C_source_margin')),
                                 lower=info['range'][0],upper=info['range'][1],T_lower=r['T_range'][0],
                                 status=('finite' if rad is not None else 'infinite') if cert else 'uncertified',
                                 radius=rad,withdrawal_percent=None if rad is None else 100*rad/n))
    with (out/'all-comparisons.csv').open('x',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
    diagnostics={}
    for label,_,_,models in SOURCES:
        for model in models:
            allrows=[r for r in rows if r['log']==label and r['model']==model]
            certified=[r for r in allrows if r['status'] in ('finite','infinite')]
            diagnostics[label+'_'+model]=dict(queries=len(allrows),certified=len(certified),
                                             uncertified=sum(r['status']=='uncertified' for r in allrows),
                                             finite=sum(r['status']=='finite' for r in certified),
                                             source_gap=disagreement(certified,'source_gap'),
                                             certified_lower=disagreement(certified,'lower'))
    selected=[r for r in rows if r['log']=='M1' and r['model']=='N' and (r['status']=='finite' or r['query']==1)]
    assert len(selected)==10 and sum(r['status']=='finite' for r in selected)==9
    table=['| Query | Source gap | N lower | Cases | Share (%) |','|---|---:|---:|---:|---:|']
    for r in selected:
        table.append('| q%02d | %d | %d | %s | %s |'%(r['query'],r['source_gap'],r['lower'],
                     'infinite' if r['radius'] is None else r['radius'],
                     '-' if r['radius'] is None else '%.2f'%r['withdrawal_percent']))
    (out/'paper-table.md').write_text('\n'.join(table)+'\n')
    (out/'heuristics.json').write_text(json.dumps(diagnostics,indent=2))
    if a.private_bounds:
        path=Path(a.private_bounds);private=json.loads(path.read_text());curves=[]
        for query in (2,8):
            r=next(x for x in rows if x['log']=='M1' and x['model']=='N' and x['query']==query)
            case=private[query-1];assert case['query']==query
            al=[x[0] for x in case['bounds']['N']];tl=[x[0] for x in case['bounds']['T']]
            assert len(al)==len(tl)==999 and sum(al)==r['lower']
            losses=sorted((x-y for x,y in zip(al,tl)),reverse=True);assert min(losses)>=0
            residual=sum(al)
            for m in range(21):
                if m:residual-=losses[m-1]
                curves.append(dict(query=query,withdrawals=m,residual_minimum=residual))
            crossing=next(x['withdrawals'] for x in curves if x['query']==query and x['residual_minimum']<0)
            assert crossing==r['radius']
        with (out/'cumulative-loss-curves.csv').open('x',newline='') as f:
            w=csv.DictWriter(f,fieldnames=['query','withdrawals','residual_minimum']);w.writeheader();w.writerows(curves)
        sources['local_private_bound_sha256']=hashlib.sha256(path.read_bytes()).hexdigest()
    (out/'provenance.json').write_text(json.dumps(dict(scope='post-results descriptive comparison',sources=sources,
        protocol_sha256=hashlib.sha256((ROOT/'docs/COMPARISON_V9_PROTOCOL.md').read_bytes()).hexdigest(),
        source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),rows=len(rows)),indent=2))
    print(json.dumps(diagnostics,indent=2))


if __name__=='__main__':main()
