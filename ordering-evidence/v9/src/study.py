"""Descriptive held-out study; all ordering policies are declared assumptions."""
import argparse
import csv
import hashlib
import json
import platform
import random
import time
from collections import Counter
from itertools import combinations
from pathlib import Path
from .core import counts, expected_counts, cheap_edge_bounds, score_bounds, screen_top_k, top_k_profile
from .io import sha256
from .study_data import make_blocks, select_cohort, write_cohort


def family(profile):
    strict = frozenset(map(tuple, profile['strict']))
    boundary = frozenset(map(tuple, profile['boundary']))
    return (strict | boundary, frozenset(), 0) if profile['unique'] else (strict, boundary, profile['slots'])


def order_events(blocks, mode, seed=0):
    rng = random.Random(seed)
    sequence = []
    for block in blocks:
        ordered = list(block)
        if mode == 'lex':
            ordered.sort(key=lambda event: event['resource'])
        elif mode == 'reverse':
            ordered.sort(key=lambda event: event['resource'], reverse=True)
        elif mode == 'random':
            rng.shuffle(ordered)
        elif mode != 'source':
            raise ValueError(mode)
        sequence.extend(ordered)
    return sequence


def audit_policy(cases, policy, settings, out):
    started = time.perf_counter()
    out.mkdir(exist_ok=False)
    blocks = {case:make_blocks(events, policy) for case, events in cases.items()}
    resources = {case:[[event['resource'] for event in b] for b in trace] for case, trace in blocks.items()}
    counters = {mode:Counter() for mode in ['source','lex','reverse']}
    expected, cheap_total_low, cheap_total_high = Counter(), Counter(), Counter()
    cheap_cases = {}
    with (out/'orders.jsonl').open('x') as stream:
        for case, trace in blocks.items():
            orders = {}
            for mode in counters:
                sequence = order_events(trace, mode)
                counters[mode].update(counts([event['resource'] for event in sequence]))
                orders[mode] = [event['source_index'] for event in sequence]
            stream.write(json.dumps({'case_id':case, 'orders':orders})+'\n')
            expected.update(expected_counts(resources[case]))
            cheap = cheap_edge_bounds(resources[case])
            cheap_cases[case] = cheap
            cheap_total_low.update({edge:bound[0] for edge,bound in cheap.items()})
            cheap_total_high.update({edge:bound[1] for edge,bound in cheap.items()})
    edges = sorted(expected, key=lambda edge:(-expected[edge],edge))
    assert set(edges) == set(cheap_total_high)
    intervals = {edge:(cheap_total_low[edge],cheap_total_high[edge]) for edge in edges}
    screening = {k:screen_top_k(intervals,k) for k in settings['top_k']}
    refine = [edge for edge in edges if intervals[edge][0] < intervals[edge][1] and
              any(screening[k][edge]=='unknown' for k in settings['top_k'])][:settings['exact_edges']]
    exact_cases = {}
    for edge in refine:
        lo = hi = covered = 0
        for case, trace in resources.items():
            cheap = cheap_cases[case].get(edge,(0,0))
            bound = cheap if cheap[0] == cheap[1] else score_bounds(trace,{edge:1},settings['max_block'])
            covered += bound is not None
            pair = cheap if bound is None else bound
            lo += pair[0]; hi += pair[1]
        intervals[edge] = lo,hi
        exact_cases[edge] = covered
    certs = {k:screen_top_k(intervals,k) for k in settings['top_k']}
    profiles = {str(k):{mode:top_k_profile({edge:value[edge] for edge in edges},k)
                       for mode,value in dict(counters, expected_weight=expected).items()}
                for k in settings['top_k']}
    mc = {str(k):{'different_top_k_families':0,'unique_samples':0} for k in settings['top_k']}
    mc_mean = Counter()
    with (out/'mc.jsonl').open('x') as stream:
        for rep in range(settings['permutations']):
            sampled = Counter()
            for case, trace in blocks.items():
                digest = hashlib.sha256(('%s/%s/%s' % (settings['seed'],rep,case)).encode()).digest()
                sequence = order_events(trace,'random',int.from_bytes(digest[:8],'big'))
                sampled.update(counts([event['resource'] for event in sequence]))
            mc_mean.update(sampled)
            result = {}
            for k in settings['top_k']:
                key = str(k)
                profile = top_k_profile({edge:sampled[edge] for edge in edges},k)
                different = family(profile) != family(profiles[key]['source'])
                mc[key]['different_top_k_families'] += different
                mc[key]['unique_samples'] += profile['unique']
                result[key] = {'profile':profile,'top_k_family_differs_from_model_source':different}
            stream.write(json.dumps({'replicate':rep,'top_k':result})+'\n')
    reversals = []
    denominators = {}
    for k in settings['top_k']:
        profile = profiles[str(k)]['source']
        important = set(map(tuple,profile['strict']+profile['boundary']))
        comparisons = 0
        for first,second in combinations(sorted(important),2):
            if counters['source'][first] == counters['source'][second]:
                continue
            e,f = (first,second) if counters['source'][first] > counters['source'][second] else (second,first)
            comparisons += 1
            for mode in ['lex','reverse']:
                if counters[mode][e] < counters[mode][f]:
                    reversals.append({'k':k,'higher_source_edge':e,'lower_source_edge':f,
                                      'mode':mode,'source_difference':counters['source'][e]-counters['source'][f],
                                      'witness_difference':counters[mode][e]-counters[mode][f]})
                    break
        denominators[str(k)] = comparisons
    e,f = ('R0015','R0006'),('R0006','R0017')
    selected_pair = None
    if policy in ['N','F']:
        lo = hi = covered = 0
        for case,trace in resources.items():
            bound = score_bounds(trace,{e:1,f:-1},settings['max_block'])
            covered += bound is not None
            if bound is None:
                ec,fc = cheap_cases[case].get(e,(0,0)),cheap_cases[case].get(f,(0,0))
                bound = ec[0]-fc[1],ec[1]-fc[0]
            lo += bound[0]; hi += bound[1]
        selected_pair = {'edge_e':e,'edge_f':f,'low':lo,'high':hi,'exact_cases':covered,
                         'total_cases':len(cases),'selection':'fixed from development; illustrative only'}
    denominator = sum(max(len(events)-1,0) for events in cases.values())
    report = {'policy':policy, 'cases':len(cases),'events':sum(map(len,cases.values())),
              'tied_events':sum(len(b) for trace in blocks.values() for b in trace if len(b)>1),
              'mixed_tied_events':sum(len(b) for trace in resources.values() for b in trace if len(set(b))>1),
              'mixed_cases':sum(any(len(set(b))>1 for b in trace) for trace in resources.values()),
              'max_mixed_block':max((len(b) for trace in resources.values() for b in trace if len(set(b))>1),default=0),
              'candidate_edges':len(edges),'point_safe_intervals':sum(lo==hi for lo,hi in intervals.values()),
              'refined_edges':len(refine),'refinement_exact_case_counts':[exact_cases[edge] for edge in refine],
              'certificates':{str(k):dict(Counter(certs[k].values())) for k in settings['top_k']},
              'fixed_adjacent_position_denominator':denominator,
              'source_expected_l1_per_position':float(sum(abs(counters['source'][edge]-expected[edge]) for edge in edges)/denominator) if denominator else 0,
              'mc_mean_expected_l1_per_position':float(sum(abs(mc_mean[edge]/settings['permutations']-float(expected[edge])) for edge in edges)/denominator) if denominator else 0,
              'mc':mc,'strict_pair_comparisons_in_source_cutoff_union':denominators,
              'strict_reversal_pairs_found':{str(k):sum(row['k']==k for row in reversals) for k in settings['top_k']},
              'fixed_development_pair':selected_pair,'seconds':time.perf_counter()-started,
              'interpretation':'descriptive sensitivity to declared ordering assumptions; no ground truth claim'}
    with (out/'edges.csv').open('x',newline='') as stream:
        writer = csv.writer(stream)
        writer.writerow(['u','v','model_source','lex','reverse','expected_num','expected_den','safe_low','safe_high','refined_exact_cases','cert5','cert10'])
        for edge in edges:
            writer.writerow([*edge,*(counters[mode][edge] for mode in ['source','lex','reverse']),
                             expected[edge].numerator,expected[edge].denominator,*intervals[edge],
                             exact_cases.get(edge,''),certs[5][edge],certs[10][edge]])
    for name,obj in [('summary.json',report),('profiles.json',profiles),('reversals.json',reversals)]:
        (out/name).write_text(json.dumps(obj,indent=2))
    return report


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--config',required=True)
    parser.add_argument('--phase',choices=['dev','test'],required=True)
    parser.add_argument('--dataset',required=True)
    parser.add_argument('--out',required=True)
    args = parser.parse_args()
    config = json.loads(Path(args.config).read_text())
    if args.phase == 'test':
        assert config['frozen'], 'Freeze before looking at reserved outcomes'
        for name,digest in config['frozen_hashes'].items():
            if sha256(name) != digest:
                raise ValueError('Frozen file changed: '+name)
    dataset = config['datasets'][args.dataset]
    out = Path(args.out); out.mkdir(parents=True,exist_ok=False)
    started = time.perf_counter()
    cases = select_cohort(dataset,args.phase)
    write_cohort(cases,out/'cohort.csv')
    reports = {}
    for policy in dataset['policies']:
        reports[policy] = audit_policy(cases,policy,config['settings'],out/policy)
    manifest = {'phase':args.phase,'dataset':args.dataset,'config':args.config,
                'config_sha256':sha256(args.config),'raw_sha256':sha256(dataset['raw']),
                'split_sha256':sha256(dataset['split']),'cohort_sha256':sha256(out/'cohort.csv'),
                'python':platform.python_version(),'seconds':time.perf_counter()-started,
                'selected_ids':list(cases),'source_hashes':{str(p):sha256(p) for p in sorted(Path('src').glob('*.py'))}}
    (out/'manifest.json').write_text(json.dumps(manifest,indent=2))
    print(json.dumps({policy:{key:report[key] for key in ['cases','events','mixed_cases','candidate_edges','certificates','strict_reversal_pairs_found','seconds']} for policy,report in reports.items()},indent=2))


if __name__ == '__main__':
    main()
