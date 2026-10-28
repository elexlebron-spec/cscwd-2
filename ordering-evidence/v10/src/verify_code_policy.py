"""Independent raw-XML validation of the fixed development code-policy audit.

No imports from core, io, semantic_audit, or code_policy_audit. Enumerates all
resource-distinct resolutions per case for both declared code keys.
"""
import argparse
import csv
import gzip
import itertools
import json
import math
import xml.etree.ElementTree as ET
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--raw', required=True)
    parser.add_argument('--cohort', required=True)
    parser.add_argument('--expected', required=True)
    parser.add_argument('--out', required=True)
    args = parser.parse_args()
    target = Path(args.out)
    if target.exists():
        raise FileExistsError(target)
    cohort = defaultdict(dict)
    with open(args.cohort) as stream:
        for row in csv.DictReader(stream):
            cohort[row['case_id']][int(row['source_index'])] = row
    with open(args.expected) as stream:
        expected = {(r['source'], r['target']): (int(r['exact_low']), int(r['exact_high']))
                    for r in csv.DictReader(stream)}
    with gzip.open(args.raw) as stream:
        root = ET.parse(stream).getroot()
    lo, hi = Counter(), Counter()
    forward, backward = {}, {}
    total_events = cases = combinations = full_mixed = 0
    delta_lo = delta_hi = 0
    pair = ('R0015', 'R0006'), ('R0006', 'R0017')
    for trace in root:
        if trace.tag.rsplit('}', 1)[-1] != 'trace':
            continue
        case = next(x.get('value') for x in trace if x.get('key') == 'concept:name')
        if case not in cohort:
            continue
        cases += 1
        numeric, full = defaultdict(list), defaultdict(list)
        n = 0
        for i, element in enumerate(x for x in trace if x.tag.rsplit('}', 1)[-1] == 'event'):
            row = {x.get('key'): x.get('value') for x in element}
            derived = cohort[case][i]
            assert derived['activity'] == row['action_code'] == row['concept:name']
            assert derived['timestamp'] == row['time:timestamp']
            raw, alias = row['org:resource'], derived['resource']
            assert forward.setdefault(raw, alias) == alias
            assert backward.setdefault(alias, raw) == raw
            stamp = datetime.fromisoformat(row['time:timestamp']).astimezone(timezone.utc)
            parts = row['action_code'].split('_')
            ordinal = next(j for j, part in enumerate(parts) if len(part) >= 3 and part[:3].isdigit())
            key = stamp, '_'.join(parts[:ordinal]), int(parts[ordinal][:3])
            numeric[key].append(alias)
            full[stamp, row['action_code']].append(alias)
            n += 1
        assert n == len(cohort[case])
        total_events += n
        full_mixed += sum(len(set(block)) > 1 for block in full.values())
        blocks = [numeric[key] for key in sorted(numeric)]
        ways = math.prod(math.factorial(len(b)) // math.prod(math.factorial(v) for v in Counter(b).values())
                         for b in blocks)
        assert ways <= 100000
        options = [set(itertools.permutations(b)) if len(set(b)) > 1 else [tuple(b)] for b in blocks]
        variants = []
        for choice in itertools.product(*options):
            sequence = list(itertools.chain.from_iterable(choice))
            assert len(sequence) == n
            variants.append(Counter((a, b) for a, b in zip(sequence, sequence[1:]) if a != b))
        assert len(variants) == ways
        combinations += ways
        for edge in set().union(*(set(v) for v in variants)):
            lo[edge] += min(v[edge] for v in variants)
            hi[edge] += max(v[edge] for v in variants)
        differences = [v[pair[0]]-v[pair[1]] for v in variants]
        delta_lo += min(differences)
        delta_hi += max(differences)
    assert {edge: (lo[edge], hi[edge]) for edge in hi} == expected
    assert full_mixed == 0
    assert (cases, total_events, combinations, delta_lo, delta_hi) == (200, 8895, 238, -7, -6)
    result = {'status': 'passed', 'independent_raw_xml_and_alternative_code_parser': True,
              'cases': cases, 'events': total_events, 'case_orders_enumerated': combinations,
              'numeric_all_candidate_intervals_matched': len(expected),
              'numeric_joint_difference': [delta_lo, delta_hi], 'full_code_mixed_blocks': full_mixed,
              'ground_truth_order_claim': False}
    with target.open('x') as stream:
        json.dump(result, stream, indent=2)
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
