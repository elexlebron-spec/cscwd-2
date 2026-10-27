"""Independent exhaustive checks for the unfrozen v6 extension."""
import itertools
import random
import unittest
from collections import Counter
from extensions.order_evidence import solve,radius,Unsupported


def evaluate(order,resources,weights):
    return sum(weights.get((resources[a],resources[b]),0) if resources[a]!=resources[b] else 0
               for a,b in zip(order,order[1:]))


class OrderEvidenceTests(unittest.TestCase):
    def test_signed_multiplicity_bounds_and_witness(self):
        rng=random.Random(20261027)
        for _ in range(250):
            sizes=[rng.randint(1,4) for _ in range(rng.randint(1,3))]
            labels=[rng.choice('ABCD') for _ in range(sum(sizes))]
            blocks=[];start=0
            for n in sizes:
                blocks.append([(i,labels[i]) for i in range(start,start+n)]);start+=n
            weights={('A','B'):1,(('C','A') if _%2 else ('C','D')):-1}
            scores=[evaluate(tuple(itertools.chain.from_iterable(p)),labels,weights)
                    for p in itertools.product(*(itertools.permutations([i for i,_ in b]) for b in blocks))]
            low,high,order=solve(blocks,weights,witness=True)
            self.assertEqual((low,high),(min(scores),max(scores)))
            self.assertEqual(sorted(order),list(range(len(labels))))
            self.assertEqual(evaluate(order,labels,weights),low)
    def test_inactive_resource_merging_keeps_events(self):
        blocks=[[(0,'X'),(1,'Y'),(2,'A'),(3,'B'),(4,'Z')]]
        low,high,order=solve(blocks,{('A','B'):1},witness=True)
        self.assertEqual((low,high),(0,1));self.assertEqual(len(order),5)
    def test_large_homogeneous_and_boundary(self):
        blocks=[[(i,'A') for i in range(40)],[(40,'B')]]
        self.assertEqual(solve(blocks,{('A','B'):1},witness=True),(1,1,tuple(range(41))))
    def test_count_state_limit_explicit(self):
        with self.assertRaises(Unsupported):solve([[(0,'A'),(1,'B')]],{('A','B'):1},max_count_states=3)
    def test_minimum_relaxation_against_all_subsets(self):
        rng=random.Random(20261028)
        for _ in range(300):
            t=[rng.randint(-4,3) for _ in range(rng.randint(1,7))]
            a=[v+rng.randint(0,4) for v in t]
            for threshold in [0,-1]:
                feasible=[]
                for mask in itertools.product([0,1],repeat=len(a)):
                    score=sum(tv if use else av for tv,av,use in zip(t,a,mask))
                    if score<=threshold:feasible.append(sum(mask))
                got=radius(a,t,threshold)
                self.assertEqual(None if got is None else got['count'],min(feasible) if feasible else None)
                if got is not None:
                    indices=set(got['indices'])
                    self.assertEqual(sum(t[i] if i in indices else a[i] for i in range(len(a))),got['minimum'])
    def test_tie_is_not_strict_reversal(self):
        self.assertEqual(radius([1],[0],0)['count'],1)
        self.assertIsNone(radius([1],[0],-1))


if __name__=='__main__':unittest.main()
