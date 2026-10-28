import datetime
import unittest
from extensions.uci_v8 import local_clock, contradictory, blocks


class UciEvidenceRules(unittest.TestCase):
    def event(self,minute,counter,index=0,supported='1'):
        return dict(time=datetime.datetime(2016,2,29,0,minute),counter=counter,
                    source_index=index,counter_supported=supported)

    def test_same_timestamp_counter_decrease_is_not_cross_time_conflict(self):
        events=[self.event(0,2,0),self.event(0,1,1),self.event(1,3,2)]
        self.assertFalse(contradictory(events))
        self.assertEqual([[e['source_index'] for e in b] for b in blocks(events,'C')],[[1],[0],[2]])

    def test_conflict_checks_all_earlier_groups_and_preserves_fallback(self):
        events=[self.event(0,4,0,'0'),self.event(1,2,1,'0'),self.event(1,3,2,'0')]
        self.assertTrue(contradictory(events))
        self.assertEqual(blocks(events,'C'),blocks(events,'T'))
        self.assertEqual(sum(map(len,blocks(events,'C'))),3)

    def test_equal_counter_remains_unordered_and_no_record_is_removed(self):
        events=[self.event(0,2,0),self.event(0,2,1),self.event(0,1,2)]
        grouped=blocks(events,'C')
        self.assertEqual([[e['source_index'] for e in b] for b in grouped],[[2],[0,1]])
        self.assertEqual(sum(map(len,grouped)),3)

    def test_local_clock_is_day_first_and_has_no_assumed_timezone(self):
        stamp=local_clock('3/4/2016 01:23')
        self.assertEqual((stamp.year,stamp.month,stamp.day),(2016,4,3))
        self.assertIsNone(stamp.tzinfo)
        with self.assertRaises(ValueError):local_clock('2016-04-03T01:23Z')


if __name__=='__main__':unittest.main()
