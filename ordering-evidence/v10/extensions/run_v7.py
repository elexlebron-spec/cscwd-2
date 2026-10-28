"""Exploratory, frozen-design analysis of case-level ordering-assumption dependence."""
import argparse
import csv
import hashlib
import itertools
import json
import math
import time
import resource
import platform
import sys
from collections import Counter,defaultdict
from pathlib import Path
from extensions.order_evidence import solve as original_solve,radius,Unsupported
from src.core import cheap_edge_bounds,score_bounds
from src.io import timestamp_us
from src.study_data import make_blocks


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--config',required=True);parser.add_argument('--out',required=True);args=parser.parse_args()
    started=time.perf_counter();out=Path(args.out);out.mkdir(parents=True,exist_ok=False)
    config=json.loads(Path(args.config).read_text())
    digest=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
    assert digest('docs/CORE_REPLICATION_V7_PROTOCOL.md')==config['protocol_sha256']
    for name,value in config['source_hashes'].items():assert digest(name)==value,name
    cohort=Path(config['cohort']);assert digest(cohort)==config['cohort_sha256']
    freeze={'settings':{'max_count_states_per_block':2000000}}
    stats={'solve_calls':0,'solved_blocks':0,'max_count_vectors':0,'max_DP_states':0,'total_DP_states':0,'max_categories':0}
    def solve(blocks,weights,cap=2000000,witness=False):
        active={r for edge,value in weights.items() if value for r in edge}
        stats['solve_calls']+=1
        for block in blocks:
            counts=Counter(r if r in active else '__OTHER__' for _,r in block)
            ns=list(counts.values()) if len(counts)>1 else [1]
            P=math.prod(n+1 for n in ns)
            actual=sum(n*math.prod(ns[k]+1 for k in range(len(ns)) if k!=j) for j,n in enumerate(ns))
            stats['solved_blocks']+=1;stats['max_count_vectors']=max(stats['max_count_vectors'],P)
            stats['max_DP_states']=max(stats['max_DP_states'],actual);stats['total_DP_states']+=actual
            stats['max_categories']=max(stats['max_categories'],len(ns))
        return original_solve(blocks,weights,cap,witness)
    cases=defaultdict(list)
    for row in csv.DictReader(cohort.open()):
        row['source_index']=int(row['source_index']);row['time']=timestamp_us(row['timestamp']);cases[row['case_id']].append(row)
    ids=list(cases);blocksets={};candidates={}
    for model in ['T','N','F']:
        blocksets[model]=[];candidates[model]=[]
        for events in cases.values():
            blocks=[[(e['source_index'],e['resource']) for e in b] for b in make_blocks(events,model)]
            blocksets[model].append(blocks)
            candidates[model].append(set(cheap_edge_bounds([[r for _,r in b] for b in blocks])))
    from src.core import counts,top_k_profile
    scores=Counter();all_candidates=set()
    for blocks,cand in zip(blocksets['N'],candidates['N']):
        scores.update(counts([r for b in blocks for _,r in b]));all_candidates.update(cand)
    scores={edge:scores[edge] for edge in all_candidates}
    profiles={str(k):{'source':top_k_profile(scores,k)} for k in [5,10]}
    important=set(map(tuple,profiles['10']['source']['strict']+profiles['10']['source']['boundary']))
    top5=set(map(tuple,profiles['5']['source']['strict']+profiles['5']['source']['boundary']))
    pairs=[]
    for a,b in itertools.combinations(sorted(important),2):
        if scores[a]!=scores[b]:pairs.append((a,b) if scores[a]>scores[b] else (b,a))
    reports=[];case_bounds=[];witnesses=0;cross_checks=Counter();max_states=0
    with (out/'witnesses-private.jsonl').open('x') as stream:
        for number,(e,f) in enumerate(pairs,1):
            q={e:1,f:-1};bounds={};unsupported=False
            for model in ['T','N','F']:
                values=[]
                for i,blocks in enumerate(blocksets[model]):
                    if not ({e,f}&candidates[model][i]):lo=hi=0
                    else:
                        try:lo,hi,_=solve(blocks,q,freeze['settings']['max_count_states_per_block'])
                        except Unsupported:unsupported=True;values.append(None);continue
                        reference=score_bounds([[r for _,r in b] for b in blocks],q,max_block=10)
                        if reference is not None:
                            assert (lo,hi)==reference,(number,model,i,(lo,hi),reference)
                            cross_checks[model]+=1
                    values.append([lo,hi])
                bounds[model]=values
            record=dict(query=number,edge_e=e,edge_f=f,within_N_source_top5=e in top5 and f in top5,N_source_margin=scores[e]-scores[f],status='unknown' if unsupported else 'exact',models={})
            if not unsupported:
                tl=[p[0] for p in bounds['T']]
                record['T_range']=[sum(tl),sum(p[1] for p in bounds['T'])]
                for model in ['N','F']:
                    al=[p[0] for p in bounds[model]];ah=[p[1] for p in bounds[model]]
                    assert all(bounds['T'][i][0]<=al[i]<=ah[i]<=bounds['T'][i][1] for i in range(len(ids)))
                    tie=radius(al,tl,0);rev=radius(al,tl,-1)
                    losses=[a-t for a,t in zip(al,tl)]
                    info=dict(range=[sum(al),sum(ah)],strict_priority_certified=sum(al)>0,
                              positive_loss_cases=sum(x>0 for x in losses),max_case_loss=max(losses),
                              tie_radius=None if tie is None else tie['count'],
                              reversal_radius=None if rev is None else rev['count'],
                              reversal_witness_margin=None if rev is None else rev['minimum'],
                              selected_case_aliases=[] if rev is None else ['C%04d'%(i+1) for i in rev['indices']])
                    if sum(al)>0 and rev is not None:
                        selected=set(rev['indices']);total=0
                        for i,case in enumerate(ids):
                            policy='T' if i in selected else model
                            low,_,order=solve(blocksets[policy][i],q,freeze['settings']['max_count_states_per_block'],witness=True)
                            assert low==bounds[policy][i][0]
                            baseline=order if i not in selected else solve(blocksets[model][i],q,freeze['settings']['max_count_states_per_block'],witness=True)[2]
                            stream.write(json.dumps(dict(query=number,base_model=model,case_id=case,case_alias='C%04d'%(i+1),relaxed=i in selected,baseline=baseline,negative=order))+'\n')
                            total+=low
                        assert total==rev['minimum']<0
                        witnesses+=1
                    record['models'][model]=info
            reports.append(record)
            case_bounds.append(dict(query=number,edge_e=e,edge_f=f,case_ids=ids,bounds=bounds))
            print(json.dumps(dict(done=number,total=len(pairs),status=record['status'])),flush=True)
    (out/'queries.json').write_text(json.dumps(reports,indent=2))
    (out/'case-bounds-private.json').write_text(json.dumps(case_bounds))
    summary=dict(scope=config['scope'],dataset=config['dataset'],
                 cases=len(ids),events=sum(map(len,cases.values())),queries=len(pairs),
                 top5_queries=sum(r['within_N_source_top5'] for r in reports),
                 exact_queries=sum(r['status']=='exact' for r in reports),
                 independent_subset_DP_cross_checks=dict(cross_checks),strict_reversal_witness_queries=witnesses,
                 models={},seconds=time.perf_counter()-started,peak_RSS_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*(1 if sys.platform=='darwin' else 1024),state_profile=stats,python=platform.python_version(),machine=platform.machine(),os=platform.platform(),CPU_seconds=resource.getrusage(resource.RUSAGE_SELF).ru_utime+resource.getrusage(resource.RUSAGE_SELF).ru_stime,
                 source_hashes={str(p):digest(p) for p in Path('extensions').glob('*.py')})
    for model in ['N','F']:
        usable=[r['models'][model] for r in reports if r['status']=='exact']
        certified=[r for r in usable if r['strict_priority_certified']]
        summary['models'][model]=dict(certified=len(certified),uncertified=len(usable)-len(certified),
            reversal_radius_distribution=dict(Counter('none' if r['reversal_radius'] is None else str(r['reversal_radius']) for r in certified)),
            tie_radius_distribution=dict(Counter('none' if r['tie_radius'] is None else str(r['tie_radius']) for r in certified)))
    (out/'profiles.json').write_text(json.dumps(profiles,indent=2))
    (out/'config.json').write_text(json.dumps(config,indent=2))
    (out/'summary.json').write_text(json.dumps(summary,indent=2));print(json.dumps(summary,indent=2))


if __name__=='__main__':main()
