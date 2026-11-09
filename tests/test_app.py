import json
import subprocess
import support
import tempfile
import unittest
from contextlib import redirect_stdout
from datetime import datetime
from io import StringIO
from pathlib import Path
from zoneinfo import ZoneInfo

from sweetline.app import run
from sweetline.corpus import char_count

TZ = ZoneInfo("Asia/Shanghai")


class AppTest(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.root = Path(self.directory.name)
        self.moment = datetime(2026, 11, 9, 6, 0, tzinfo=TZ)
        support.make_project(self.root)

    def tearDown(self):
        self.directory.cleanup()

    def test_dry_run_prints_without_sending_or_writing_state(self):
        calls = []

        def sender(recipient, text):
            calls.append((recipient, text))

        buffer = StringIO()
        with redirect_stdout(buffer):
            code = run(["--dry-run", "--now"], root=self.root, sender=sender, moment=self.moment)
        self.assertEqual(code, 0)
        self.assertEqual(calls, [])
        self.assertIn("执子之手，与子偕老。\n——诗经《邶风·击鼓》", buffer.getvalue())
        self.assertIn("——诗经《邶风·击鼓》", buffer.getvalue())
        self.assertFalse((self.root / "state" / "state.json").exists())

    def test_past_grace_skips_until_forced(self):
        late = datetime(2026, 11, 9, 6, 21, tzinfo=TZ)
        calls = []

        def sender(recipient, text):
            calls.append(text)

        self.assertEqual(run([], root=self.root, sender=sender, moment=late), 0)
        self.assertEqual(calls, [])
        self.assertEqual(run(["--now"], root=self.root, sender=sender, moment=late), 0)
        self.assertEqual(len(calls), 1)

    def test_outside_window_never_sends(self):
        night = datetime(2026, 11, 9, 3, 0, tzinfo=TZ)
        calls = []
        self.assertEqual(
            run(["--now"], root=self.root, sender=lambda recipient, text: calls.append(text), moment=night),
            0,
        )
        self.assertEqual(calls, [])

    def test_empty_recipient_refuses_real_send(self):
        support.make_project(self.root, config=support.base_config(recipient="  "))
        calls = []
        code = run(["--now"], root=self.root, sender=lambda recipient, text: calls.append(text), moment=self.moment)
        self.assertEqual(code, 1)
        self.assertEqual(calls, [])
        early = datetime(2026, 11, 9, 5, 0, tzinfo=TZ)
        self.assertEqual(run(["--now"], root=self.root, sender=lambda recipient, text: calls.append(text), moment=early), 0)

    def test_dry_run_allows_empty_recipient(self):
        support.make_project(self.root, config=support.base_config(recipient=""))
        buffer = StringIO()
        with redirect_stdout(buffer):
            code = run(["--dry-run"], root=self.root, moment=self.moment)
        self.assertEqual(code, 0)
        self.assertIn("执子之手，与子偕老。\n——诗经《邶风·击鼓》", buffer.getvalue())

    def test_success_records_hour_and_second_run_skips(self):
        calls = []

        def sender(recipient, text):
            calls.append(recipient)

        self.assertEqual(run(["--now"], root=self.root, sender=sender, moment=self.moment), 0)
        self.assertEqual(calls, ["+8613800138000"])
        saved = json.loads((self.root / "state" / "state.json").read_text(encoding="utf-8"))
        self.assertIn("2026-11-09-06", saved["sent_hours"])
        self.assertEqual(saved["quotes"][0]["id"], "q1")
        self.assertEqual(run(["--now"], root=self.root, sender=sender, moment=self.moment), 0)
        self.assertEqual(len(calls), 1)

    def test_plain_hour_records_plain_text(self):
        moment = datetime(2026, 11, 9, 12, 0, tzinfo=TZ)
        calls = []

        def sender(recipient, text):
            calls.append(text)

        self.assertEqual(run(["--now"], root=self.root, sender=sender, moment=moment), 0)
        self.assertGreaterEqual(char_count(calls[0]), 50)
        self.assertNotIn("——", calls[0])
        saved = json.loads((self.root / "state" / "state.json").read_text(encoding="utf-8"))
        self.assertEqual(saved["plains"][0]["id"], "noon-p")
        self.assertEqual(saved["quotes"], [])

    def test_send_failure_does_not_record(self):
        def sender(recipient, text):
            raise subprocess.CalledProcessError(1, ["osascript"])

        self.assertEqual(run(["--now"], root=self.root, sender=sender, moment=self.moment), 2)
        self.assertFalse((self.root / "state" / "state.json").exists())

    def test_bad_corpus_returns_1(self):
        support.write_json(self.root / "corpus" / "quotes.json", [{"id": "q1"}])
        self.assertEqual(run(["--now"], root=self.root, moment=self.moment, sender=lambda recipient, text: None), 1)

    def test_missing_config_returns_1(self):
        config = support.base_config()
        del config["timezone"]
        support.write_json(self.root / "config.json", config)
        self.assertEqual(run(["--now"], root=self.root, moment=self.moment), 1)


if __name__ == "__main__":
    unittest.main()
