"""Independent event-level enumeration for new precedence and retention logic."""
import itertools
import random
import unittest

from extensions.assumptions_v10 import solve_w, p_blocks, retain
from extensions.order_evidence import solve, Unsupported


def legal(order, events, model):
    pos = {v: i for i, v in enumerate(order)}
    for a, b in itertools.permutations(events, 2):
        ap, an, _ = a['code'].split('_'); bp, bn, _ = b['code'].split('_')
        before = (a['time'] < b['time'] or
                  a['time'] == b['time'] and ((model == 'P' and ap < bp) or
                  (model == 'W' and ap == bp and int(an) < int(bn))))
        if before and pos[a['source_index']] > pos[b['source_index']]:
            return False
    return True


class AssumptionTests(unittest.TestCase):
    def test_partial_models_against_original_event_permutations(self):
        rng = random.Random(2026102810)
        for trial in range(150):
            events = [dict(source_index=i, resource=rng.choice('ABCD'),
                           code='%s_%03d_%s' % (rng.choice('PQ'), rng.randrange(3), rng.choice('ab')),
                           time=rng.randrange(2)) for i in range(rng.randint(2, 7))]
            weights = {('A', 'B'): 1, ('C', 'A'): -1}
            ids = list(range(len(events)))
            def score(order):
                return sum(weights.get((events[a]['resource'], events[b]['resource']), 0)
                           for a, b in zip(order, order[1:]))
            for model in ['P', 'W']:
                values = [score(o) for o in itertools.permutations(ids) if legal(o, events, model)]
                lo, hi, order = (solve_w(events, weights, witness=True) if model == 'W' else
                                 solve(p_blocks(events), weights, witness=True))
                self.assertEqual((lo, hi), (min(values), max(values)), (trial, model))
                self.assertEqual(sorted(order), ids)
                self.assertTrue(legal(order, events, model))
                self.assertEqual(score(order), lo)

    def test_cross_subprocess_interleaving_allowed(self):
        events = [dict(source_index=i, resource=r, time=0, code=c)
                  for i, (r, c) in enumerate([('A', 'P_001_a'), ('B', 'P_002_a'),
                                              ('C', 'Q_001_a')])]
        lo, hi, order = solve_w(events, {('A', 'B'): 1}, witness=True)
        self.assertEqual((lo, hi), (0, 1))
        self.assertEqual(order, (0, 2, 1))

    def test_sufficient_retention_against_all_subsets(self):
        rng = random.Random(2026102811)
        for _ in range(300):
            t = [rng.randint(-4, 3) for i in range(rng.randint(1, 8))]
            a = [v+rng.randint(0, 4) for v in t]
            possible = [sum(mask) for mask in itertools.product([0, 1], repeat=len(a))
                        if sum(av if k else tv for av, tv, k in zip(a, t, mask)) > 0]
            got = retain(a, t)
            self.assertEqual(None if got is None else got['count'], min(possible) if possible else None)
            if got is not None:
                chosen = set(got['indices'])
                self.assertEqual(got['minimum'], sum(a[i] if i in chosen else t[i] for i in range(len(a))))
                self.assertGreater(got['minimum'], 0)

    def test_unknown_on_state_cap(self):
        events = [dict(source_index=i, resource=r, time=0, code='P_001_a')
                  for i, r in enumerate('ABCD')]
        with self.assertRaises(Unsupported):
            solve_w(events, {('A', 'B'): 1}, cap=3)


if __name__ == '__main__':
    unittest.main()
