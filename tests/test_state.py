import json
import support
import unittest
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from sweetline.state import already_sent, load_state, locked, record

TZ = ZoneInfo("Asia/Shanghai")


class StateTest(unittest.TestCase):
    def setUp(self):
        import tempfile
        from pathlib import Path

        self.directory = tempfile.TemporaryDirectory()
        self.root = Path(self.directory.name)

    def tearDown(self):
        self.directory.cleanup()

    def test_missing_state_is_empty(self):
        state = load_state(self.root)
        self.assertEqual(state["sent_hours"], [])
        self.assertFalse(already_sent(state, "2026-11-09-06"))

    def test_record_then_seen_and_prune(self):
        moment = datetime(2026, 11, 9, 6, 0, tzinfo=TZ)
        old = moment - timedelta(days=45)
        keep = moment - timedelta(days=44)
        support.write_json(
            self.root / "state" / "state.json",
            {
                "sent_hours": [
                    f"{old:%Y-%m-%d}-{old.hour:02d}",
                    f"{keep:%Y-%m-%d}-{keep.hour:02d}",
                ],
                "quotes": [
                    {"id": "oldq", "at": old.isoformat()},
                    {"id": "keepq", "at": keep.isoformat()},
                ],
                "frames": [
                    {"id": "oldf", "at": old.isoformat()},
                    {"id": "keepf", "at": keep.isoformat()},
                ],
            },
        )
        with locked(self.root):
            record(
                self.root,
                "2026-11-09-06",
                {"quote_id": "newq", "open_id": "newo", "close_id": "newc"},
                moment,
                45,
            )
        saved = json.loads((self.root / "state" / "state.json").read_text(encoding="utf-8"))
        quote_ids = [item["id"] for item in saved["quotes"]]
        frame_ids = [item["id"] for item in saved["frames"]]
        self.assertEqual(quote_ids, ["keepq", "newq"])
        self.assertIn("keepf", frame_ids)
        self.assertNotIn("oldf", frame_ids)
        self.assertIn("newo", frame_ids)
        self.assertIn("newc", frame_ids)
        self.assertIn("2026-11-09-06", saved["sent_hours"])
        self.assertIn(f"{keep:%Y-%m-%d}-{keep.hour:02d}", saved["sent_hours"])
        self.assertNotIn(f"{old:%Y-%m-%d}-{old.hour:02d}", saved["sent_hours"])
        self.assertTrue(already_sent(saved, "2026-11-09-06"))


if __name__ == "__main__":
    unittest.main()
