"""Independent order replay and per-case exhaustive checks for v6 artifacts.

Does not import the new optimizer or its radius function. Uses the frozen
independent multiset-enumeration routine for all raw-resource cases within cap.
"""
import argparse
import csv
import itertools
import json
import math
import re
import gzip
import hashlib
import datetime
import calendar
import time
import xml.etree.ElementTree as ET
from collections import Counter,defaultdict
from pathlib import Path
from src.verify_study import unique_orders


def blocks(events,policy):
    timestamps=defaultdict(list)
    for event in events:timestamps[event['_utc']].append(event)
    result=[]
    for stamp in sorted(timestamps):
        same=timestamps[stamp]
        if policy=='T' or len(same)==1:result.append(same);continue
        grouped=defaultdict(list)
        for event in same:
            if policy=='N':
                parsed=re.fullmatch(r'(.+?)_(\d{3})(.*)',event['code']);assert parsed
                key=parsed[1],int(parsed[2])
            else:key=(event['code'],)
            grouped[key].append(event)
        result.extend(grouped[key] for key in sorted(grouped))
    return result


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--run',required=True);parser.add_argument('--out',required=True)
    parser.add_argument('--raw',required=True);parser.add_argument('--raw-sha256',required=True);args=parser.parse_args()
    started=time.perf_counter()
    run=Path(args.run);config=json.loads((run/'config.json').read_text());reports=json.loads((run/'queries.json').read_text());private=json.loads((run/'case-bounds-private.json').read_text())
    cases=defaultdict(list)
    for row in csv.DictReader(Path(config['cohort']).open()):
        row['source_index']=int(row['source_index']);stamp=datetime.datetime.fromisoformat(row['timestamp'].replace('Z','+00:00')).astimezone(datetime.timezone.utc);row['_utc']=calendar.timegm(stamp.utctimetuple())*1000000+stamp.microsecond;cases[row['case_id']].append(row)
    assert hashlib.sha256(Path(args.raw).read_bytes()).hexdigest()==args.raw_sha256
    rawroot=ET.parse(gzip.open(args.raw)).getroot()
    attrs=lambda element:{x.get('key'):x.get('value') for x in element if x.get('key')}
    rawcases={};all_resources=set()
    for trace in rawroot:
        if not trace.tag.endswith('trace'):continue
        case=attrs(trace)['concept:name'];events=[attrs(e) for e in trace if e.tag.endswith('event')]
        assert all(e['lifecycle:transition'].lower()=='complete' and e.get('org:resource') for e in events)
        rawcases[case]=events;all_resources.update(e['org:resource'] for e in events)
    aliases={r:'R%04d'%i for i,r in enumerate(sorted(all_resources),1)}
    matched=0
    for case,events in cases.items():
        assert len(events)==len(rawcases[case])
        for event in events:
            raw=rawcases[case][event['source_index']]
            assert event['resource']==aliases[raw['org:resource']]
            assert event['timestamp']==raw['time:timestamp'] and event['code']==raw.get('action_code','')
            assert event['activity']==raw['concept:name'];matched+=1
    ids=list(cases);pairs=[(tuple(r['edge_e']),tuple(r['edge_f'])) for r in reports]
    coverage={};checks=0
    all_blocks={}
    for model in ['T','N','F']:
        count=orders=0;all_blocks[model]={}
        for i,case in enumerate(ids):
            grouped=blocks(cases[case],model);all_blocks[model][case]=grouped
            resources=[[r['resource'] for r in b] for b in grouped]
            possibilities=1
            for b in resources:
                multiplicities=Counter(b)
                possibilities*=math.factorial(len(b))//math.prod(math.factorial(n) for n in multiplicities.values())
            if possibilities>10000:continue
            lower=[math.inf]*len(pairs);upper=[-math.inf]*len(pairs)
            for choice in itertools.product(*(unique_orders(b) for b in resources)):
                sequence=list(itertools.chain.from_iterable(choice));weights=Counter(zip(sequence,sequence[1:]))
                for query,(e,f) in enumerate(pairs):
                    value=weights[e]-weights[f]
                    lower[query]=min(lower[query],value);upper[query]=max(upper[query],value)
            for query in range(len(pairs)):
                assert private[query]['case_ids']==ids
                assert private[query]['bounds'][model][i]==[lower[query],upper[query]],(model,i,query)
                checks+=1
            count+=1;orders+=possibilities
        coverage[model]=dict(cases_enumerated=count,summed_case_sequences=orders,all_queries_checked=True)
    # Every complete baseline and negative order is checked against the model's
    # ordered blocks, independently reconstructed from timestamp/code strings.
    totals=defaultdict(lambda:[0,0,0,set()])
    by_index={case:{r['source_index']:r['resource'] for r in events} for case,events in cases.items()}
    seen=defaultdict(set)
    for line in (run/'witnesses-private.jsonl').open():
        record=json.loads(line);qid=record['query'];model=record['base_model'];case=record['case_id'];key=qid,model
        if not record['relaxed']:assert record['baseline']==record['negative']
        assert case not in seen[key];seen[key].add(case)
        e,f=pairs[qid-1];expected_indices=set(by_index[case])
        for column,policy,total_index in [('baseline',model,0),('negative','T' if record['relaxed'] else model,1)]:
            sequence=record[column];assert len(sequence)==len(expected_indices) and set(sequence)==expected_indices
            order_blocks=all_blocks[policy][case]
            ordinal={row['source_index']:j for j,b in enumerate(order_blocks) for row in b}
            assert all(ordinal[a]<=ordinal[b] for a,b in zip(sequence,sequence[1:])),(qid,model,case,column)
            resources=[by_index[case][i] for i in sequence];weights=Counter(zip(resources,resources[1:]))
            totals[key][total_index]+=weights[e]-weights[f]
        if record['relaxed']:totals[key][2]+=1;totals[key][3].add(record['case_alias'])
    witnessed=[]
    for (qid,model),(baseline,negative,n,aliases) in totals.items():
        expected=reports[qid-1]['models'][model]
        assert baseline==expected['range'][0]
        assert len(seen[qid,model])==len(ids) and baseline>0>negative
        assert negative==expected['reversal_witness_margin'] and n==expected['reversal_radius']
        assert aliases==set(expected['selected_case_aliases'])
        lows=[p[0] for p in private[qid-1]['bounds'][model]];t=[p[0] for p in private[qid-1]['bounds']['T']]
        losses=sorted((a-b for a,b in zip(lows,t)),reverse=True)
        assert sum(lows)-sum(losses[:n-1])>=0 # no subset with fewer cases can reverse
        assert sum(lows)-sum(losses[:n])==negative
        witnessed.append(dict(query=qid,base_model=model,relaxed_cases=n,baseline_margin=baseline,witness_margin=negative,minimality_prefix_checked=True))
    source_counts=Counter();candidate_set=set()
    for case in ids:
        grouped=all_blocks['N'][case];previous=None
        sequence=[e['resource'] for b in grouped for e in b]
        source_counts.update((a,b) for a,b in zip(sequence,sequence[1:]) if a!=b)
        for block in grouped:
            labels=set(e['resource'] for e in block)
            candidate_set.update((a,b) for a in labels for b in labels if a!=b)
            if previous is not None:candidate_set.update((a,b) for a in previous for b in labels if a!=b)
            previous=labels
    cutoff=sorted((source_counts[e] for e in candidate_set),reverse=True)[9]
    important={e for e in candidate_set if source_counts[e]>=cutoff}
    expected_pairs=set()
    for a,b in itertools.combinations(sorted(important),2):
        if source_counts[a]!=source_counts[b]:expected_pairs.add((a,b) if source_counts[a]>source_counts[b] else (b,a))
    assert set(pairs)==expected_pairs
    summary=json.loads((run/'summary.json').read_text())
    assert len(witnessed)==summary['strict_reversal_witness_queries']
    result=dict(status='passed',case_bound_comparisons=checks,enumeration_coverage=coverage,
                unrelaxed_case_orders_identical=True,raw_events_matched=matched,raw_cases=len(rawcases),cohort_cases=len(cases),seconds=time.perf_counter()-started,
                complete_mixed_model_witnesses=witnessed,
                limitations='Enumeration coverage is reported per model; unenumerated case extrema rely on multiplicity DP correctness and small-instance tests. All full-log witnesses replayed; minimality uses exact case bounds.')
    with Path(args.out).open('x') as stream:json.dump(result,stream,indent=2)
    print(json.dumps({k:v for k,v in result.items() if k!='complete_mixed_model_witnesses'},indent=2))


if __name__=='__main__':main()
