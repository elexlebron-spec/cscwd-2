"""Run a pilot, with input and source hashes. Does NOT execute formal study."""
import argparse
import csv
import hashlib
import json
import platform
import time
from collections import Counter
from pathlib import Path
from .core import (blocks_from_events, counts, expected_counts, linearize, score_bounds,
                   cheap_edge_bounds, top_k_profile, screen_top_k)
from .io import load_csv, sha256


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--input', required=True)
    p.add_argument('--out', required=True)
    p.add_argument('--permutations', type=int, default=100)
    p.add_argument('--seed', type=int, default=20261027)
    p.add_argument('--top-k', type=int, default=5)
    p.add_argument('--max-block', type=int, default=10)
    p.add_argument('--exact-top', type=int, default=5, help='refinement budget among unscreened edges; NOT a global top-k guarantee')
    a = p.parse_args()
    if min(a.permutations, a.top_k, a.max_block, a.exact_top) < 1 or a.max_block > 14:
        p.error('Positive sizes required; max-block capped at 14')
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=False)
    started = time.perf_counter()
    cases, rejected = load_csv(a.input)
    if not cases:
        raise ValueError('No eligible cases')
    traces = {c: blocks_from_events(e) for c, e in sorted(cases.items())}
    expected, source, lex, reverse = Counter(), Counter(), Counter(), Counter()
    for b in traces.values():
        expected.update(expected_counts(b))
        source.update(counts(linearize(b)))
        lex.update(counts(linearize(b, 'lex')))
        reverse.update(counts(linearize(b, 'reverse')))
    edges = sorted(expected, key=lambda e: (-expected[e], e))
    cheap = [cheap_edge_bounds(b) for b in traces.values()]
    intervals = {e: (sum(c.get(e, (0, 0))[0] for c in cheap),
                     sum(c.get(e, (0, 0))[1] for c in cheap)) for e in edges}
    screened = screen_top_k(intervals, a.top_k)
    exact = {}
    refine = [e for e in edges if screened[e] == 'unknown'][:a.exact_top]
    for edge in refine:
        pairs = [score_bounds(b, {edge: 1}, a.max_block) for b in traces.values()]
        ok = [v for v in pairs if v is not None]
        exact[edge] = (sum(v[0] for v in ok), sum(v[1] for v in ok), len(ok))
        covered = [v if v is not None else c.get(edge, (0, 0)) for v, c in zip(pairs, cheap)]
        intervals[edge] = (sum(v[0] for v in covered), sum(v[1] for v in covered))
    certificates = screen_top_k(intervals, a.top_k)
    profiles = {name: top_k_profile({e: counter[e] for e in edges}, a.top_k)
                for name, counter in [('source', source), ('lex', lex), ('reverse', reverse),
                                      ('expected_edge_weight', expected)]}
    (out / 'top_k_profiles.json').write_text(json.dumps(profiles, indent=2), encoding='utf-8')
    def top(counter):
        return set(sorted(edges, key=lambda e: (-counter[e], e))[:a.top_k])
    source_top = top(source)
    overlaps = []
    with open(out / 'permutations.jsonl', 'x') as f:
        for rep in range(a.permutations):
            sample = Counter()
            for case, b in traces.items():
                digest = hashlib.sha256(('%s/%s/%s' % (a.seed, rep, case)).encode()).digest()
                sample.update(counts(linearize(b, 'random', int.from_bytes(digest[:8], 'big'))))
            selected = top(sample)
            union = source_top | selected
            j = len(source_top & selected) / len(union) if union else None
            overlaps.append(j)
            f.write(json.dumps({'replicate': rep, 'diagnostic_id_tiebroken_jaccard_vs_source': j,
                                'diagnostic_id_tiebroken_top_edges': sorted(selected),
                                'tie_aware_profile': top_k_profile({e: sample[e] for e in edges}, a.top_k)}) + '\n')
    with open(out / 'edges.csv', 'x', newline='') as f:
        w = csv.writer(f)
        w.writerow(['source_resource', 'target_resource', 'source_order_count', 'lex_count', 'reverse_count',
                    'uniform_expectation', 'expected_numerator', 'expected_denominator',
                    'exact_low_covered_cases', 'exact_high_covered_cases', 'exact_case_count', 'total_case_count',
                    'full_log_safe_low', 'full_log_safe_high', 'top_k_certificate', 'refined'])
        for edge in edges:
            bounds = exact.get(edge, ('', '', ''))
            w.writerow([*edge, source[edge], lex[edge], reverse[edge], float(expected[edge]),
                        expected[edge].numerator, expected[edge].denominator, *bounds, len(traces),
                        *intervals[edge], certificates[edge], edge in exact])
    with open(out / 'cases.jsonl', 'x') as f:
        for case, b in traces.items():
            f.write(json.dumps({'case_id': case, 'events': sum(map(len, b)), 'blocks': len(b),
                                'tied_events': sum(len(x) for x in b if len(x) > 1),
                                'mixed_tied_events': sum(len(x) for x in b if len(set(x)) > 1),
                                'max_block': max(map(len, b))}) + '\n')
    valid_j = [x for x in overlaps if x is not None]
    report = {'status': 'pilot_not_formal_study', 'cases': len(cases),
              'events': sum(len(v) for v in cases.values()), 'candidate_edges': len(edges),
              'diagnostic_id_tiebroken_jaccard_mean': sum(valid_j)/len(valid_j) if valid_j else None,
              'ranking_ties': 'strict and boundary sets in profiles; ID-based Jaccard is diagnostic only',
              'expectation_interpretation': 'ranking expected edge weights is NOT expected rank or modal top-k',
              'top_k_certificates': dict(Counter(certificates.values())),
              'refined_edges': len(refine),
              'full_log_safe_bounds': 'all cases included; conservative where unrefined or exact computation unavailable',
              'exact_bounds_scope': 'covered cases only; never full-log bounds unless count equals total',
              'rejections': rejected, 'seconds': time.perf_counter()-started}
    manifest = {'arguments': vars(a), 'input_sha256': sha256(a.input), 'python': platform.python_version(),
                'source_hashes': {str(p): sha256(p) for p in sorted(Path('src').glob('*.py'))}}
    for name, obj in [('summary.json', report), ('manifest.json', manifest)]:
        (out / name).write_text(json.dumps(obj, indent=2), encoding='utf-8')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
