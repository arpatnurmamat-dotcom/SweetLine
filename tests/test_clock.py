import support
import unittest
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from sweetline.clock import hour_key, in_grace, now, slot_for, uses_poem

TZ = ZoneInfo("Asia/Shanghai")


class ClockTest(unittest.TestCase):
    def test_slots_cover_send_window(self):
        expected = {
            6: "dawn",
            7: "morning",
            8: "morning",
            9: "forenoon",
            10: "forenoon",
            11: "forenoon",
            12: "noon",
            13: "afternoon_early",
            14: "afternoon_early",
            15: "afternoon",
            16: "afternoon",
            17: "afternoon",
            18: "dusk",
            19: "evening",
            20: "evening",
            21: "night",
            22: "night",
            23: "close",
        }
        for hour, name in expected.items():
            moment = datetime(2026, 11, 9, hour, 0, tzinfo=TZ)
            self.assertEqual(slot_for(moment, 6, 23), name, hour)
        for hour in range(0, 6):
            moment = datetime(2026, 11, 9, hour, 0, tzinfo=TZ)
            self.assertIsNone(slot_for(moment, 6, 23), hour)

    def test_window_bounds_are_inclusive_and_configurable(self):
        dawn = datetime(2026, 11, 9, 6, 0, tzinfo=TZ)
        noon = datetime(2026, 11, 9, 12, 0, tzinfo=TZ)
        after = datetime(2026, 11, 9, 13, 0, tzinfo=TZ)
        self.assertIsNone(slot_for(dawn, 7, 23))
        self.assertEqual(slot_for(noon, 7, 12), "noon")
        self.assertIsNone(slot_for(after, 7, 12))

    def test_grace_includes_minute_20(self):
        self.assertTrue(in_grace(datetime(2026, 11, 9, 6, 0, tzinfo=TZ), 20))
        self.assertTrue(in_grace(datetime(2026, 11, 9, 6, 20, 59, tzinfo=TZ), 20))
        self.assertFalse(in_grace(datetime(2026, 11, 9, 6, 21, tzinfo=TZ), 20))

    def test_hour_key(self):
        moment = datetime(2026, 11, 9, 6, 40, tzinfo=TZ)
        self.assertEqual(hour_key(moment), "2026-11-09-06")

    def test_poem_hours_are_the_sparse_ones(self):
        poem = [hour for hour in range(6, 24) if uses_poem(hour)]
        self.assertEqual(poem, [6, 10, 15, 18, 21, 23])

    def test_now_uses_configured_zone(self):
        moment = now("Asia/Shanghai")
        self.assertEqual(moment.utcoffset(), timedelta(hours=8))
        self.assertEqual(moment.tzinfo.key, "Asia/Shanghai")


if __name__ == "__main__":
    unittest.main()
