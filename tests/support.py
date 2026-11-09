import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

SLOTS = [
    "dawn",
    "morning",
    "forenoon",
    "noon",
    "afternoon_early",
    "afternoon",
    "dusk",
    "evening",
    "night",
    "close",
]


def write_json(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def base_config(**overrides):
    config = {
        "recipient": "+8613800138000",
        "timezone": "Asia/Shanghai",
        "start_hour": 6,
        "end_hour": 23,
        "grace_minutes": 20,
        "quote_cooldown_days": 45,
        "frame_cooldown_days": 7,
    }
    config.update(overrides)
    return config


def quote(qid="q1", text="执子之手，与子偕老。", slots=None, author="诗经", work="邶风·击鼓"):
    return {
        "id": qid,
        "text": text,
        "author": author,
        "work": work,
        "slots": list(slots or SLOTS),
    }


def minimal_frames():
    frames = []
    for slot in SLOTS:
        if slot == "close":
            open_text = "今天最后一条。晚安。"
            close_text = "去睡吧。晚安。"
        else:
            open_text = "此刻想你。"
            close_text = "这一句给你。"
        frames.append({"id": f"{slot}-o", "slot": slot, "role": "open", "text": open_text})
        frames.append({"id": f"{slot}-c", "slot": slot, "role": "close", "text": close_text})
    return frames


def minimal_denylist():
    return {slot: [] for slot in SLOTS}


def minimal_plains():
    text = (
        "想你这件事我说得具体一点。记得吃饭，记得喝水，忙的时候也停一下。"
        "我想你此刻过得好不好，有没有偷偷笑。你要好好的，我在这头等你。"
    )
    slots = ["morning", "forenoon", "noon", "afternoon_early", "afternoon", "evening", "night"]
    return [{"id": f"{slot}-p", "slot": slot, "text": text} for slot in slots]


def make_project(root, quotes=None, frames=None, denylist=None, config=None, state=None, plains=None):
    root = Path(root)
    write_json(root / "corpus" / "quotes.json", [quote()] if quotes is None else quotes)
    write_json(root / "corpus" / "frames.json", minimal_frames() if frames is None else frames)
    write_json(root / "corpus" / "plains.json", minimal_plains() if plains is None else plains)
    write_json(root / "corpus" / "denylist.json", minimal_denylist() if denylist is None else denylist)
    write_json(root / "config.json", base_config() if config is None else config)
    if state is not None:
        write_json(root / "state" / "state.json", state)
    return root
