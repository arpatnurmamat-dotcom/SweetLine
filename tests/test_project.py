import plistlib
import support
import unittest
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from sweetline.clock import hour_key, slot_for, uses_poem
from sweetline.compose import for_hour
from sweetline.corpus import char_count, hits_denylist, load

TZ = ZoneInfo("Asia/Shanghai")


class ProjectTest(unittest.TestCase):
    def test_plist_fires_each_hour_from_6_through_23(self):
        with (support.ROOT / "launchd" / "com.sweetline.send.plist").open("rb") as handle:
            plist = plistlib.load(handle)
        hours = sorted(item["Hour"] for item in plist["StartCalendarInterval"])
        self.assertEqual(hours, list(range(6, 24)))
        self.assertTrue(all(item["Minute"] == 0 for item in plist["StartCalendarInterval"]))
        self.assertEqual(plist["Label"], "com.sweetline.send")
        self.assertFalse(plist["RunAtLoad"])
        self.assertEqual(plist["WorkingDirectory"], str(support.ROOT))
        self.assertEqual(plist["ProgramArguments"], ["/usr/bin/python3", "-m", "sweetline"])

    def test_real_corpus_covers_every_slot_and_composes(self):
        data = load(support.ROOT)
        self.assertGreaterEqual(len(data["quotes"]), 30)
        for slot in support.SLOTS:
            quotes = [item for item in data["quotes"] if slot in item["slots"]]
            opens = [item for item in data["frames"] if item["slot"] == slot and item["role"] == "open"]
            closes = [item for item in data["frames"] if item["slot"] == slot and item["role"] == "close"]
            self.assertGreaterEqual(len(quotes), 8, slot)
            self.assertGreaterEqual(len(opens), 4, slot)
            self.assertGreaterEqual(len(closes), 4, slot)
            for frame in opens + closes:
                self.assertFalse(hits_denylist(frame["text"], data["denylist"][slot]), frame["id"])
        for slot in ("morning", "forenoon", "noon", "afternoon_early", "afternoon", "evening", "night"):
            plains = [item for item in data["plains"] if item["slot"] == slot]
            self.assertGreaterEqual(len(plains), 4, slot)
            for item in plains:
                self.assertGreaterEqual(char_count(item["text"]), 50, item["id"])
        seen = {}
        for hour in range(6, 24):
            moment = datetime(2026, 11, 9, hour, 0, tzinfo=TZ)
            slot = {
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
            }[hour]
            message, picks = for_hour(data, slot, moment, {"quotes": [], "frames": [], "plains": []}, 45, 7)
            again, _ = for_hour(data, slot, moment, {"quotes": [], "frames": [], "plains": []}, 45, 7)
            self.assertEqual(message, again)
            self.assertFalse(hits_denylist(message, data["denylist"][slot]), hour_key(moment))
            if uses_poem(hour):
                self.assertIn("quote_id", picks)
                self.assertIn("——", message)
                self.assertIn("《", message)
            else:
                self.assertIn("plain_id", picks)
                self.assertNotIn("——", message)
                self.assertGreaterEqual(char_count(message), 50)
            if slot == "close":
                self.assertTrue("晚安" in message or "今天最后" in message)
            seen[hour] = message
        self.assertGreaterEqual(len(set(seen.values())), 10)

    def test_plain_lines_do_not_repeat_within_a_week(self):
        data = load(support.ROOT)
        per_day = {
            "morning": (7, 8),
            "forenoon": (9, 11),
            "noon": (12,),
            "afternoon_early": (13, 14),
            "afternoon": (16, 17),
            "evening": (19, 20),
            "night": (22,),
        }
        history = {"quotes": [], "frames": [], "plains": []}
        seen = []
        start = datetime(2026, 11, 9, tzinfo=TZ)
        for day in range(7):
            for hours in per_day.values():
                for hour in hours:
                    moment = start + timedelta(days=day, hours=hour)
                    slot = slot_for(moment, 6, 23)
                    message, picks = for_hour(data, slot, moment, history, 45, 7)
                    self.assertNotIn(message, seen)
                    seen.append(message)
                    history["plains"].append({"id": picks["plain_id"], "at": moment.isoformat()})


if __name__ == "__main__":
    unittest.main()
