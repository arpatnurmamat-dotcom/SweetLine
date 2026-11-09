from datetime import datetime

from sweetline.clock import hour_key, uses_poem
from sweetline.corpus import char_count, hits_denylist, MIN_PLAIN_CHARS


def render(opener, quote, closer):
    return f"{opener}\n\n{quote['text']}\n——{quote['author']}《{quote['work']}》\n\n{closer}"


def _latest(entries):
    latest = {}
    for item in entries:
        at = datetime.fromisoformat(item["at"])
        previous = latest.get(item["id"])
        if previous is None or at > previous:
            latest[item["id"]] = at
    return latest


def _stamp(latest, item_id, moment):
    at = latest.get(item_id)
    if at is None:
        return datetime.min.replace(tzinfo=moment.tzinfo)
    if at.tzinfo is None:
        return at.replace(tzinfo=moment.tzinfo)
    return at


def _ordered(valid, latest, moment, _days, _seed):
    return sorted(valid, key=lambda item: (_stamp(latest, item["id"], moment), item["id"]))


def compose(data, slot, moment, history, quote_cooldown_days, frame_cooldown_days):
    history = history or {}
    words = data["denylist"][slot]
    key = hour_key(moment)
    quote_latest = _latest(history.get("quotes", []))
    frame_latest = _latest(history.get("frames", []))
    quotes = [
        quote
        for quote in data["quotes"]
        if slot in quote["slots"] and not hits_denylist(quote["text"], words)
    ]
    if not quotes:
        raise ValueError(f"no quote for {slot}")
    opens = [
        frame
        for frame in data["frames"]
        if frame["slot"] == slot and frame["role"] == "open" and not hits_denylist(frame["text"], words)
    ]
    closes = [
        frame
        for frame in data["frames"]
        if frame["slot"] == slot and frame["role"] == "close" and not hits_denylist(frame["text"], words)
    ]
    if not opens or not closes:
        raise ValueError(f"no frame for {slot}")
    for quote in _ordered(quotes, quote_latest, moment, quote_cooldown_days, key):
        for opener in _ordered(opens, frame_latest, moment, frame_cooldown_days, f"{key}-open"):
            for closer in _ordered(closes, frame_latest, moment, frame_cooldown_days, f"{key}-close"):
                message = render(opener["text"], quote, closer["text"])
                if hits_denylist(message, words):
                    continue
                if slot == "close" and "晚安" not in message and "今天最后" not in message:
                    continue
                return message, {
                    "quote_id": quote["id"],
                    "open_id": opener["id"],
                    "close_id": closer["id"],
                }
    raise ValueError(f"no clean message for {slot}")


def compose_plain(data, slot, moment, history, frame_cooldown_days):
    history = history or {}
    words = data["denylist"][slot]
    key = hour_key(moment)
    latest = _latest(history.get("plains", []))
    plains = [
        item
        for item in data["plains"]
        if item["slot"] == slot and not hits_denylist(item["text"], words) and char_count(item["text"]) >= MIN_PLAIN_CHARS
    ]
    if not plains:
        raise ValueError(f"no plain for {slot}")
    for item in _ordered(plains, latest, moment, frame_cooldown_days, key):
        if hits_denylist(item["text"], words):
            continue
        return item["text"], {"plain_id": item["id"]}
    raise ValueError(f"no clean plain for {slot}")


def for_hour(data, slot, moment, history, quote_cooldown_days, frame_cooldown_days):
    if uses_poem(moment.hour):
        return compose(data, slot, moment, history, quote_cooldown_days, frame_cooldown_days)
    return compose_plain(data, slot, moment, history, frame_cooldown_days)
