import itertools
import random
import tempfile
import unittest
from fractions import Fraction
from pathlib import Path
from src.core import (counts, expected_counts, score_bounds, exhaustive_counts, blocks_from_events,
                      cheap_edge_bounds, top_k_profile, screen_top_k)
from src.io import timestamp_us, load_csv, convert_xes


class AuditTests(unittest.TestCase):
    def test_random_differential(self):
        rng = random.Random(31)
        for _ in range(150):
            b = [[rng.choice('ABC') for _ in range(rng.randint(1, 4))]
                 for _ in range(rng.randint(1, 3))]
            records = list(exhaustive_counts(b))
            expected = expected_counts(b)
            for edge in itertools.permutations('ABC', 2):
                values = [r[edge] for r in records]
                self.assertEqual(expected.get(edge, 0), Fraction(sum(values), len(values)))
                self.assertEqual(score_bounds(b, {edge: 1}), (min(values), max(values)))
            weights = {('A', 'B'): 1, ('B', 'C'): -1}
            margins = [r['A', 'B']-r['B', 'C'] for r in records]
            self.assertEqual(score_bounds(b, weights), (min(margins), max(margins)))

    def test_boundary(self):
        b = [['A'], ['B', 'C'], ['D']]
        self.assertEqual(expected_counts(b)['A', 'B'], Fraction(1, 2))
        self.assertEqual(score_bounds(b, {('A', 'B'): 1}), (0, 1))

    def test_homogeneous(self):
        b = [['A'] * 30, ['B'] * 30]
        self.assertEqual(score_bounds(b, {('A', 'B'): 1}), (1, 1))
        self.assertEqual(expected_counts(b), {('A', 'B'): Fraction(1)})

    def test_unsupported(self):
        self.assertIsNone(score_bounds([list('ABABAB')], {('A', 'B'): 1}, max_block=3))

    def test_empty_and_single(self):
        self.assertEqual(expected_counts([]), {})
        self.assertEqual(score_bounds([], {}), (0, 0))
        self.assertEqual(counts(['A']), {})
        with self.assertRaises(ValueError):
            score_bounds([[]], {})

    def test_input_order_invariance(self):
        self.assertEqual(expected_counts([list('ABC'), list('BA')]),
                         expected_counts([list('BCA'), list('AB')]))

    def test_no_ties(self):
        b = [['A'], ['B'], ['C'], ['A']]
        self.assertEqual(expected_counts(b), counts('ABCA'))
        self.assertEqual(score_bounds(b, {('A', 'B'): 1}), (1, 1))

    def test_timezone(self):
        self.assertEqual(timestamp_us('2026-01-01T08:00:00+08:00'), timestamp_us('2026-01-01T00:00:00Z'))
        with self.assertRaises(ValueError):
            timestamp_us('2026-01-01T00:00:00')

    def test_missing_drops_whole_case(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d)/'x.csv'
            p.write_text('case_id,timestamp,resource\na,2026-01-01T00:00:00Z,A\na,2026-01-01T00:01:00Z,\nb,2026-01-01T00:00:00Z,B\n')
            cases, audit = load_csv(p)
            self.assertEqual(set(cases), {'b'})
            self.assertEqual(audit['invalid_cases'], ['a'])

    def test_xes(self):
        xes = '<log xmlns="http://www.xes-standard.org/"><trace><string key="concept:name" value="c"/><event><string key="org:resource" value="A"/><date key="time:timestamp" value="2026-01-01T00:00:00Z"/><string key="lifecycle:transition" value="complete"/></event></trace></log>'
        with tempfile.TemporaryDirectory() as d:
            p, q = Path(d)/'x.xes', Path(d)/'x.csv'
            p.write_text(xes)
            stats = convert_xes(p, q, 'complete')
            cases, _ = load_csv(q)
            self.assertEqual(stats['events_written'], 1)
            self.assertEqual(cases['c'][0][1], 'A')

    def test_sorting(self):
        self.assertEqual(blocks_from_events([(2, 'C'), (1, 'A'), (1, 'B')]), [['A', 'B'], ['C']])

    def test_independent_cases_add(self):
        b, c = [['A', 'B'], ['C']], [['B'], ['A', 'C']]
        weights = {('A', 'B'): 1, ('B', 'C'): -1}
        lo1, hi1 = score_bounds(b, weights)
        lo2, hi2 = score_bounds(c, weights)
        scores = [x['A', 'B'] - x['B', 'C'] + y['A', 'B'] - y['B', 'C']
                  for x in exhaustive_counts(b) for y in exhaustive_counts(c)]
        self.assertEqual((lo1 + lo2, hi1 + hi2), (min(scores), max(scores)))

    def test_large_irrelevant_block_exact_zero(self):
        b = [list('AB') * 20, ['C']]
        self.assertEqual(score_bounds(b, {('C', 'A'): 1}, max_block=2), (0, 0))
        self.assertIsNone(score_bounds(b, {('A', 'B'): 1}, max_block=2))

    def test_cheap_bounds_and_certificates_against_enumeration(self):
        rng = random.Random(113)
        for _ in range(100):
            b = [[rng.choice('ABC') for _ in range(rng.randint(1, 4))]
                 for _ in range(rng.randint(1, 3))]
            intervals = cheap_edge_bounds(b)
            records = list(exhaustive_counts(b))
            self.assertEqual(set(intervals), set(expected_counts(b)))
            for edge, (lo, hi) in intervals.items():
                self.assertTrue(all(lo <= record[edge] <= hi for record in records))
            for k in (1, 2, 5):
                cert = screen_top_k(intervals, k)
                for record in records:
                    for edge, status in cert.items():
                        if status == 'excluded':
                            self.assertGreaterEqual(sum(record[f] > record[edge] for f in intervals if f != edge), k)
                        if status == 'certified':
                            self.assertLess(sum(record[f] >= record[edge] for f in intervals if f != edge), k)

    def test_top_k_profile_keeps_ties(self):
        scores = {('A', 'B'): 5, ('B', 'C'): 3, ('A', 'C'): 3}
        p = top_k_profile(scores, 2)
        self.assertEqual(p['strict'], [('A', 'B')])
        self.assertEqual(len(p['boundary']), 2)
        self.assertEqual(p['slots'], 1)
        self.assertFalse(p['unique'])
        self.assertTrue(top_k_profile(scores, 3)['unique'])
        self.assertEqual(top_k_profile({}, 5)['slots'], 0)

    def test_outside_expected_top_is_still_competitor(self):
        intervals = {('A', 'B'): (5, 5), ('B', 'C'): (0, 6), ('C', 'D'): (0, 2)}
        result = screen_top_k(intervals, 1)
        self.assertEqual(result[('A', 'B')], 'unknown')
        self.assertEqual(result[('B', 'C')], 'unknown')
        self.assertEqual(result[('C', 'D')], 'excluded')

    def test_resource_renaming(self):
        b = [['A', 'B', 'A'], ['C', 'B']]
        names = {'A': 'z', 'B': 'a', 'C': 'm'}
        renamed = [[names[x] for x in block] for block in b]
        mapped = {(names[u], names[v]): x for (u, v), x in expected_counts(b).items()}
        self.assertEqual(mapped, expected_counts(renamed))
        self.assertEqual(score_bounds(b, {('A', 'B'): 1}),
                         score_bounds(renamed, {('z', 'a'): 1}))


if __name__ == '__main__':
    unittest.main()
