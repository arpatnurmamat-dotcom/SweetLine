import support
import unittest
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from sweetline.compose import compose, compose_plain, for_hour
from sweetline.corpus import char_count

TZ = ZoneInfo("Asia/Shanghai")


def project(quotes, frames=None, denylist=None):
    return {
        "quotes": quotes,
        "frames": frames if frames is not None else support.minimal_frames(),
        "denylist": denylist if denylist is not None else support.minimal_denylist(),
    }


class ComposeTest(unittest.TestCase):
    def test_render_shape_and_determinism(self):
        quotes = [
            support.quote("q1", text="执子之手，与子偕老。", slots=["dawn"]),
            support.quote("q2", text="思君如流水，何有穷已时。", slots=["dawn"], author="徐干", work="室思"),
            support.quote("q3", text="愿得一心人，白头不相离。", slots=["dawn"], author="卓文君", work="白头吟"),
        ]
        frames = []
        for slot in support.SLOTS:
            for index, text in enumerate(("此刻想你。", "我在。", "看着你。"), start=1):
                open_text = f"今天最后{index}。晚安。" if slot == "close" else text
                close_text = f"去睡吧{index}。晚安。" if slot == "close" else f"收好{index}。"
                frames.append({"id": f"{slot}-o-{index}", "slot": slot, "role": "open", "text": open_text})
                frames.append({"id": f"{slot}-c-{index}", "slot": slot, "role": "close", "text": close_text})
        data = project(quotes, frames)
        moment = datetime(2026, 11, 9, 6, 0, tzinfo=TZ)
        history = {"quotes": [], "frames": []}
        first, picks = compose(data, "dawn", moment, history, 45, 7)
        second, again = compose(data, "dawn", moment, history, 45, 7)
        self.assertEqual(first, second)
        self.assertEqual(picks, again)
        self.assertEqual(picks["quote_id"], "q1")
        self.assertEqual(picks["open_id"], "dawn-o-1")
        self.assertEqual(picks["close_id"], "dawn-c-1")
        quote = next(item for item in quotes if item["id"] == picks["quote_id"])
        opener = next(item for item in frames if item["id"] == picks["open_id"])
        closer = next(item for item in frames if item["id"] == picks["close_id"])
        self.assertEqual(
            first,
            f"{opener['text']}\n\n{quote['text']}\n——{quote['author']}《{quote['work']}》\n\n{closer['text']}",
        )
        self.assertEqual(history, {"quotes": [], "frames": []})

    def test_slot_filter(self):
        quotes = [
            support.quote("q-dawn", text="女曰鸡鸣，士曰昧旦。", slots=["dawn"]),
            support.quote("q-night", text="海上生明月，天涯共此时。", slots=["night"], author="张九龄", work="望月怀远"),
        ]
        moment = datetime(2026, 11, 9, 6, 0, tzinfo=TZ)
        message, picks = compose(project(quotes), "dawn", moment, {"quotes": [], "frames": []}, 45, 7)
        self.assertEqual(picks["quote_id"], "q-dawn")
        self.assertNotIn("海上生明月", message)

    def test_full_message_skips_banned_frame(self):
        denylist = support.minimal_denylist()
        denylist["dawn"] = ["晚安"]
        frames = support.minimal_frames()
        frames.append({"id": "dawn-c-bad", "slot": "dawn", "role": "close", "text": "早点晚安。"})
        quotes = [support.quote("q1", slots=["dawn"])]
        moment = datetime(2026, 11, 9, 6, 0, tzinfo=TZ)
        message, picks = compose(project(quotes, frames, denylist), "dawn", moment, {"quotes": [], "frames": []}, 45, 7)
        self.assertNotIn("晚安", message)
        self.assertEqual(picks["close_id"], "dawn-c")

    def test_cooldown_boundary_and_oldest_fallback(self):
        moment = datetime(2026, 11, 9, 6, 0, tzinfo=TZ)
        quotes = [
            support.quote("q-old", text="执子之手，与子偕老。", slots=["dawn"]),
            support.quote("q-mid", text="思君如流水，何有穷已时。", slots=["dawn"], author="徐干", work="室思"),
            support.quote("q-new", text="愿得一心人，白头不相离。", slots=["dawn"], author="卓文君", work="白头吟"),
        ]
        history = {
            "quotes": [
                {"id": "q-new", "at": (moment - timedelta(days=1)).isoformat()},
                {"id": "q-mid", "at": (moment - timedelta(days=3)).isoformat()},
                {"id": "q-old", "at": (moment - timedelta(days=10)).isoformat()},
            ],
            "frames": [],
        }
        _, picks = compose(project(quotes), "dawn", moment, history, 45, 7)
        self.assertEqual(picks["quote_id"], "q-old")

        pair = [quotes[0], quotes[2]]
        expired = {
            "quotes": [{"id": "q-new", "at": (moment - timedelta(days=45)).isoformat()}],
            "frames": [],
        }
        _, picks = compose(project(pair), "dawn", moment, expired, 45, 7)
        self.assertEqual(picks["quote_id"], "q-old")

        still_hot = {
            "quotes": [
                {"id": "q-new", "at": (moment - timedelta(days=45) + timedelta(seconds=1)).isoformat()},
            ],
            "frames": [],
        }
        _, picks = compose(project(pair), "dawn", moment, still_hot, 45, 7)
        self.assertEqual(picks["quote_id"], "q-old")

    def test_frame_cooldown_keeps_exact_seven_days_usable(self):
        moment = datetime(2026, 11, 9, 8, 0, tzinfo=TZ)
        frames = support.minimal_frames()
        frames.append({"id": "morning-o-old", "slot": "morning", "role": "open", "text": "清晨好。"})
        quotes = [support.quote("q1", slots=["morning"])]
        expired = {
            "quotes": [],
            "frames": [{"id": "morning-o-old", "at": (moment - timedelta(days=7)).isoformat()}],
        }
        _, picks = compose(project(quotes, frames), "morning", moment, expired, 45, 7)
        self.assertEqual(picks["open_id"], "morning-o")
        still_hot = {
            "quotes": [],
            "frames": [
                {"id": "morning-o-old", "at": (moment - timedelta(days=7) + timedelta(seconds=1)).isoformat()}
            ],
        }
        _, picks = compose(project(quotes, frames), "morning", moment, still_hot, 45, 7)
        self.assertEqual(picks["open_id"], "morning-o")

    def test_close_message_contains_phrase(self):
        moment = datetime(2026, 11, 9, 23, 0, tzinfo=TZ)
        message, _ = compose(
            project([support.quote("q1", slots=["close"])]),
            "close",
            moment,
            {"quotes": [], "frames": []},
            45,
            7,
        )
        self.assertTrue("晚安" in message or "今天最后" in message)

    def test_plain_hour_is_long_and_has_no_poem(self):
        moment = datetime(2026, 11, 9, 12, 0, tzinfo=TZ)
        text = "想你记得吃饭喝水" * 7
        data = {
            "plains": [{"id": "noon-p-01", "slot": "noon", "text": text}],
            "denylist": {"noon": []},
        }
        message, picks = for_hour(data, "noon", moment, {}, 45, 7)
        self.assertEqual(picks, {"plain_id": "noon-p-01"})
        self.assertNotIn("——", message)
        self.assertNotIn("《", message)
        self.assertGreaterEqual(char_count(message), 50)

    def test_plain_cooldown_skips_hot_line(self):
        moment = datetime(2026, 11, 9, 12, 0, tzinfo=TZ)
        body = "想你记得吃饭喝水" * 7
        data = {
            "plains": [
                {"id": "noon-p-a", "slot": "noon", "text": body + "甲"},
                {"id": "noon-p-b", "slot": "noon", "text": body + "乙"},
            ],
            "denylist": {"noon": []},
        }
        hot = {"plains": [{"id": "noon-p-a", "at": (moment - timedelta(days=7) + timedelta(seconds=1)).isoformat()}]}
        _, picks = compose_plain(data, "noon", moment, hot, 7)
        self.assertEqual(picks["plain_id"], "noon-p-b")
        cooled = {"plains": [{"id": "noon-p-a", "at": (moment - timedelta(days=7)).isoformat()}]}
        _, fresh = compose_plain(data, "noon", moment, cooled, 7)
        self.assertEqual(fresh["plain_id"], "noon-p-b")

    def test_plain_repeats_only_after_the_rest_are_used(self):
        moment = datetime(2026, 11, 9, 12, 0, tzinfo=TZ)
        body = "想你记得吃饭喝水" * 7
        data = {
            "plains": [
                {"id": "noon-p-a", "slot": "noon", "text": body + "甲"},
                {"id": "noon-p-b", "slot": "noon", "text": body + "乙"},
                {"id": "noon-p-c", "slot": "noon", "text": body + "丙"},
            ],
            "denylist": {"noon": []},
        }
        history = {
            "plains": [
                {"id": "noon-p-a", "at": (moment - timedelta(days=1)).isoformat()},
                {"id": "noon-p-b", "at": (moment - timedelta(days=10)).isoformat()},
            ]
        }
        _, picks = compose_plain(data, "noon", moment, history, 7)
        self.assertEqual(picks["plain_id"], "noon-p-c")
        history["plains"].append({"id": "noon-p-c", "at": moment.isoformat()})
        _, picks = compose_plain(data, "noon", moment, history, 7)
        self.assertEqual(picks["plain_id"], "noon-p-b")

    def test_empty_pool_raises(self):
        moment = datetime(2026, 11, 9, 6, 0, tzinfo=TZ)
        with self.assertRaises(ValueError):
            compose(project([support.quote("q1", slots=["night"])]), "dawn", moment, {"quotes": [], "frames": []}, 45, 7)


if __name__ == "__main__":
    unittest.main()
