import json
from contextlib import contextmanager
from datetime import datetime, timedelta
from pathlib import Path

import fcntl


def empty_state():
    return {"sent_hours": [], "quotes": [], "frames": [], "plains": []}


def load_state(root):
    path = Path(root) / "state" / "state.json"
    if not path.exists():
        return empty_state()
    data = json.loads(path.read_text(encoding="utf-8"))
    for key in ("sent_hours", "quotes", "frames", "plains"):
        data.setdefault(key, [])
    return data


def save_state(root, data):
    path = Path(root) / "state" / "state.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)


def _aware(at, moment):
    if at.tzinfo is None:
        return at.replace(tzinfo=moment.tzinfo)
    return at


def _recent(at, moment, days):
    return moment - _aware(at, moment) < timedelta(days=days)


def prune(state, moment, keep_days):
    state["quotes"] = [
        item
        for item in state["quotes"]
        if _recent(datetime.fromisoformat(item["at"]), moment, keep_days)
    ]
    state["frames"] = [
        item
        for item in state["frames"]
        if _recent(datetime.fromisoformat(item["at"]), moment, keep_days)
    ]
    state["plains"] = [
        item
        for item in state.get("plains", [])
        if _recent(datetime.fromisoformat(item["at"]), moment, keep_days)
    ]
    kept = []
    for key in state["sent_hours"]:
        try:
            at = datetime.strptime(key, "%Y-%m-%d-%H").replace(tzinfo=moment.tzinfo)
        except ValueError:
            kept.append(key)
            continue
        if _recent(at, moment, keep_days):
            kept.append(key)
    state["sent_hours"] = kept


def already_sent(state, hour_key):
    return hour_key in state["sent_hours"]


def record(root, hour_key, picks, moment, keep_days):
    state = load_state(root)
    state["sent_hours"].append(hour_key)
    stamp = moment.isoformat()
    if picks.get("plain_id"):
        state["plains"].append({"id": picks["plain_id"], "at": stamp})
    else:
        state["quotes"].append({"id": picks["quote_id"], "at": stamp})
        state["frames"].append({"id": picks["open_id"], "at": stamp})
        state["frames"].append({"id": picks["close_id"], "at": stamp})
    prune(state, moment, keep_days)
    save_state(root, state)
    return state


@contextmanager
def locked(root):
    path = Path(root) / "state" / "send.lock"
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a+") as handle:
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
