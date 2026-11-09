import subprocess

SCRIPT = """on run {targetHandle, msg}
  tell application "Messages"
    set targetService to first account whose service type = iMessage
    set targetBuddy to participant targetHandle of targetService
    send msg to targetBuddy
  end tell
end run
"""


def send(recipient, text, runner=None):
    run = runner or subprocess.run
    return run(
        ["osascript", "-", recipient, text],
        input=SCRIPT,
        text=True,
        check=True,
        capture_output=True,
    )
