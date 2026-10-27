import unittest
from src.core import top_k_profile
from src.study import family, order_events
from src.study_data import make_blocks, code_key
from src.verify_study import unique_orders


class StudyTests(unittest.TestCase):
    def test_missing_code_singleton_has_no_ordering_choice(self):
        singleton = [dict(time=1,code='',resource='A',source_index=0)]
        self.assertEqual(make_blocks(singleton,'N'),[singleton])
        with self.assertRaises(ValueError):
            make_blocks(singleton+[dict(time=1,code='01_HOOFD_010',resource='B',source_index=1)],'N')

    def test_multiset_enumeration_does_not_expand_duplicate_event_permutations(self):
        orders = unique_orders(['A']*34+['B'])
        self.assertEqual(len(orders),35)
        self.assertEqual(len(set(orders)),35)
        self.assertTrue(all(order.count('A')==34 and order.count('B')==1 for order in orders))

    def test_suffix_variants_remain_unordered_in_numeric_model(self):
        events = [dict(time=1,code='01_HOOFD_030_2',resource='B',source_index=0),
                  dict(time=1,code='01_HOOFD_030_1',resource='A',source_index=1),
                  dict(time=2,code='01_HOOFD_010',resource='C',source_index=2)]
        numeric = make_blocks(events,'N')
        full = make_blocks(events,'F')
        self.assertEqual([len(b) for b in numeric],[2,1])
        self.assertEqual([len(b) for b in full],[1,1,1])
        self.assertEqual([e['source_index'] for e in order_events(numeric,'source')],[0,1,2])
        self.assertEqual([e['source_index'] for e in order_events(full,'source')],[1,0,2])

    def test_subprocess_with_embedded_underscore_and_attached_suffix(self):
        self.assertEqual(code_key('09_AH_I_010'),('09_AH_I',10))
        self.assertEqual(code_key('01_HOOFD_494a'),('01_HOOFD',494))
        with self.assertRaises(ValueError):
            code_key('unknown')

    def test_equal_top_families_despite_different_cutoff_tiers(self):
        first = top_k_profile({'a':5,'b':4,'c':1},2)
        second = top_k_profile({'a':4,'b':4,'c':1},2)
        self.assertEqual(family(first),family(second))
        tied = top_k_profile({'a':4,'b':4,'c':4},2)
        self.assertNotEqual(family(first),family(tied))

    def test_tie_membership_family_does_not_use_identifier_tiebreak(self):
        first = top_k_profile({'a':10,'b':5,'c':5},2)
        second = top_k_profile({'a':20,'b':7,'c':7},2)
        self.assertEqual(family(first),family(second))
        self.assertFalse(first['unique'])


if __name__ == '__main__':
    unittest.main()
