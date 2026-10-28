"""Exact development audit under a declared code-order heuristic.

Enumerate resource-distinct orders, not probabilities. The heuristic follows
subprocess and three-digit ordinal, leaving all suffix variants unordered.
This is an assumption sensitivity check, never a claim about true chronology.
"""
import argparse
import csv
import hashlib
import itertools
import json
import math
import re
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from .core import score_bounds, screen_top_k, top_k_profile


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--input', required=True)
    parser.add_argument('--out', required=True)
    args = parser.parse_args()
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=False)
    groups = defaultdict(lambda: defaultdict(list))
    with open(args.input) as stream:
        for row in csv.DictReader(stream):
            match = re.fullmatch(r'(.+?)_(\d{3})(.*)', row['activity'])
            assert match
            stamp = datetime.fromisoformat(row['timestamp'])
            assert stamp.tzinfo is not None
            key = stamp.astimezone(timezone.utc), match.group(1), int(match.group(2))
            groups[row['case_id']][key].append(row['resource'])
    e, f = ('R0015', 'R0006'), ('R0006', 'R0017')
    lower, upper, base = Counter(), Counter(), Counter()
    joint_low = joint_high = enumerations = max_orders = 0
    def count(sequence):
        return Counter((a, b) for a, b in zip(sequence, sequence[1:]) if a != b)
    for case_groups in groups.values():
        blocks = [case_groups[key] for key in sorted(case_groups)]
        ways = 1
        for block in blocks:
            multiplicities = Counter(block)
            ways *= math.factorial(len(block)) // math.prod(math.factorial(n) for n in multiplicities.values())
        if ways > 100000:
            raise ValueError('Predeclared exhaustive-case budget exceeded; do not silently truncate')
        choices = [sorted(set(itertools.permutations(block))) if len(set(block)) > 1
                   else [tuple(block)] for block in blocks]
        variants = [count([r for block in variant for r in block])
                    for variant in itertools.product(*choices)]
        assert len(variants) == ways
        enumerations += ways
        max_orders = max(max_orders, ways)
        possible = set().union(*(set(v) for v in variants))
        for edge in possible:
            lower[edge] += min(v[edge] for v in variants)
            upper[edge] += max(v[edge] for v in variants)
        differences = [v[e]-v[f] for v in variants]
        exact = min(differences), max(differences)
        assert score_bounds(blocks, {e: 1, f: -1}, max_block=5) == exact
        joint_low += exact[0]
        joint_high += exact[1]
        base.update(count([resource for block in blocks for resource in block]))
    intervals = {edge: (lower[edge], upper[edge]) for edge in sorted(upper)}
    rows = []
    for edge, (low, high) in intervals.items():
        rows.append({'source':edge[0], 'target':edge[1], 'exact_low':low, 'exact_high':high,
                     'code_source_count':base[edge]})
    with (out/'edges.csv').open('x', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    result = {'scope':'fixed 200-case development cohort; code-order assumption only',
              'assumption':'timestamp, subprocess, numeric three-digit ordinal; suffix variants free',
              'cases':len(groups), 'resource_distinct_case_orders_enumerated':enumerations,
              'max_orders_per_case':max_orders, 'candidate_edges':len(intervals),
              'point_intervals':sum(low==high for low, high in intervals.values()),
              'illustrative_pair_joint_exact_interval':[joint_low, joint_high],
              'pair_order':'R0015->R0006 minus R0006->R0017',
              'dp_independently_checked_against_enumeration':True,
              'top_k':{str(k):{'screen_counts':dict(Counter(screen_top_k(intervals,k).values())),
                               'code_source_profile':top_k_profile(base,k)} for k in [5,10]},
              'input_sha256':hashlib.sha256(Path(args.input).read_bytes()).hexdigest(),
              'code_sha256':{str(path):hashlib.sha256(path.read_bytes()).hexdigest()
                             for path in [Path(__file__),Path(__file__).with_name('core.py')]}}
    (out/'summary.json').write_text(json.dumps(result,indent=2))
    print(json.dumps({key:value for key,value in result.items() if key!='top_k'},indent=2))


if __name__ == '__main__':
    main()
