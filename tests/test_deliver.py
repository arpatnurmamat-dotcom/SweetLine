import support
import unittest

from sweetline.deliver import SCRIPT, send


class DeliverTest(unittest.TestCase):
    def test_arguments_stay_outside_the_script(self):
        captured = {}

        def runner(args, input, text, check, capture_output):
            captured["args"] = args
            captured["input"] = input
            captured["text"] = text
            captured["check"] = check
            captured["capture_output"] = capture_output

            class Result:
                returncode = 0

            return Result()

        message = "早安。\n\n「执子之手，与子偕老。」"
        send("+8613800138000", message, runner=runner)
        self.assertEqual(captured["args"], ["osascript", "-", "+8613800138000", message])
        self.assertEqual(captured["input"], SCRIPT)
        self.assertNotIn("+8613800138000", SCRIPT)
        self.assertNotIn("执子之手", SCRIPT)
        self.assertIn("on run {targetHandle, msg}", SCRIPT)
        self.assertIn("service type = iMessage", SCRIPT)
        self.assertIn("send msg to targetBuddy", SCRIPT)
        self.assertTrue(captured["check"])
        self.assertTrue(captured["capture_output"])
        self.assertTrue(captured["text"])


if __name__ == "__main__":
    unittest.main()
