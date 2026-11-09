import json
from pathlib import Path

from sweetline.clock import SLOT_NAMES


MIN_PLAIN_CHARS = 50
PLAIN_SLOTS = (
    "morning",
    "forenoon",
    "noon",
    "afternoon_early",
    "afternoon",
    "evening",
    "night",
)


def char_count(text):
    return len("".join(text.split()))


def hits_denylist(text, words):
    return any(word and word in text for word in words)


def _text(value):
    return isinstance(value, str) and bool(value.strip())


def validate(data):
    quotes = data["quotes"]
    frames = data["frames"]
    denylist = data["denylist"]
    if not isinstance(quotes, list) or not isinstance(frames, list) or not isinstance(denylist, dict):
        raise ValueError("corpus shape")
    for slot in SLOT_NAMES:
        if not isinstance(denylist.get(slot), list):
            raise ValueError(f"denylist {slot}")
    seen = set()
    for quote in quotes:
        if not _text(quote.get("id")) or not _text(quote.get("text")) or not _text(quote.get("author")) or not _text(quote.get("work")):
            raise ValueError("quote field")
        slots = quote.get("slots")
        if not isinstance(slots, list) or not slots:
            raise ValueError(f"{quote.get('id')} slots")
        if quote["id"] in seen:
            raise ValueError(f"duplicate {quote['id']}")
        seen.add(quote["id"])
        for slot in slots:
            if slot not in SLOT_NAMES:
                raise ValueError(f"unknown slot {slot}")
            if hits_denylist(quote["text"], denylist[slot]):
                raise ValueError(f"{quote['id']} denylist {slot}")
    seen_frames = set()
    counts = {slot: {"open": 0, "close": 0} for slot in SLOT_NAMES}
    for frame in frames:
        if not _text(frame.get("id")) or not _text(frame.get("text")):
            raise ValueError("frame field")
        if frame["id"] in seen_frames:
            raise ValueError(f"duplicate {frame['id']}")
        seen_frames.add(frame["id"])
        slot = frame.get("slot")
        role = frame.get("role")
        if slot not in SLOT_NAMES:
            raise ValueError(f"frame slot {frame['id']}")
        if role not in ("open", "close"):
            raise ValueError(f"frame role {frame['id']}")
        counts[slot][role] += 1
        if slot == "close" and "晚安" not in frame["text"] and "今天最后" not in frame["text"]:
            raise ValueError(f"{frame['id']} close phrase")
    for slot, roles in counts.items():
        if roles["open"] < 1 or roles["close"] < 1:
            raise ValueError(f"missing frame {slot}")
    if "plains" in data:
        _validate_plains(data)


def _validate_plains(data):
    plains = data["plains"]
    denylist = data["denylist"]
    if not isinstance(plains, list):
        raise ValueError("plains shape")
    seen = set()
    counts = {slot: 0 for slot in PLAIN_SLOTS}
    for item in plains:
        if not _text(item.get("id")) or not _text(item.get("text")):
            raise ValueError("plain field")
        if item["id"] in seen:
            raise ValueError(f"duplicate {item['id']}")
        seen.add(item["id"])
        slot = item.get("slot")
        if slot not in PLAIN_SLOTS:
            raise ValueError(f"plain slot {item['id']}")
        if char_count(item["text"]) < MIN_PLAIN_CHARS:
            raise ValueError(f"{item['id']} short")
        if hits_denylist(item["text"], denylist[slot]):
            raise ValueError(f"{item['id']} denylist {slot}")
        counts[slot] += 1
    for slot, count in counts.items():
        if count < 1:
            raise ValueError(f"missing plain {slot}")


def load(root):
    root = Path(root)
    data = {
        "quotes": json.loads((root / "corpus" / "quotes.json").read_text(encoding="utf-8")),
        "frames": json.loads((root / "corpus" / "frames.json").read_text(encoding="utf-8")),
        "denylist": json.loads((root / "corpus" / "denylist.json").read_text(encoding="utf-8")),
        "plains": json.loads((root / "corpus" / "plains.json").read_text(encoding="utf-8")),
    }
    validate(data)
    return data
