"""Independent raw-XML/cohort/order replay, with bounded exhaustive checks.

Does not import study, study_data, core, or io. Certificate algorithms are also
tested against exhaustive toy worlds in tests/test_core.py.
"""
import argparse
import csv
import gzip
import hashlib
import itertools
import json
import math
import xml.etree.ElementTree as ET
from collections import Counter, defaultdict
from datetime import datetime, timezone
from fractions import Fraction
from pathlib import Path


def unique_orders(block):
    """Enumerate a multiset directly; do not generate n! duplicate event orders."""
    remaining = Counter(block)
    labels = sorted(remaining)
    prefix = []
    def visit():
        if len(prefix) == len(block):
            yield tuple(prefix)
            return
        for label in labels:
            if remaining[label]:
                remaining[label] -= 1
                prefix.append(label)
                yield from visit()
                prefix.pop()
                remaining[label] += 1
    return list(visit())


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--run',required=True)
    parser.add_argument('--config',required=True)
    parser.add_argument('--out',required=True)
    args = parser.parse_args()
    out = Path(args.out)
    if out.exists():
        raise FileExistsError(out)
    run = Path(args.run)
    manifest = json.loads((run/'manifest.json').read_text())
    config = json.loads(Path(args.config).read_text())
    digest = lambda path: hashlib.sha256(Path(path).read_bytes()).hexdigest()
    assert digest(args.config) == manifest['config_sha256']
    assert digest(run/'cohort.csv') == manifest['cohort_sha256']
    for name,value in manifest['source_hashes'].items():
        assert digest(name) == value, name
    dataset = config['datasets'][manifest['dataset']]
    assert digest(dataset['raw']) == manifest['raw_sha256'] == dataset['sha256']
    assert digest(dataset['split']) == manifest['split_sha256']
    split = json.loads(Path(dataset['split']).read_text())
    selected = split['dev' if manifest['phase']=='dev' else 'reserved_test']
    assert selected == manifest['selected_ids']
    assert set(split['dev']).isdisjoint(split['reserved_test'])
    cases = defaultdict(dict)
    with (run/'cohort.csv').open() as stream:
        for row in csv.DictReader(stream):
            index = int(row['source_index'])
            assert index not in cases[row['case_id']]
            cases[row['case_id']][index] = row
    assert set(cases) == set(selected)
    with gzip.open(dataset['raw']) as stream:
        root = ET.parse(stream).getroot()
    forward,backward = {},{}
    original_events = 0
    for trace in root:
        if trace.tag.rsplit('}',1)[-1] != 'trace':
            continue
        case = next(x.get('value') for x in trace if x.get('key')=='concept:name')
        if case not in cases:
            continue
        retained = []
        for index,event in enumerate(x for x in trace if x.tag.rsplit('}',1)[-1]=='event'):
            raw = {x.get('key'):x.get('value') for x in event}
            if dataset['lifecycle'] != 'all' and raw.get('lifecycle:transition','').lower()!=dataset['lifecycle']:
                continue
            row = cases[case][index]
            assert row['timestamp']==raw['time:timestamp'] and row['activity']==raw['concept:name']
            assert row['code']==raw.get('action_code','') and row['lifecycle']==raw.get('lifecycle:transition','')
            assert forward.setdefault(raw['org:resource'],row['resource'])==row['resource']
            assert backward.setdefault(row['resource'],raw['org:resource'])==raw['org:resource']
            retained.append(index)
        assert retained == list(cases[case])
        original_events += len(retained)
    time_counts = {case:Counter(datetime.fromisoformat(row['timestamp'].replace('Z','+00:00')).astimezone(timezone.utc)
                               for row in events.values()) for case,events in cases.items()}
    def key(row,policy):
        dt = datetime.fromisoformat(row['timestamp'].replace('Z','+00:00'))
        assert dt.tzinfo is not None
        stamp = dt.astimezone(timezone.utc)
        if policy=='T':
            return (stamp,)
        if policy=='F':
            return stamp,row['code']
        if time_counts[row['case_id']][stamp]==1:
            return stamp,'',-1
        parts = row['code'].split('_')
        ordinal = next(i for i,part in enumerate(parts) if len(part)>=3 and part[:3].isdigit())
        return stamp,'_'.join(parts[:ordinal]),int(parts[ordinal][:3])
    def count(sequence):
        return Counter((a,b) for a,b in zip(sequence,sequence[1:]) if a!=b)
    reports = {}
    for policy in dataset['policies']:
        folder = run/policy
        vectors = {mode:Counter() for mode in ['source','lex','reverse']}
        seen = set()
        for line in (folder/'orders.jsonl').read_text().splitlines():
            record = json.loads(line);case=record['case_id']
            assert case not in seen;seen.add(case)
            for mode,indices in record['orders'].items():
                assert len(indices)==len(set(indices))==len(cases[case])
                assert set(indices)==set(cases[case])
                rows = [cases[case][i] for i in indices]
                keys = [key(row,policy) for row in rows]
                assert keys==sorted(keys)
                for _,group in itertools.groupby(rows,key=lambda row:key(row,policy)):
                    group=list(group)
                    if mode=='source':
                        assert [int(r['source_index']) for r in group]==sorted(int(r['source_index']) for r in group)
                    else:
                        assert [r['resource'] for r in group]==sorted((r['resource'] for r in group),reverse=mode=='reverse')
                vectors[mode].update(count([row['resource'] for row in rows]))
        assert seen==set(cases)
        possible=set();expectation=Counter();exact_low=Counter();exact_high=Counter()
        enumerated_cases=enumerated_orders=0
        tied=mixed=mixed_cases=0
        for events in cases.values():
            ordered=sorted(events.values(),key=lambda row:key(row,policy))
            blocks=[[row['resource'] for row in group] for _,group in itertools.groupby(ordered,key=lambda row:key(row,policy))]
            tied+=sum(len(b) for b in blocks if len(b)>1)
            mixed+=sum(len(b) for b in blocks if len(set(b))>1)
            mixed_cases+=any(len(set(b))>1 for b in blocks)
            previous=None
            for block in blocks:
                c=Counter(block)
                for u in c:
                    for v in c:
                        if u!=v:
                            possible.add((u,v));expectation[u,v]+=Fraction(c[u]*c[v],len(block))
                if previous is not None:
                    for u in previous:
                        for v in c:
                            if u!=v:
                                possible.add((u,v));expectation[u,v]+=Fraction(previous[u]*c[v],sum(previous.values())*len(block))
                previous=c
            ways=math.prod(math.factorial(len(b))//math.prod(math.factorial(n) for n in Counter(b).values()) for b in blocks)
            # Avoid materializing huge permutations of homogeneous blocks.
            if ways<=config.get('verification_max_case_orders',10000):
                choices=[unique_orders(b) if len(set(b))>1 else [tuple(b)] for b in blocks]
                variants=[count(list(itertools.chain.from_iterable(choice))) for choice in itertools.product(*choices)]
                assert len(variants)==ways
                enumerated_cases+=1;enumerated_orders+=ways
                for edge in set().union(*(set(v) for v in variants)):
                    exact_low[edge]+=min(v[edge] for v in variants)
                    exact_high[edge]+=max(v[edge] for v in variants)
        with (folder/'edges.csv').open() as stream:
            rows={(row['u'],row['v']):row for row in csv.DictReader(stream)}
        assert set(rows)==possible==set(expectation)
        for edge,row in rows.items():
            for mode in vectors:
                field='model_source' if mode=='source' else mode
                assert int(row[field])==vectors[mode][edge]
                assert int(row['safe_low'])<=vectors[mode][edge]<=int(row['safe_high'])
            assert Fraction(int(row['expected_num']),int(row['expected_den']))==expectation[edge]
            if enumerated_cases==len(cases):
                assert int(row['safe_low'])<=exact_low[edge]<=exact_high[edge]<=int(row['safe_high'])
        summary=json.loads((folder/'summary.json').read_text())
        assert (tied,mixed,mixed_cases)==(summary['tied_events'],summary['mixed_tied_events'],summary['mixed_cases'])
        for witness in json.loads((folder/'reversals.json').read_text()):
            e,f=tuple(witness['higher_source_edge']),tuple(witness['lower_source_edge'])
            assert vectors['source'][e]-vectors['source'][f]==witness['source_difference']>0
            assert vectors[witness['mode']][e]-vectors[witness['mode']][f]==witness['witness_difference']<0
        reports[policy]={'candidate_edges_checked':len(rows),'all_saved_event_orders_replayed':True,
                         'cases_exhaustively_checked':enumerated_cases,'case_orders_enumerated':enumerated_orders,
                         'global_safe_intervals_independently_checked':enumerated_cases==len(cases)}
    result={'status':'passed','dataset':manifest['dataset'],'phase':manifest['phase'],
            'cases':len(cases),'raw_events_matched':original_events,'policies':reports,
            'scope':'independent parser and order replay; exhaustive global interval checks only where every case is enumerable'}
    with out.open('x') as stream:json.dump(result,stream,indent=2)
    print(json.dumps(result,indent=2))


if __name__=='__main__':
    main()
