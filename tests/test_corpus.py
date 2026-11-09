import support
import unittest

from sweetline.corpus import hits_denylist, load, validate

MORNING_BAN = ["晚安", "晚餐", "夜宵", "入睡", "梦里", "夜里", "月亮", "星空", "熬夜"]
EVENING_BAN = ["早安", "早餐", "清晨", "刚醒", "晨光"]


class CorpusTest(unittest.TestCase):
    def test_hits_denylist_by_substring(self):
        self.assertTrue(hits_denylist("今天说晚安", ["晚安"]))
        self.assertFalse(hits_denylist("明天醒来", ["刚醒"]))

    def test_validate_accepts_minimal_corpus(self):
        validate(
            {
                "quotes": [support.quote()],
                "frames": support.minimal_frames(),
                "denylist": support.minimal_denylist(),
            }
        )

    def test_duplicate_quote_id_rejected(self):
        data = {
            "quotes": [support.quote("q1"), support.quote("q1", text="思君如流水，何有穷已时。")],
            "frames": support.minimal_frames(),
            "denylist": support.minimal_denylist(),
        }
        with self.assertRaises(ValueError):
            validate(data)

    def test_quote_must_pass_every_tagged_slot(self):
        denylist = support.minimal_denylist()
        denylist["dawn"] = ["月亮"]
        denylist["night"] = ["早安"]
        bad = support.quote("q1", text="海上生月亮", slots=["dawn", "night"])
        with self.assertRaises(ValueError):
            validate(
                {
                    "quotes": [bad],
                    "frames": support.minimal_frames(),
                    "denylist": denylist,
                }
            )

    def test_night_quote_may_mention_moon_word_when_not_banned(self):
        denylist = support.minimal_denylist()
        denylist["night"] = list(EVENING_BAN)
        good = support.quote("q1", text="海上生明月，天涯共此时。", slots=["night"])
        validate(
            {
                "quotes": [good],
                "frames": support.minimal_frames(),
                "denylist": denylist,
            }
        )

    def test_close_frames_need_goodnight_phrase(self):
        frames = support.minimal_frames()
        frames = [frame for frame in frames if frame["id"] != "close-c"]
        frames.append({"id": "close-c", "slot": "close", "role": "close", "text": "去睡吧。"})
        with self.assertRaises(ValueError):
            validate(
                {
                    "quotes": [support.quote()],
                    "frames": frames,
                    "denylist": support.minimal_denylist(),
                }
            )

    def test_each_slot_needs_open_and_close(self):
        frames = [frame for frame in support.minimal_frames() if frame["id"] != "noon-o"]
        with self.assertRaises(ValueError):
            validate(
                {
                    "quotes": [support.quote()],
                    "frames": frames,
                    "denylist": support.minimal_denylist(),
                }
            )

    def test_unknown_slot_rejected(self):
        with self.assertRaises(ValueError):
            validate(
                {
                    "quotes": [support.quote(slots=["midnight"])],
                    "frames": support.minimal_frames(),
                    "denylist": support.minimal_denylist(),
                }
            )

    def test_empty_slots_rejected(self):
        bad = support.quote()
        bad["slots"] = []
        with self.assertRaises(ValueError):
            validate(
                {
                    "quotes": [bad],
                    "frames": support.minimal_frames(),
                    "denylist": support.minimal_denylist(),
                }
            )

    def test_short_plain_rejected(self):
        plains = support.minimal_plains()
        plains[0] = dict(plains[0], text="太短了")
        with self.assertRaises(ValueError):
            validate(
                {
                    "quotes": [support.quote()],
                    "frames": support.minimal_frames(),
                    "denylist": support.minimal_denylist(),
                    "plains": plains,
                }
            )

    def test_load_reads_project_files(self):
        root = support.ROOT
        denylist = load(root)["denylist"]
        for slot in ("dawn", "morning", "forenoon", "noon", "afternoon_early", "afternoon"):
            self.assertEqual(denylist[slot], MORNING_BAN)
        for slot in ("dusk", "evening", "night", "close"):
            self.assertEqual(denylist[slot], EVENING_BAN)


if __name__ == "__main__":
    unittest.main()
